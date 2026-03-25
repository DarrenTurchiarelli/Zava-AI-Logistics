// =============================================================================
// RBAC Helper Module - Cognitive Services OpenAI User Role Assignment
// =============================================================================

@description('Principal ID (Managed Identity) to grant access to')
param principalId string

@description('Full resource ID of the Cognitive Services account')
param cognitiveServiceName string

// Get reference to existing Cognitive Services account
resource cognitiveService 'Microsoft.CognitiveServices/accounts@2023-05-01' existing = {
  name: cognitiveServiceName
}

// Cognitive Services OpenAI User role ID
var cognitiveServicesOpenAIUserRoleId = '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd'

resource roleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(cognitiveService.id, principalId, cognitiveServicesOpenAIUserRoleId)
  scope: cognitiveService
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', cognitiveServicesOpenAIUserRoleId)
    principalId: principalId
    principalType: 'ServicePrincipal'
  }
}

output assignmentId string = roleAssignment.id
