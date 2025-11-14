# About: Create persistent Foundry agents for Last Mile Logistics Parcel Tracking
# Creates three specialized agents: Parcel Intake Agent, Sorting Facility Agent V2, and Delivery Coordination Agent V2
# These agents work together in a sequential workflow to manage parcel tracking from store registration through delivery
# Ref: https://learn.microsoft.com/en-us/agent-framework/user-guide/agents/agent-types/azure-ai-foundry-agent?pivots=programming-language-python#creating-and-managing-persistent-agents 

import os
import asyncio
from random import randint
from typing import Annotated

from agent_framework.azure import AzureAIAgentClient
from azure.identity.aio import AzureCliCredential
from azure.ai.projects.aio import AIProjectClient
from agent_framework import ChatAgent
from pydantic import Field

from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

AZURE_AI_PROJECT_ENDPOINT = os.getenv("AZURE_AI_PROJECT_ENDPOINT")
AZURE_AI_MODEL_DEPLOYMENT_NAME = os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME")

async def main():
    async with (
        AzureCliCredential() as credential,
        AIProjectClient(
            endpoint=AZURE_AI_PROJECT_ENDPOINT, 
            credential=credential
        ) as project_client,
    ):
        
        # Note: You can also list existing agents here to get their IDs, then delete them if needed before creating new ones
        # e.g. project_client.agents.list_agents()

        # Create a persistent agent for Parcel Intake
        parcel_intake_agent = await project_client.agents.create_agent(
            model=AZURE_AI_MODEL_DEPLOYMENT_NAME,
            name="Parcel Intake Agent",
            instructions='''Process new parcels from store intake operations. 
            Analyze parcel data including tracking numbers, sender/recipient information, service types, and package specifications.
            Identify any data anomalies or missing information in parcel registrations.
            Check for duplicate tracking numbers or invalid package details.
            Summarize findings in a structured format: [Status: Valid/Invalid], [Details: Parcel data validation results], [Action Required: None/Data Correction].
            Always pass parcel analysis results to the Sorting Facility Agent for routing decisions.
            Do not make up facts, be concise and to the point.''',
            description='An agent that processes and validates new parcel registrations from store intake operations.',            
            temperature=0.0,
            # tools=get_data # Tool registration not yet supported in create_agent API. Specify tools when using the agent (ChatAgent) as below.
        )

        # Create a persistent agent for Sorting Facility with Human Approval
        sorting_facility_agent = await project_client.agents.create_agent(
            model=AZURE_AI_MODEL_DEPLOYMENT_NAME,
            name="Sorting Facility Agent V2",
            instructions='''Review parcel analysis report from Parcel Intake Agent and manage parcel routing through sorting facilities.
            Assess parcel routing requirements based on destination postcodes, service types, and special handling needs.
            Identify delivery exceptions: damaged packages, incorrect addresses, special handling violations, or delivery restrictions.
            Determine recommended action: [Route Normally], [Request Special Handling], [Return to Sender], or [Hold for Investigation].
            For critical actions like [Request Special Handling], [Return to Sender], or [Hold for Investigation], request supervisor approval.
            Provide a concise routing summary and forward it to Delivery Coordination Agent.
            Do not make up facts, be concise and to the point.''',
            description='An agent that manages parcel routing through sorting facilities and handles delivery exceptions, initiates supervisor approval for critical actions.',
            temperature=0.0,
            # tools=get_data # Tool registration not yet supported in create_agent API. Specify tools when using the agent (ChatAgent) as below.
        )

        # Create a persistent agent for Delivery Coordination with Human Approval
        delivery_coordination_agent = await project_client.agents.create_agent(
            model=AZURE_AI_MODEL_DEPLOYMENT_NAME,
            name="Delivery Coordination Agent V2",
            instructions='''Based on the routing summary from Sorting Facility Agent, coordinate delivery assignments and manage delivery exceptions.
            If action is [Route Normally], assign parcels to delivery drivers (DRV001, DRV002, etc.).
            If [Request Special Handling], coordinate with specialized delivery teams.
            If [Return to Sender] or [Hold for Investigation], manage exception handling procedures.
            For delivery failures or damaged packages, send appropriate alerts and notifications.
            Critical actions like [Return to Sender], [Special Handling], or [Exception Processing] require supervisor approval result [APPROVED].
            Do nothing when approval result is [REJECTED] or when waiting on approval result.
            You can retrieve supervisor approval status. Say [PENDING] if approval is required but not yet granted.
            Confirm the delivery assignment or exception action and output a final status report.
            Do not make up facts, be concise and to the point.''',
            description='An agent that coordinates delivery assignments and manages delivery exceptions, checks supervisor approval for critical actions.',
            temperature=0.0,
            # tools=get_data # Tool registration not yet supported in create_agent API. Specify tools when using the agent (ChatAgent) as below.
        )

        # Print the new logistics agent IDs for use in W04_Sequential_Workflow_Human_Approval.py
        print(f'parcel_intake_agent.id: {parcel_intake_agent.id}') # Parcel Intake Agent        
        print(f'sorting_facility_agent.id: {sorting_facility_agent.id}') # Sorting Facility Agent with supervisor approval
        print(f'delivery_coordination_agent.id: {delivery_coordination_agent.id}') # Delivery Coordination Agent with supervisor approval

asyncio.run(main())