# Zava Azure Infrastructure Deployment Plan

## Status

Planning

## Mode

Modify the existing Zava AI Logistics Azure infrastructure.

## Goal

Author and validate Bicep for the Azure topology shown in the supplied architecture screenshot, using the repository's existing modular Bicep implementation as the baseline.

## Screenshot Resource Mapping

| Screenshot resource | Planned Bicep owner |
|---|---|
| Azure Workbook | To be verified and added if absent |
| Azure Cosmos DB account | `infra/modules/backend.bicep` |
| Azure AI Services / Foundry resource | `infra/modules/middleware.bicep` |
| Azure Machine Learning / Foundry hub workspace | `infra/modules/middleware.bicep` |
| Foundry project workspace | `infra/modules/middleware.bicep` |
| Speech service | `infra/modules/shared.bicep` |
| Vision service | `infra/modules/shared.bicep` |
| Azure Maps account | `infra/modules/shared.bicep` |
| App Service | `infra/modules/frontend.bicep` |
| App Service plan | `infra/modules/frontend.bicep` |
| Application Insights | `infra/modules/frontend.bicep` |
| Smart Detection alert rule and action group | To be verified and added if absent |
| Storage account | `infra/modules/middleware.bicep` |

## Planned Changes

1. Compare the screenshot with the existing modules and identify only missing or invalid resources and relationships.
2. Add any missing monitoring resources represented in the screenshot.
3. Correct deployment scope, dependencies, outputs, RBAC, and documentation where required for a coherent subscription-scoped deployment.
4. Keep managed identity and local-auth restrictions where supported.
5. Validate every touched module and the subscription entry point with the Bicep compiler.
6. Update deployment documentation with the correct command and parameters.

## Constraints

- Reuse the existing four-resource-group modular architecture.
- Preserve existing application-facing output names and resource naming conventions where practical.
- Do not deploy resources in this task.
- Do not overwrite unrelated user changes.

## Validation

- Compile each touched `.bicep` module.
- Compile `infra/main.bicep`.
- Review compiler diagnostics and resolve errors introduced or exposed by the change.
- Verify documentation uses subscription-scope deployment commands.

## Deployment

Not requested. Any deployment requires a separate validated handoff and explicit Azure subscription/location confirmation.
