// =============================================================================
// RBAC Helper Module - Cognitive Services OpenAI User Role Assignment
// =============================================================================

@description('Principal ID (Managed Identity) to grant access to')
param principalId string

@description('Resource ID of the Cognitive Services account')
param resourceId string

// Extract resource parts for naming
var resourceParts = split(resourceId, '/')
var resourceName = resourceParts[length(resourceParts) - 1]

// Cognitive Services OpenAI User role ID
var roleDefinitionId = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd')

resource roleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(resourceId, principalId, 'openai-user')
  properties: {
    roleDefinitionId: roleDefinitionId
    principalId: principalId
    principalType: 'ServicePrincipal'
  }
}

output assignmentId string = roleAssignment.id
