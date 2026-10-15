// =============================================================================
// RBAC Helper Module - Foundry Project User
// =============================================================================

@description('Principal ID (Managed Identity) to grant Foundry project access to')
param principalId string

@description('Name of the parent Microsoft Foundry account')
param foundryAccountName string

@description('Name of the Microsoft Foundry project')
param foundryProjectName string

resource foundryAccount 'Microsoft.CognitiveServices/accounts@2025-06-01' existing = {
  name: foundryAccountName
}

resource foundryProject 'Microsoft.CognitiveServices/accounts/projects@2025-06-01' existing = {
  parent: foundryAccount
  name: foundryProjectName
}

// Foundry User - required for SDK and model access through a Foundry project endpoint.
var foundryUserRoleId = '53ca6127-db72-4b80-b1b0-d745d6d5456d'

resource roleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(foundryProject.id, principalId, foundryUserRoleId)
  scope: foundryProject
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', foundryUserRoleId)
    principalId: principalId
    principalType: 'ServicePrincipal'
  }
}

output assignmentId string = roleAssignment.id
