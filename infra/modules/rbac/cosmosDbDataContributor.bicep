// =============================================================================
// Cosmos DB RBAC Module - Grants App Service access to Cosmos DB
// =============================================================================

@description('Principal ID of the App Service managed identity')
param appServicePrincipalId string

@description('Cosmos DB account name')
param cosmosAccountName string

// Get reference to existing Cosmos DB account
resource cosmosAccount 'Microsoft.DocumentDB/databaseAccounts@2023-11-15' existing = {
  name: cosmosAccountName
}

// Built-in Data Contributor role definition ID
var dataContributorRoleId = '00000000-0000-0000-0000-000000000002'

// Assign Cosmos DB Data Contributor role to App Service
resource roleAssignment 'Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments@2023-11-15' = {
  parent: cosmosAccount
  name: guid(cosmosAccount.id, appServicePrincipalId, dataContributorRoleId)
  properties: {
    roleDefinitionId: '${cosmosAccount.id}/sqlRoleDefinitions/${dataContributorRoleId}'
    principalId: appServicePrincipalId
    scope: cosmosAccount.id
  }
}

output roleAssignmentId string = roleAssignment.id
