// =============================================================================
// RBAC Helper Module - Cognitive Services Role Assignment
// Supports both OpenAI and general Cognitive Services (Vision, Speech, etc.)
// =============================================================================

@description('Principal ID (Managed Identity) to grant access to')
param principalId string

@description('Full resource ID of the Cognitive Services account')
param cognitiveServiceName string

@description('Service type: openai, vision, speech, or general')
@allowed([
  'openai'
  'vision'
  'speech'
  'general'
])
param serviceType string = 'general'

// Get reference to existing Cognitive Services account
resource cognitiveService 'Microsoft.CognitiveServices/accounts@2023-05-01' existing = {
  name: cognitiveServiceName
}

// Role IDs for different Cognitive Services
var roleIds = {
  // Cognitive Services OpenAI User - For Azure OpenAI service only
  openai: '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd'
  // Cognitive Services User - For Vision, Speech, and other Cognitive Services
  general: 'a97b65f3-24c7-4388-baec-2e87135dc908'
  // Cognitive Services User - Same for Vision
  vision: 'a97b65f3-24c7-4388-baec-2e87135dc908'
  // Cognitive Services User - Same for Speech
  speech: 'a97b65f3-24c7-4388-baec-2e87135dc908'
}

var roleId = roleIds[serviceType]

resource roleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(cognitiveService.id, principalId, roleId)
  scope: cognitiveService
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleId)
    principalId: principalId
    principalType: 'ServicePrincipal'
  }
}

output assignmentId string = roleAssignment.id
