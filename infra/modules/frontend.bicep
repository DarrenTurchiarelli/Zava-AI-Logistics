// =============================================================================
// Frontend Resource Group - App Service, App Service Plan, Application Insights
// =============================================================================

@description('Primary location for all resources')
param location string

@description('Unique suffix for resource names')
param uniqueSuffix string

@description('Environment name (dev, staging, production)')
param environment string

@description('SKU for App Service Plan')
param appServiceSku string

@description('Log Analytics Workspace ID from Shared Services')
param logAnalyticsId string

var resourcePrefix = 'zava-${environment}'
var appServicePlanName = '${resourcePrefix}-plan'
var appServiceName = '${resourcePrefix}-web-${uniqueSuffix}'
var appInsightsName = '${resourcePrefix}-insights-${uniqueSuffix}'

// =============================================================================
// Application Insights
// =============================================================================

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: appInsightsName
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalyticsId
  }
}

// =============================================================================
// App Service Plan
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
// App Service (Web App)
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
          name: 'USE_MANAGED_IDENTITY'
          value: 'true'
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
// Outputs
// =============================================================================

output appServiceName string = appService.name
output appServiceUrl string = 'https://${appService.properties.defaultHostName}'
output appServiceId string = appService.id
output appServicePrincipalId string = appService.identity.principalId
output appInsightsId string = appInsights.id
@secure()
output appInsightsConnectionString string = appInsights.properties.ConnectionString
output appServicePlanName string = appServicePlan.name
