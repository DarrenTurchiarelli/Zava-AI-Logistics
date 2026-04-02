// =============================================================================
// Zava - Multi-Resource Group Infrastructure Orchestrator
// Deploys resources across 4 resource groups for better organization
// =============================================================================

targetScope = 'subscription'

@description('Primary location for all resources')
param location string = 'australiaeast'

@description('Unique suffix for resource names')
param uniqueSuffix string = substring(uniqueString(subscription().id), 0, 6)

@description('Environment name (dev, staging, production)')
@allowed([
  'dev'
  'staging'
  'production'
])
param environment string = 'dev'

@description('SKU for App Service Plan')
@allowed([
  'B1'
  'B2'
  'B3'
  'P1v2'
  'P2v2'
  'P3v2'
])
param appServiceSku string = 'B2'

// =============================================================================
// Resource Group Names
// =============================================================================

var frontendRgName = 'RG-Zava-Frontend-${environment}'
var middlewareRgName = 'RG-Zava-Middleware-${environment}'
var backendRgName = 'RG-Zava-Backend-${environment}'
var sharedRgName = 'RG-Zava-Shared-${environment}'

// =============================================================================
// Resource Groups
// =============================================================================

resource frontendRg 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: frontendRgName
  location: location
  tags: {
    Environment: environment
    Layer: 'Frontend'
    Project: 'Zava-Logistics'
  }
}

resource middlewareRg 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: middlewareRgName
  location: location
  tags: {
    Environment: environment
    Layer: 'Middleware'
    Project: 'Zava-Logistics'
  }
}

resource backendRg 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: backendRgName
  location: location
  tags: {
    Environment: environment
    Layer: 'Backend'
    Project: 'Zava-Logistics'
  }
}

resource sharedRg 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: sharedRgName
  location: location
  tags: {
    Environment: environment
    Layer: 'Shared Services'
    Project: 'Zava-Logistics'
  }
}

// =============================================================================
// Module Deployments
// =============================================================================

// 1. Shared Services (deployed first - provides Log Analytics for others)
module sharedServices 'modules/shared.bicep' = {
  scope: sharedRg
  name: 'sharedServices-${uniqueSuffix}'
  params: {
    location: location
    uniqueSuffix: uniqueSuffix
    environment: environment
  }
}

// 2. Frontend (depends on Shared Services for Log Analytics)
module frontend 'modules/frontend.bicep' = {
  scope: frontendRg
  name: 'frontend-${uniqueSuffix}'
  params: {
    location: location
    uniqueSuffix: uniqueSuffix
    environment: environment
    appServiceSku: appServiceSku
    logAnalyticsId: sharedServices.outputs.logAnalyticsId
  }
}

// 3. Middleware (depends on Frontend for Application Insights)
module middleware 'modules/middleware.bicep' = {
  scope: middlewareRg
  name: 'middleware-${uniqueSuffix}'
  params: {
    location: location
    uniqueSuffix: uniqueSuffix
    environment: environment
    appInsightsId: frontend.outputs.appInsightsId
  }
}

// 4. Backend (can be deployed independently)
module backend 'modules/backend.bicep' = {
  scope: backendRg
  name: 'backend-${uniqueSuffix}'
  params: {
    location: location
    uniqueSuffix: uniqueSuffix
    environment: environment
  }
}

// =============================================================================
// Cross-Resource Group RBAC Assignments
// =============================================================================

// Cosmos DB Data Contributor for App Service (deployed to Backend RG)
module cosmosRoleAssignment 'modules/rbac/cosmosDbDataContributor.bicep' = {
  scope: backendRg
  name: 'cosmos-appservice-rbac'
  params: {
    appServicePrincipalId: frontend.outputs.appServicePrincipalId
    cosmosAccountName: backend.outputs.cosmosDbAccountName
  }
}

// Cognitive Services OpenAI User for App Service (deployed to Middleware RG)
module openAIAppServiceRbac 'modules/rbac/cognitiveServicesUser.bicep' = {
  scope: middlewareRg
  name: 'openai-appservice-rbac'
  params: {
    principalId: frontend.outputs.appServicePrincipalId
    cognitiveServiceName: middleware.outputs.openAIServiceName
    serviceType: 'openai'
  }
}

// Cognitive Services OpenAI User for AI Hub (deployed to Middleware RG)
module openAIHubRbac 'modules/rbac/cognitiveServicesUser.bicep' = {
  scope: middlewareRg
  name: 'openai-hub-rbac'
  params: {
    principalId: middleware.outputs.aiHubPrincipalId
    cognitiveServiceName: middleware.outputs.openAIServiceName
    serviceType: 'openai'
  }
}

// Cognitive Services OpenAI User for AI Project (deployed to Middleware RG)
module openAIProjectRbac 'modules/rbac/cognitiveServicesUser.bicep' = {
  scope: middlewareRg
  name: 'openai-project-rbac'
  params: {
    principalId: middleware.outputs.aiProjectPrincipalId
    cognitiveServiceName: middleware.outputs.openAIServiceName
    serviceType: 'openai'
  }
}

// Cognitive Services User for App Service to Speech Service (deployed to Shared RG)
module speechAppServiceRbac 'modules/rbac/cognitiveServicesUser.bicep' = {
  scope: sharedRg
  name: 'speech-appservice-rbac'
  params: {
    principalId: frontend.outputs.appServicePrincipalId
    cognitiveServiceName: sharedServices.outputs.speechServiceName
    serviceType: 'speech'
  }
}

// Cognitive Services User for App Service to Vision Service (deployed to Shared RG)
module visionAppServiceRbac 'modules/rbac/cognitiveServicesUser.bicep' = {
  scope: sharedRg
  name: 'vision-appservice-rbac'
  params: {
    principalId: frontend.outputs.appServicePrincipalId
    cognitiveServiceName: sharedServices.outputs.visionServiceName
    serviceType: 'vision'
  }
}

// =============================================================================
// Update App Service Configuration with Cross-Resource Group Endpoints
// =============================================================================

// Update App Service config with endpoints from all resource groups (deployed to Frontend RG)
module appServiceConfig 'modules/appServiceConfig.bicep' = {
  scope: frontendRg
  name: 'appservice-config'
  params: {
    appServiceName: frontend.outputs.appServiceName
    cosmosDbEndpoint: backend.outputs.cosmosDbEndpoint
    azureOpenAIEndpoint: middleware.outputs.openAIServiceEndpoint
    aiProjectEndpoint: middleware.outputs.aiProjectEndpoint
    azureMapsSubscriptionKey: sharedServices.outputs.mapsSubscriptionKey
    speechServiceEndpoint: sharedServices.outputs.speechServiceEndpoint
    visionServiceEndpoint: sharedServices.outputs.visionServiceEndpoint
    location: location
    flaskSecretKey: uniqueString(subscription().id, frontend.outputs.appServiceName)
    appInsightsConnectionString: frontend.outputs.appInsightsConnectionString
  }
}

// =============================================================================
// Outputs
// =============================================================================

output resourceGroups object = {
  frontend: frontendRgName
  middleware: middlewareRgName
  backend: backendRgName
  shared: sharedRgName
}

output frontend object = {
  appServiceName: frontend.outputs.appServiceName
  appServiceUrl: frontend.outputs.appServiceUrl
  appInsightsId: frontend.outputs.appInsightsId
}

output middleware object = {
  openAIServiceName: middleware.outputs.openAIServiceName
  openAIServiceEndpoint: middleware.outputs.openAIServiceEndpoint
  aiHubName: middleware.outputs.aiHubName
  aiProjectName: middleware.outputs.aiProjectName
  aiProjectEndpoint: middleware.outputs.aiProjectEndpoint
}

output backend object = {
  cosmosDbAccountName: backend.outputs.cosmosDbAccountName
  cosmosDbEndpoint: backend.outputs.cosmosDbEndpoint
}

output shared object = {
  mapsAccountName: sharedServices.outputs.mapsAccountName
  speechServiceEndpoint: sharedServices.outputs.speechServiceEndpoint
  visionServiceEndpoint: sharedServices.outputs.visionServiceEndpoint
}

output nextSteps string = '''
✅ Multi-Resource Group Infrastructure Deployed Successfully!

RESOURCE GROUPS:
- Frontend: ${frontendRgName}
- Middleware: ${middlewareRgName}
- Backend: ${backendRgName}
- Shared Services: ${sharedRgName}

NEXT STEPS:

1. Create 8 AI Agents (automated in deployment script)
2. Agent IDs will be configured in App Service settings
3. Demo data will be initialized automatically

Access your application at: ${frontend.outputs.appServiceUrl}
'''
