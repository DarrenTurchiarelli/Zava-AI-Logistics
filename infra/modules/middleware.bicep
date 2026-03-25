// =============================================================================
// Middleware Resource Group - Azure OpenAI, AI Hub, AI Project, Storage
// =============================================================================

@description('Primary location for all resources')
param location string

@description('Unique suffix for resource names')
param uniqueSuffix string

@description('Environment name (dev, staging, production)')
param environment string

@description('Application Insights ID from Frontend')
param appInsightsId string

var resourcePrefix = 'zava-${environment}'
var openAIServiceName = '${resourcePrefix}-openai-${uniqueSuffix}'
var aiHubName = '${resourcePrefix}-aihub-${uniqueSuffix}'
var aiProjectName = '${resourcePrefix}-aiproject-${uniqueSuffix}'
var storageAccountName = 'zava${environment}st${uniqueSuffix}'

// =============================================================================
// Storage Account (for AI Hub)
// =============================================================================

resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: storageAccountName
  location: location
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    accessTier: 'Hot'
    allowBlobPublicAccess: false
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
  }
}

// =============================================================================
// Azure OpenAI Service (for AI agents)
// =============================================================================

resource openAIService 'Microsoft.CognitiveServices/accounts@2023-05-01' = {
  name: openAIServiceName
  location: location
  sku: {
    name: 'S0'
  }
  kind: 'OpenAI'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    customSubDomainName: openAIServiceName
    publicNetworkAccess: 'Enabled'
    disableLocalAuth: true  // Managed identity only (deployment script temporarily enables keys for agent creation)
  }
}

// Deploy GPT-4o model
resource gpt4oDeployment 'Microsoft.CognitiveServices/accounts/deployments@2023-05-01' = {
  parent: openAIService
  name: 'gpt-4o'
  sku: {
    name: 'GlobalStandard'
    capacity: 10
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'gpt-4o'
      version: '2024-08-06'
    }
    raiPolicyName: 'Microsoft.Default'
  }
}

// =============================================================================
// Azure AI Foundry Hub
// =============================================================================

resource aiHub 'Microsoft.MachineLearningServices/workspaces@2024-04-01' = {
  name: aiHubName
  location: location
  sku: {
    name: 'Basic'
    tier: 'Basic'
  }
  kind: 'Hub'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    friendlyName: 'Zava AI Hub'
    description: 'AI Hub for Zava logistics platform with 8 AI agents'
    storageAccount: storageAccount.id
    applicationInsights: appInsightsId
  }
}

// =============================================================================
// Azure AI Foundry Project
// =============================================================================

resource aiProject 'Microsoft.MachineLearningServices/workspaces@2024-04-01' = {
  name: aiProjectName
  location: location
  sku: {
    name: 'Basic'
    tier: 'Basic'
  }
  kind: 'Project'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    friendlyName: 'Zava AI Project'
    description: 'AI Project for Zava with Customer Service, Fraud Detection, and operational agents'
    hubResourceId: aiHub.id
  }
}

// Connection from AI Hub to Azure OpenAI
resource openAIConnection 'Microsoft.MachineLearningServices/workspaces/connections@2024-04-01' = {
  parent: aiHub
  name: 'aoai-connection'
  properties: {
    category: 'AzureOpenAI'
    target: openAIService.properties.endpoint
    authType: 'AAD'
    isSharedToAll: true
    metadata: {
      ApiVersion: '2024-02-01'
      ApiType: 'Azure'
      ResourceId: openAIService.id
    }
  }
}

// =============================================================================
// Outputs
// =============================================================================

output openAIServiceName string = openAIService.name
output openAIServiceEndpoint string = openAIService.properties.endpoint
output openAIServiceId string = openAIService.id
output openAIServicePrincipalId string = openAIService.identity.principalId
output aiHubName string = aiHub.name
output aiHubId string = aiHub.id
output aiHubPrincipalId string = aiHub.identity.principalId
output aiProjectName string = aiProject.name
output aiProjectEndpoint string = aiProject.properties.discoveryUrl
output aiProjectId string = aiProject.id
output aiProjectPrincipalId string = aiProject.identity.principalId
output storageAccountName string = storageAccount.name
output storageAccountId string = storageAccount.id
