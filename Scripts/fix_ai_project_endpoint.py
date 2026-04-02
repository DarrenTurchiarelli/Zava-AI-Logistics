"""Fix AZURE_AI_PROJECT_ENDPOINT in .env file with correct project-specific endpoint"""
import os
from dotenv import load_dotenv

load_dotenv()

subscription_id = "728f99b5-49fe-47b9-9bcd-97d981ccdfa9"
resource_group = "RG-Zava-Middleware-dev"
workspace_name = "zava-dev-aiproject-bmwcty"

# Build correct project endpoint URL
correct_endpoint = f"https://australiaeast.api.azureml.ms/discovery/subscriptions/{subscription_id}/resourceGroups/{resource_group}/providers/Microsoft.MachineLearningServices/workspaces/{workspace_name}"

print("🔧 Updating AZURE_AI_PROJECT_ENDPOINT in .env")
print(f"\n❌ Current (generic discovery): https://australiaeast.api.azureml.ms/discovery")
print(f"\n✅ Correct (project-specific): {correct_endpoint}")

# Read current .env
with open('.env', 'r') as f:
    lines = f.readlines()

# Update the endpoint
updated = False
new_lines = []
for line in lines:
    if line.startswith('AZURE_AI_PROJECT_ENDPOINT='):
        new_lines.append(f'AZURE_AI_PROJECT_ENDPOINT={correct_endpoint}\n')
        updated = True
    else:
        new_lines.append(line)

# Write back
with open('.env', 'w') as f:
    f.writelines(new_lines)

if updated:
    print("\n✅ .env file updated successfully!")
else:
    print("\n⚠️  AZURE_AI_PROJECT_ENDPOINT not found in .env")

print("\n📋 Next step: Run 'python Scripts/list_agents.py' to verify")
