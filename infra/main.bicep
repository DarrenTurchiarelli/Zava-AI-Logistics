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
  dependsOn: [
    sharedServices
  ]
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
  dependsOn: [
    frontend
  ]
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

// Cosmos DB Data Contributor for App Service
resource cosmosRoleAssignment 'Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments@2023-11-15' = {
  name: guid(backend.outputs.cosmosDbAccountId, frontend.outputs.appServicePrincipalId, 'cosmosdb-contributor')
  scope: resourceGroup(backendRgName)
  properties: {
    roleDefinitionId: '${backend.outputs.cosmosDbAccountId}/sqlRoleDefinitions/00000000-0000-0000-0000-000000000002'
    principalId: frontend.outputs.appServicePrincipalId
    scope: backend.outputs.cosmosDbAccountId
  }
  dependsOn: [
    frontend
    backend
  ]
}

// Cognitive Services OpenAI User for App Service
module openAIAppServiceRbac 'modules/rbac/cognitiveServicesUser.bicep' = {
  scope: middlewareRg
  name: 'openai-appservice-rbac'
  params: {
    principalId: frontend.outputs.appServicePrincipalId
    resourceId: middleware.outputs.openAIServiceId
  }
  dependsOn: [
    frontend
    middleware
  ]
}

// Cognitive Services OpenAI User for AI Hub
module openAIHubRbac 'modules/rbac/cognitiveServicesUser.bicep' = {
  scope: middlewareRg
  name: 'openai-hub-rbac'
  params: {
    principalId: middleware.outputs.aiHubPrincipalId
    resourceId: middleware.outputs.openAIServiceId
  }
  dependsOn: [
    middleware
  ]
}

// Cognitive Services OpenAI User for AI Project
module openAIProjectRbac 'modules/rbac/cognitiveServicesUser.bicep' = {
  scope: middlewareRg
  name: 'openai-project-rbac'
  params: {
    principalId: middleware.outputs.aiProjectPrincipalId
    resourceId: middleware.outputs.openAIServiceId
  }
  dependsOn: [
    middleware
  ]
}

// Cognitive Services User for AI Hub (for Speech/Vision)
module aiHubSharedRbac 'modules/rbac/cognitiveServicesUser.bicep' = {
  scope: middlewareRg
  name: 'aihub-shared-rbac'
  params: {
    principalId: middleware.outputs.aiHubPrincipalId
    resourceId: middleware.outputs.openAIServiceId
  }
  dependsOn: [
    middleware
  ]
}

// Cognitive Services User for App Service to Speech Service
module speechAppServiceRbac 'modules/rbac/cognitiveServicesUser.bicep' = {
  scope: sharedRg
  name: 'speech-appservice-rbac'
  params: {
    principalId: frontend.outputs.appServicePrincipalId
    resourceId: sharedServices.outputs.speechServiceId
  }
  dependsOn: [
    frontend
    sharedServices
  ]
}

// Cognitive Services User for App Service to Vision Service
module visionAppServiceRbac 'modules/rbac/cognitiveServicesUser.bicep' = {
  scope: sharedRg
  name: 'vision-appservice-rbac'
  params: {
    principalId: frontend.outputs.appServicePrincipalId
    resourceId: sharedServices.outputs.visionServiceId
  }
  dependsOn: [
    frontend
    sharedServices
  ]
}

// =============================================================================
// Update App Service Configuration with Cross-Resource Group Endpoints
// =============================================================================

resource appService 'Microsoft.Web/sites@2023-01-01' existing = {
  scope: frontendRg
  name: frontend.outputs.appServiceName
}

resource appServiceConfig 'Microsoft.Web/sites/config@2023-01-01' = {
  parent: appService
  name: 'appsettings'
  properties: {
    SCM_DO_BUILD_DURING_DEPLOYMENT: 'true'
    USE_MANAGED_IDENTITY: 'true'
    FLASK_ENV: 'production'
    FLASK_SECRET_KEY: uniqueString(subscription().id, frontend.outputs.appServiceName)
    APPLICATIONINSIGHTS_CONNECTION_STRING: frontend.outputs.appInsightsConnectionString
    
    // Backend - Cosmos DB
    COSMOS_DB_ENDPOINT: backend.outputs.cosmosDbEndpoint
    COSMOS_DB_DATABASE_NAME: 'logisticstracking'
    
    // Middleware - Azure OpenAI & AI
    AZURE_OPENAI_ENDPOINT: middleware.outputs.openAIServiceEndpoint
    AZURE_AI_PROJECT_ENDPOINT: middleware.outputs.aiProjectEndpoint
    AZURE_AI_MODEL_DEPLOYMENT_NAME: 'gpt-4o'
    
    // Shared Services
    AZURE_MAPS_SUBSCRIPTION_KEY: sharedServices.outputs.mapsSubscriptionKey
    AZURE_SPEECH_ENDPOINT: sharedServices.outputs.speechServiceEndpoint
    AZURE_SPEECH_REGION: location
    AZURE_VISION_ENDPOINT: sharedServices.outputs.visionServiceEndpoint
  }
  dependsOn: [
    frontend
    middleware
    backend
    sharedServices
  ]
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
