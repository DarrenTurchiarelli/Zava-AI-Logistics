// =============================================================================
// App Service Configuration Update Module
// Updates app settings with cross-resource group endpoint values
// =============================================================================

@description('App Service name')
param appServiceName string

@description('Cosmos DB endpoint from Backend RG')
param cosmosDbEndpoint string

@description('Azure OpenAI endpoint from Middleware RG')
param azureOpenAIEndpoint string

@description('AI Project endpoint from Middleware RG')
param aiProjectEndpoint string

@description('Azure Maps subscription key from Shared RG')
@secure()
param azureMapsSubscriptionKey string

@description('Speech Service endpoint from Shared RG')
param speechServiceEndpoint string

@description('Vision Service endpoint from Shared RG')
param visionServiceEndpoint string

@description('Location for regional services')
param location string

@description('Flask secret key')
@secure()
param flaskSecretKey string

@description('Application Insights connection string')
@secure()
param appInsightsConnectionString string

// Get reference to existing App Service
resource appService 'Microsoft.Web/sites@2023-01-01' existing = {
  name: appServiceName
}

// Update app settings with cross-RG endpoints
resource appServiceConfig 'Microsoft.Web/sites/config@2023-01-01' = {
  parent: appService
  name: 'appsettings'
  properties: {
    SCM_DO_BUILD_DURING_DEPLOYMENT: 'true'
    USE_MANAGED_IDENTITY: 'true'
    FLASK_ENV: 'production'
    FLASK_SECRET_KEY: flaskSecretKey
    APPLICATIONINSIGHTS_CONNECTION_STRING: appInsightsConnectionString
    
    // Backend - Cosmos DB
    COSMOS_DB_ENDPOINT: cosmosDbEndpoint
    COSMOS_DB_DATABASE_NAME: 'logisticstracking'
    
    // Middleware - Azure OpenAI & AI
    AZURE_OPENAI_ENDPOINT: azureOpenAIEndpoint
    AZURE_AI_PROJECT_ENDPOINT: aiProjectEndpoint
    AZURE_AI_MODEL_DEPLOYMENT_NAME: 'gpt-4o'
    
    // Shared Services
    AZURE_MAPS_SUBSCRIPTION_KEY: azureMapsSubscriptionKey
    AZURE_SPEECH_ENDPOINT: speechServiceEndpoint
    AZURE_SPEECH_REGION: location
    AZURE_VISION_ENDPOINT: visionServiceEndpoint
  }
}

output configUpdated bool = true
