# TODO

## GitHub Actions — Wire up authentication for daily data generator

**File:** `.github/workflows/daily-data-generator.yml`

Pick one of the two options below and complete all steps before enabling the schedule.

---

### Option A — Connection String (simpler, fine for dev/demo)

- [ ] In Azure Portal → Cosmos DB → `zava-dev-cosmos-keqftv` → **Keys**  
      Copy the **PRIMARY CONNECTION STRING**
- [ ] In GitHub → Zava-Logistics repo → **Settings → Secrets and variables → Actions → New repository secret**  
      Name: `COSMOS_CONNECTION_STRING`  
      Value: *(paste the connection string)*
- [ ] In `.github/workflows/daily-data-generator.yml`, uncomment this line under `env:`:
      ```yaml
      COSMOS_CONNECTION_STRING: ${{ secrets.COSMOS_CONNECTION_STRING }}
      ```
- [ ] Commit and push

---

### Option B — Service Principal + RBAC (recommended for prod)

- [ ] Create a service principal:
      ```bash
      az ad sp create-for-rbac --name "zava-gh-actions" --sdk-auth
      ```
      Save the full JSON output — you need `appId`, `password`, `tenant`

- [ ] Get the Cosmos DB resource ID and service principal object ID:
      ```bash
      COSMOS_ID=$(az cosmosdb show --name zava-dev-cosmos-keqftv \
        --resource-group RG-Zava-Backend-dev --query id -o tsv)

      SP_OBJECT_ID=$(az ad sp show --id <appId-from-above> --query id -o tsv)
      ```

- [ ] Assign Cosmos DB Built-in Data Contributor role:
      ```bash
      az cosmosdb sql role assignment create \
        --account-name zava-dev-cosmos-keqftv \
        --resource-group RG-Zava-Backend-dev \
        --role-definition-name "Cosmos DB Built-in Data Contributor" \
        --scope "$COSMOS_ID" \
        --principal-id "$SP_OBJECT_ID"
      ```

- [ ] Add four GitHub repository secrets:

      | Secret name              | Value                                         |
      |--------------------------|-----------------------------------------------|
      | `AZURE_CLIENT_ID`        | `appId` from the sp create output             |
      | `AZURE_CLIENT_SECRET`    | `password` from the sp create output          |
      | `AZURE_TENANT_ID`        | `tenant` from the sp create output            |
      | `COSMOS_DB_ENDPOINT`     | `https://zava-dev-cosmos-keqftv.documents.azure.com:443/` |

- [ ] In `.github/workflows/daily-data-generator.yml`, uncomment the Option B block under `env:`:
      ```yaml
      AZURE_CLIENT_ID:          ${{ secrets.AZURE_CLIENT_ID }}
      AZURE_CLIENT_SECRET:      ${{ secrets.AZURE_CLIENT_SECRET }}
      AZURE_TENANT_ID:          ${{ secrets.AZURE_TENANT_ID }}
      COSMOS_DB_ENDPOINT:       ${{ secrets.COSMOS_DB_ENDPOINT }}
      COSMOS_DB_DATABASE_NAME:  logisticstracking
      ```
- [ ] Delete or comment out the Option A line

- [ ] Commit and push

---

### Final verification (both options)

- [ ] Add `AZURE_AI_PROJECT_ENDPOINT` secret (needed by the agents):  
      Value: your AI Foundry project endpoint from `.env`
- [ ] Go to **Actions** tab → **Daily Demo Data Generator** → **Run workflow** (manual trigger)  
      Confirm it completes without auth errors before relying on the schedule
