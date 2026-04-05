// =============================================================================
// Backend Resource Group - Cosmos DB
// =============================================================================

@description('Primary location for all resources')
param location string

@description('Unique suffix for resource names')
param uniqueSuffix string

@description('Environment name (dev, staging, production)')
param environment string

var resourcePrefix = 'zava-${environment}'
var cosmosDbAccountName = '${resourcePrefix}-cosmos-${uniqueSuffix}'

// =============================================================================
// Cosmos DB Account
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
      defaultTtl: 2592000 // 30 days — manifests accumulate daily; auto-expire old ones
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
          '/username'
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
// Outputs
// =============================================================================

output cosmosDbEndpoint string = cosmosDbAccount.properties.documentEndpoint
output cosmosDbAccountName string = cosmosDbAccount.name
output cosmosDbAccountId string = cosmosDbAccount.id
output cosmosDbPrincipalId string = cosmosDbAccount.identity.principalId
