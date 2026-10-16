param(
    [string]$ProjectEndpoint = "https://zava-dev-aisvc-vurjkn.services.ai.azure.com/api/projects/zava-dev-aisvc-vurjkn-project",
    [string]$AppBaseUrl = "https://zava-dev-web-vurjkn.azurewebsites.net",
    [string]$ResourceGroup = "RG-Zava-Frontend-dev",
    [string]$AppServiceName = "zava-dev-web-vurjkn",
    [string]$FoundryResourceGroup = "RG-Zava-Middleware-dev",
    [string]$FoundryAccountName = "zava-dev-aisvc-vurjkn",
    [string]$FoundryProjectName = "zava-dev-aisvc-vurjkn-project",
    [string]$SubscriptionId = "728f99b5-49fe-47b9-9bcd-97d981ccdfa9",
    [string]$TenantId = "8919f557-d17d-4c0b-aa1b-3efb410323e0"
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path $PSScriptRoot -Parent
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    throw "Project Python environment not found: $python"
}

function New-ToolKey {
    $bytes = [byte[]]::new(32)
    [System.Security.Cryptography.RandomNumberGenerator]::Fill($bytes)
    return [Convert]::ToBase64String($bytes).TrimEnd('=').Replace('+', '-').Replace('/', '_')
}

function Get-OrCreate-AppSetting {
    param([string]$Name)

    $value = az webapp config appsettings list `
        --resource-group $ResourceGroup `
        --name $AppServiceName `
        --query "[?name=='$Name'].value | [0]" `
        --output tsv
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to read App Service setting $Name."
    }

    if (-not $value) {
        $value = New-ToolKey
        az webapp config appsettings set `
            --resource-group $ResourceGroup `
            --name $AppServiceName `
            --settings "$Name=$value" `
            --output none
        if ($LASTEXITCODE -ne 0) {
            throw "Unable to configure App Service setting $Name."
        }
    }
    return $value
}

function Set-FoundryToolConnection {
    param(
        [string]$ConnectionName,
        [string]$ApiKey
    )

    $connectionFile = New-TemporaryFile
    try {
        $body = @{
            properties = @{
                category = "RemoteTool"
                target = $AppBaseUrl
                authType = "CustomKeys"
                credentials = @{
                    keys = @{
                        "x-zava-tool-key" = $ApiKey
                    }
                }
            }
        }
        $body | ConvertTo-Json -Depth 10 | Set-Content -Path $connectionFile -Encoding utf8NoBOM
        $resourceId = "/subscriptions/$SubscriptionId/resourceGroups/$FoundryResourceGroup/providers/Microsoft.CognitiveServices/accounts/$FoundryAccountName/projects/$FoundryProjectName/connections/$ConnectionName"
        az rest `
            --method put `
            --url "https://management.azure.com${resourceId}?api-version=2025-12-01" `
            --body "@$connectionFile" `
            --output none
        if ($LASTEXITCODE -ne 0) {
            throw "Unable to create Foundry project connection $ConnectionName."
        }
    }
    finally {
        Remove-Item $connectionFile -Force -ErrorAction SilentlyContinue
    }
}

$readKey = Get-OrCreate-AppSetting "ZAVA_TOOL_READ_API_KEY"
$writeKey = Get-OrCreate-AppSetting "ZAVA_TOOL_WRITE_API_KEY"

Set-FoundryToolConnection "zava-logistics-read-api" $readKey
Set-FoundryToolConnection "zava-logistics-write-api" $writeKey

$env:AZURE_TENANT_ID = $TenantId
$env:AZURE_AI_PROJECT_ENDPOINT = $ProjectEndpoint
& $python (Join-Path $PSScriptRoot "create_foundry_toolboxes.py") `
    --project-endpoint $ProjectEndpoint `
    --app-base-url $AppBaseUrl `
    --tenant-id $TenantId
if ($LASTEXITCODE -ne 0) {
    throw "Foundry toolbox creation failed."
}