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
var aiServicesName = '${resourcePrefix}-aisvc-${uniqueSuffix}'   // AIServices kind — new name forces clean create (kind is immutable)
var openAIServiceName = aiServicesName                         // backward-compat alias used by outputs and RBAC modules
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
// Azure AI Services Account (unified: OpenAI + Vision + Speech + future models)
// kind: AIServices gives *.cognitiveservices.azure.com endpoint, which the AI Hub
// can connect to via category: AIServices — required for FoundryChatClient support.
// =============================================================================

resource openAIService 'Microsoft.CognitiveServices/accounts@2024-04-01-preview' = {
  name: aiServicesName
  location: location
  sku: {
    name: 'S0'
  }
  kind: 'AIServices'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    customSubDomainName: aiServicesName
    publicNetworkAccess: 'Enabled'
    disableLocalAuth: true  // Managed identity only
  }
}

// Deploy GPT-4o model
resource gpt4oDeployment 'Microsoft.CognitiveServices/accounts/deployments@2024-04-01-preview' = {
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

// Connection from AI Hub to Azure AI Services
// category: AIServices enables the Hub/Project to expose *.services.ai.azure.com
// and allows FoundryChatClient to resolve the deployment through the project plane.
resource aiServicesConnection 'Microsoft.MachineLearningServices/workspaces/connections@2024-04-01' = {
  parent: aiHub
  name: 'aiservices-connection'
  properties: {
    category: 'AIServices'
    target: openAIService.properties.endpoint
    authType: 'AAD'
    isSharedToAll: true
    metadata: {
      ApiVersion: '2024-05-01-preview'
      Kind: 'AIServices'
      ResourceId: openAIService.id
    }
  }
}

// =============================================================================
// Outputs
// =============================================================================

output openAIServiceName string = openAIService.name           // backward-compat: used by RBAC modules
output openAIServiceEndpoint string = openAIService.properties.endpoint  // *.cognitiveservices.azure.com — OpenAI SDK accepts this
output aiServicesEndpoint string = openAIService.properties.endpoint     // explicit alias for FoundryChatClient (project_endpoint)
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
