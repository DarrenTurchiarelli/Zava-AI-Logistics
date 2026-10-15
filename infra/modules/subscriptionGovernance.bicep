targetScope = 'subscription'

type roleAssignmentConfig = {
  principalId: string
  roleDefinitionId: string
  principalType: 'User' | 'Group' | 'ServicePrincipal' | 'ForeignGroup' | 'Device'
  description: string
}

type policyAssignmentConfig = {
  name: string
  displayName: string
  description: string
  policyDefinitionId: string
  enforcementMode: 'Default' | 'DoNotEnforce'
  parameters: object
}

type defenderPlanConfig = {
  name: string
  pricingTier: 'Free' | 'Standard'
  subPlan: string
}

@description('Name of the subscription budget.')
param budgetName string = 'zava-monthly-budget'

@description('Monthly budget amount in the subscription billing currency. Set to 0 to skip budget deployment.')
@minValue(0)
param monthlyBudgetAmount int = 0

@description('Email addresses that receive budget notifications. At least one is required when monthlyBudgetAmount is greater than 0.')
param budgetContactEmails string[] = []

@description('Budget start date. Azure requires the first day of a month.')
param budgetStartDate string = utcNow('yyyy-MM-01')

@description('Subscription-scope role assignments. roleDefinitionId must be a built-in or custom role definition GUID.')
param roleAssignments roleAssignmentConfig[] = []

@description('Subscription-scope Azure Policy assignments. policyDefinitionId must be a full resource ID.')
param policyAssignments policyAssignmentConfig[] = []

@description('Microsoft Defender for Cloud plans. Standard pricing can incur charges; no plans are enabled by default.')
param defenderPlans defenderPlanConfig[] = []

resource budget 'Microsoft.Consumption/budgets@2024-08-01' = if (monthlyBudgetAmount > 0 && length(budgetContactEmails) > 0) {
  name: budgetName
  properties: {
    amount: monthlyBudgetAmount
    category: 'Cost'
    timeGrain: 'Monthly'
    timePeriod: {
      startDate: budgetStartDate
    }
    notifications: {
      Actual80Percent: {
        enabled: true
        operator: 'GreaterThanOrEqualTo'
        threshold: 80
        thresholdType: 'Actual'
        contactEmails: budgetContactEmails
      }
      Actual100Percent: {
        enabled: true
        operator: 'GreaterThanOrEqualTo'
        threshold: 100
        thresholdType: 'Actual'
        contactEmails: budgetContactEmails
      }
      Forecast100Percent: {
        enabled: true
        operator: 'GreaterThanOrEqualTo'
        threshold: 100
        thresholdType: 'Forecasted'
        contactEmails: budgetContactEmails
      }
    }
  }
}

resource subscriptionRoleAssignments 'Microsoft.Authorization/roleAssignments@2022-04-01' = [for assignment in roleAssignments: {
  name: guid(subscription().id, assignment.principalId, assignment.roleDefinitionId)
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', assignment.roleDefinitionId)
    principalId: assignment.principalId
    principalType: assignment.principalType
    description: assignment.description
  }
}]

resource subscriptionPolicyAssignments 'Microsoft.Authorization/policyAssignments@2024-04-01' = [for assignment in policyAssignments: {
  name: assignment.name
  properties: {
    displayName: assignment.displayName
    description: assignment.description
    policyDefinitionId: assignment.policyDefinitionId
    enforcementMode: assignment.enforcementMode
    parameters: assignment.parameters
  }
}]

resource defenderForCloudPlans 'Microsoft.Security/pricings@2024-01-01' = [for plan in defenderPlans: {
  name: plan.name
  properties: empty(plan.subPlan) ? {
    pricingTier: plan.pricingTier
  } : {
    pricingTier: plan.pricingTier
    subPlan: plan.subPlan
  }
}]

output budgetId string = monthlyBudgetAmount > 0 && length(budgetContactEmails) > 0 ? budget.id : ''
output roleAssignmentIds string[] = [for assignment in subscriptionRoleAssignments: assignment.id]
output policyAssignmentIds string[] = [for assignment in subscriptionPolicyAssignments: assignment.id]
output defenderPlanIds string[] = [for plan in defenderForCloudPlans: plan.id]