// =============================================================================
// Shared Services Resource Group - Maps, Speech, Vision, Log Analytics
// =============================================================================

@description('Primary location for all resources')
param location string

@description('Unique suffix for resource names')
param uniqueSuffix string

@description('Environment name (dev, staging, production)')
param environment string

var resourcePrefix = 'zava-${environment}'
var mapsAccountName = '${resourcePrefix}-maps-${uniqueSuffix}'
var speechServiceName = '${resourcePrefix}-speech-${uniqueSuffix}'
var visionServiceName = '${resourcePrefix}-vision-${uniqueSuffix}'
var logAnalyticsName = '${resourcePrefix}-logs-${uniqueSuffix}'

// =============================================================================
// Log Analytics Workspace (for monitoring)
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
// Azure Maps Account
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
// Speech Services
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
// Computer Vision (for OCR)
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
// Outputs
// =============================================================================

output mapsAccountName string = mapsAccount.name
output mapsAccountId string = mapsAccount.id
output mapsSubscriptionKey string = mapsAccount.listKeys().primaryKey
output speechServiceName string = speechService.name
output speechServiceEndpoint string = speechService.properties.endpoint
output speechServiceId string = speechService.id
output speechServicePrincipalId string = speechService.identity.principalId
output visionServiceName string = visionService.name
output visionServiceEndpoint string = visionService.properties.endpoint
output visionServiceId string = visionService.id
output visionServicePrincipalId string = visionService.identity.principalId
output logAnalyticsId string = logAnalytics.id
output logAnalyticsWorkspaceId string = logAnalytics.properties.customerId
