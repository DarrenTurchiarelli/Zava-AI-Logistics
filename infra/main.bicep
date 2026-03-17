// =============================================================================
// Zava - Complete Infrastructure as Code (Bicep)
// Deploys all Azure resources required for the solution
// =============================================================================

@description('Primary location for all resources')
param location string = resourceGroup().location

@description('Unique suffix for resource names')
param uniqueSuffix string = substring(uniqueString(resourceGroup().id), 0, 6)

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
// Variables
// =============================================================================

var resourcePrefix = 'zava-${environment}'
var cosmosDbAccountName = '${resourcePrefix}-cosmos-${uniqueSuffix}'
var appServicePlanName = '${resourcePrefix}-plan'
var appServiceName = '${resourcePrefix}-web-${uniqueSuffix}'
var aiHubName = '${resourcePrefix}-aihub-${uniqueSuffix}'
var aiProjectName = '${resourcePrefix}-aiproject-${uniqueSuffix}'
var mapsAccountName = '${resourcePrefix}-maps-${uniqueSuffix}'
var speechServiceName = '${resourcePrefix}-speech-${uniqueSuffix}'
var visionServiceName = '${resourcePrefix}-vision-${uniqueSuffix}'
var storageAccountName = 'zava${environment}st${uniqueSuffix}'
var logAnalyticsName = '${resourcePrefix}-logs-${uniqueSuffix}'
var appInsightsName = '${resourcePrefix}-insights-${uniqueSuffix}'

// =============================================================================
// 1. Log Analytics Workspace (for monitoring)
// =============================================================================

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: logAnalyticsName
  location: location
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
  }
}

// =============================================================================
// 2. Application Insights
// =============================================================================

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: appInsightsName
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalytics.id
  }
}

// =============================================================================
// 3. Storage Account (for AI Hub)
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
// 4. Cosmos DB Account
// =============================================================================

resource cosmosDbAccount 'Microsoft.DocumentDB/databaseAccounts@2023-11-15' = {
  name: cosmosDbAccountName
  location: location
  kind: 'GlobalDocumentDB'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    databaseAccountOfferType: 'Standard'
    consistencyPolicy: {
      defaultConsistencyLevel: 'Session'
    }
    locations: [
      {
        locationName: location
        failoverPriority: 0
        isZoneRedundant: false
      }
    ]
    capabilities: [
      {
        name: 'EnableServerless'
      }
    ]
    disableLocalAuth: true  // Force RBAC authentication only
  }
}

// Cosmos DB Database
resource cosmosDatabase 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases@2023-11-15' = {
  parent: cosmosDbAccount
  name: 'logisticstracking'
  properties: {
    resource: {
      id: 'logisticstracking'
    }
  }
}

// Cosmos DB Containers
resource parcelsContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2023-11-15' = {
  parent: cosmosDatabase
  name: 'parcels'
  properties: {
    resource: {
      id: 'parcels'
      partitionKey: {
        paths: [
          '/store_location'
        ]
        kind: 'Hash'
      }
    }
  }
}

resource eventsContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2023-11-15' = {
  parent: cosmosDatabase
  name: 'parcel_events'
  properties: {
    resource: {
      id: 'parcel_events'
      partitionKey: {
        paths: [
          '/barcode'
        ]
        kind: 'Hash'
      }
    }
  }
}

resource manifestsContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2023-11-15' = {
  parent: cosmosDatabase
  name: 'driver_manifests'
  properties: {
    resource: {
      id: 'driver_manifests'
      partitionKey: {
        paths: [
          '/driver_id'
        ]
        kind: 'Hash'
      }
    }
  }
}

resource usersContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2023-11-15' = {
  parent: cosmosDatabase
  name: 'users'
  properties: {
    resource: {
      id: 'users'
      partitionKey: {
        paths: [
          '/user_type'
        ]
        kind: 'Hash'
      }
    }
  }
}

resource addressNotesContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2023-11-15' = {
  parent: cosmosDatabase
  name: 'address_notes'
  properties: {
    resource: {
      id: 'address_notes'
      partitionKey: {
        paths: [
          '/address_hash'
        ]
        kind: 'Hash'
      }
    }
  }
}

// =============================================================================
// 5. Azure Maps Account
// =============================================================================

resource mapsAccount 'Microsoft.Maps/accounts@2023-06-01' = {
  name: mapsAccountName
  location: 'global'
  sku: {
    name: 'G2'
  }
  kind: 'Gen2'
  properties: {
    disableLocalAuth: false  // Maps Gen2 uses subscription key authentication
  }
}

// =============================================================================
// 6. Speech Services
// =============================================================================

resource speechService 'Microsoft.CognitiveServices/accounts@2023-05-01' = {
  name: speechServiceName
  location: location
  sku: {
    name: 'S0'
  }
  kind: 'SpeechServices'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    customSubDomainName: speechServiceName
    publicNetworkAccess: 'Enabled'
    disableLocalAuth: true  // Force managed identity authentication
  }
}

// =============================================================================
// 7. Computer Vision (for OCR)
// =============================================================================

resource visionService 'Microsoft.CognitiveServices/accounts@2023-05-01' = {
  name: visionServiceName
  location: location
  sku: {
    name: 'S1'
  }
  kind: 'ComputerVision'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    customSubDomainName: visionServiceName
    publicNetworkAccess: 'Enabled'
    disableLocalAuth: true  // Force managed identity authentication
  }
}

// =============================================================================
// 8. Azure AI Foundry Hub
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
    applicationInsights: appInsights.id
  }
}

// =============================================================================
// 9. Azure AI Foundry Project
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

// =============================================================================
// 10. App Service Plan
// =============================================================================

resource appServicePlan 'Microsoft.Web/serverfarms@2023-01-01' = {
  name: appServicePlanName
  location: location
  sku: {
    name: appServiceSku
  }
  kind: 'linux'
  properties: {
    reserved: true
  }
}

// =============================================================================
// 11. App Service (Web App)
// =============================================================================

resource appService 'Microsoft.Web/sites@2023-01-01' = {
  name: appServiceName
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    serverFarmId: appServicePlan.id
    siteConfig: {
      linuxFxVersion: 'PYTHON|3.11'
      alwaysOn: true
      ftpsState: 'Disabled'
      minTlsVersion: '1.2'
      appCommandLine: 'gunicorn --bind=0.0.0.0:8000 --timeout 600 --workers=4 app:app'
      appSettings: [
        {
          name: 'SCM_DO_BUILD_DURING_DEPLOYMENT'
          value: 'true'
        }
        {
          name: 'COSMOS_DB_ENDPOINT'
          value: cosmosDbAccount.properties.documentEndpoint
        }
        {
          name: 'COSMOS_DB_DATABASE_NAME'
          value: 'logisticstracking'
        }
        {
          name: 'USE_MANAGED_IDENTITY'
          value: 'true'
        }
        {
          name: 'AZURE_MAPS_SUBSCRIPTION_KEY'
          value: mapsAccount.listKeys().primaryKey
        }
        {
          name: 'AZURE_SPEECH_ENDPOINT'
          value: speechService.properties.endpoint
        }
        {
          name: 'AZURE_SPEECH_REGION'
          value: location
        }
        {
          name: 'AZURE_VISION_ENDPOINT'
          value: visionService.properties.endpoint
        }
        {
          name: 'AZURE_AI_PROJECT_ENDPOINT'
          value: aiProject.properties.discoveryUrl
        }
        {
          name: 'AZURE_AI_MODEL_DEPLOYMENT_NAME'
          value: 'gpt-4o'
        }
        {
          name: 'FLASK_ENV'
          value: 'production'
        }
        {
          name: 'FLASK_SECRET_KEY'
          value: uniqueString(resourceGroup().id, appServiceName)
        }
        {
          name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
          value: appInsights.properties.ConnectionString
        }
      ]
    }
    httpsOnly: true
  }
}

// =============================================================================
// 12. RBAC Role Assignments
// =============================================================================

// Cosmos DB Data Contributor for App Service
resource cosmosRoleAssignment 'Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments@2023-11-15' = {
  parent: cosmosDbAccount
  name: guid(cosmosDbAccount.id, appService.id, 'cosmosdb-contributor')
  properties: {
    roleDefinitionId: '${cosmosDbAccount.id}/sqlRoleDefinitions/00000000-0000-0000-0000-000000000002'
    principalId: appService.identity.principalId
    scope: cosmosDbAccount.id
  }
}

// Cognitive Services OpenAI User for AI Hub access
resource aiRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(aiHub.id, appService.id, 'ai-user')
  scope: aiHub
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd')
    principalId: appService.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

// Cognitive Services User for Speech Service
resource speechRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(speechService.id, appService.id, 'speech-user')
  scope: speechService
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'a97b65f3-24c7-4388-baec-2e87135dc908')
    principalId: appService.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

// Cognitive Services User for Vision Service
resource visionRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(visionService.id, appService.id, 'vision-user')
  scope: visionService
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'a97b65f3-24c7-4388-baec-2e87135dc908')
    principalId: appService.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

// =============================================================================
// Outputs
// =============================================================================

output appServiceName string = appService.name
output appServiceUrl string = 'https://${appService.properties.defaultHostName}'
output cosmosDbEndpoint string = cosmosDbAccount.properties.documentEndpoint
output cosmosDbAccountName string = cosmosDbAccount.name
output aiHubName string = aiHub.name
output aiProjectName string = aiProject.name
output aiProjectEndpoint string = aiProject.properties.discoveryUrl
output mapsAccountName string = mapsAccount.name
output speechServiceEndpoint string = speechService.properties.endpoint
output visionServiceEndpoint string = visionService.properties.endpoint
output resourceGroupName string = resourceGroup().name

output nextSteps string = '''
Infrastructure deployed successfully!

NEXT STEPS:

1. Deploy GPT-4o model in AI Foundry:
   - Visit: https://ai.azure.com
   - Select your project: ${aiProjectName}
   - Go to "Deployments" -> "Deploy Model"
   - Deploy "gpt-4o" model

2. Create 8 AI Agents in AI Foundry:
   - Customer Service Agent
   - Fraud Detection Agent
   - Identity Verification Agent
   - Dispatcher Agent
   - Parcel Intake Agent
   - Sorting Facility Agent
   - Delivery Coordination Agent
   - Optimization Agent

3. Update App Service settings with agent IDs:
   az webapp config appsettings set --name ${appServiceName} --resource-group ${resourceGroupName} --settings \\
     CUSTOMER_SERVICE_AGENT_ID=asst_xxx \\
     FRAUD_RISK_AGENT_ID=asst_xxx \\
     ... (remaining 6 agent IDs)

4. Deploy application code:
   cd <repo-directory>
   az webapp up --name ${appServiceName} --resource-group ${resourceGroupName}

5. Initialize database and demo data:
   Visit: https://${appService.properties.defaultHostName}/setup
   Or run manually: python parcel_tracking_db.py && python utils/generators/generate_demo_manifests.py

Access your application at: https://${appService.properties.defaultHostName}
'''
