# About: Create persistent Foundry agents for Last Mile Logistics Parcel Tracking
# Creates six specialized agents for comprehensive logistics operations:
# 1-3: Original workflow agents (Intake, Sorting, Delivery Coordination)
# 4-6: Enhanced logistics agents (Dispatcher, Driver, Optimization, Customer Service, Fraud & Risk, Identity)
# These agents work together in workflows to manage complete parcel tracking and delivery operations
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

        print("🚀 Creating Comprehensive Logistics Agent Suite...")
        print("=" * 60)
        
        # === ORIGINAL WORKFLOW AGENTS (1-3) ===

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
        )

        # Create a persistent agent for Sorting Facility with Human Approval
        sorting_facility_agent = await project_client.agents.create_agent(
            model=AZURE_AI_MODEL_DEPLOYMENT_NAME,
            name="Sorting Facility Agent",
            instructions='''Review parcel analysis report from Parcel Intake Agent and manage parcel routing through sorting facilities.
            Assess parcel routing requirements based on destination postcodes, service types, and special handling needs.
            Identify delivery exceptions: damaged packages, incorrect addresses, special handling violations, or delivery restrictions.
            Determine recommended action: [Route Normally], [Request Special Handling], [Return to Sender], or [Hold for Investigation].
            For critical actions like [Request Special Handling], [Return to Sender], or [Hold for Investigation], request supervisor approval.
            Provide a concise routing summary and forward it to Delivery Coordination Agent.
            Do not make up facts, be concise and to the point.''',
            description='An agent that manages parcel routing through sorting facilities and handles delivery exceptions, initiates supervisor approval for critical actions.',
            temperature=0.0,
        )

        # Create a persistent agent for Delivery Coordination with Human Approval
        delivery_coordination_agent = await project_client.agents.create_agent(
            model=AZURE_AI_MODEL_DEPLOYMENT_NAME,
            name="Delivery Coordination Agent",
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
        )
        
        # === ENHANCED LOGISTICS AGENTS (4-6) ===

        # 4. Dispatcher Agent - Route and Driver Assignment
        dispatcher_agent = await project_client.agents.create_agent(
            model=AZURE_AI_MODEL_DEPLOYMENT_NAME,
            name="Dispatcher Agent",
            instructions='''Optimize parcel-to-route assignments and driver allocations based on capacity constraints and SLA requirements.
            Analyze delivery volumes, driver availability, vehicle capacity, and service level agreements.
            Consider geographic proximity, traffic patterns, and delivery time windows when assigning routes.
            Balance workload across drivers while ensuring on-time delivery commitments.
            For high-priority or express parcels, prioritize optimal routing and flag potential delays.
            Generate route manifests and driver assignments with estimated delivery windows.
            Escalate capacity issues or SLA risks to operations management.
            Output format: [Route ID], [Driver Assigned], [Estimated Completion], [Capacity Utilization], [SLA Status].
            Be concise and focus on operational efficiency.''',
            description='Optimizes parcel routing and driver assignments based on capacity and SLA requirements.',
            temperature=0.1,
        )

        # 5. Driver Agent - Delivery Execution and Proof of Delivery
        driver_agent = await project_client.agents.create_agent(
            model=AZURE_AI_MODEL_DEPLOYMENT_NAME,
            name="Driver Agent",
            instructions='''Execute delivery scans, manage proof-of-delivery, and handle real-time delivery scenarios.
            Process parcel scans at pickup, transit, and delivery points with location verification.
            Capture proof-of-delivery including signatures, photos, and recipient verification.
            Handle delivery exceptions: customer not home, incorrect address, damaged parcel, access issues.
            Request rerouting assistance for blocked roads, vehicle issues, or delivery problems.
            Support offline operations when connectivity is limited - queue scans for later sync.
            Communicate delivery status updates and estimated arrival times to customers.
            Flag suspicious delivery requests or security concerns to fraud detection.
            Output format: [Scan Type], [Location], [Timestamp], [Status], [Next Action Required].
            Be practical and focus on delivery execution.''',
            description='Manages delivery execution, proof-of-delivery, and real-time delivery scenarios.',
            temperature=0.1,
        )

        # 6. Optimization Agent - ETA and Route Intelligence
        optimization_agent = await project_client.agents.create_agent(
            model=AZURE_AI_MODEL_DEPLOYMENT_NAME,
            name="Optimization Agent",
            instructions='''Predict accurate ETAs and optimize routes based on real-time conditions and disruptions.
            Calculate delivery estimates considering traffic patterns, weather conditions, and route complexity.
            React to disruptions: road closures, vehicle breakdowns, driver delays, or surge capacity events.
            Recommend route adjustments, parcel locker diversions, or next-day delivery options.
            Optimize for multiple objectives: on-time delivery, fuel efficiency, driver satisfaction, and CO₂ reduction.
            Provide "running early/late" alerts with updated ETA predictions.
            Suggest contingency plans for high-impact disruptions or weather events.
            Monitor delivery performance metrics and identify improvement opportunities.
            Output format: [Updated ETA], [Route Changes], [Optimization Score], [Environmental Impact], [Recommendations].
            Be analytical and focus on continuous improvement.''',
            description='Provides ETA predictions and route optimization based on real-time conditions.',
            temperature=0.2,
        )

        # 7. Customer Service Agent - Exception Handling and Communications
        customer_service_agent = await project_client.agents.create_agent(
            model=AZURE_AI_MODEL_DEPLOYMENT_NAME,
            name="Customer Service Agent",
            instructions='''Handle delivery exceptions and manage customer communications across multiple channels.
            Resolve common issues: delivery preferences, address changes, failed deliveries, damaged parcels.
            Provide options: "leave at reception", "deliver tomorrow", "redirect to parcel locker", "return to sender".
            Send proactive notifications via SMS, email, or app with accurate delivery updates.
            Manage delivery preferences: authority-to-leave, safe-drop locations, secure locker preferences.
            Handle post-delivery feedback collection and NPS surveys.
            Escalate complex issues or complaints to human customer service representatives.
            Maintain empathetic and helpful communication tone while providing practical solutions.
            Output format: [Issue Type], [Resolution Option], [Customer Communication], [Follow-up Required], [Satisfaction Score].
            Be customer-focused and solution-oriented.''',
            description='Handles customer exceptions, communications, and delivery preference management.',
            temperature=0.3,
        )

        # 8. Fraud & Risk Agent - Security and Scam Detection
        fraud_risk_agent = await project_client.agents.create_agent(
            model=AZURE_AI_MODEL_DEPLOYMENT_NAME,
            name="Fraud & Risk Agent",
            instructions='''Detect suspicious activities, fraudulent communications, and security risks in logistics operations.
            Identify potential scam messages, phishing attempts, or fraudulent delivery requests.
            Flag unusual patterns: multiple delivery redirections, suspicious addresses, payment anomalies.
            Educate customers about common delivery scams and security best practices.
            Monitor for identity theft attempts, package theft patterns, or courier impersonation.
            Verify high-value deliveries and flag packages requiring additional security measures.
            Coordinate with identity verification for suspicious delivery attempts.
            Generate security alerts and provide risk mitigation recommendations.
            Output format: [Risk Level], [Threat Type], [Recommended Action], [Customer Education], [Security Alert].
            Be vigilant and security-focused while maintaining operational efficiency.''',
            description='Monitors security risks, detects fraud patterns, and educates users about scams.',
            temperature=0.1,
        )

        # 9. Identity Agent - Courier Verification and Authentication
        identity_agent = await project_client.agents.create_agent(
            model=AZURE_AI_MODEL_DEPLOYMENT_NAME,
            name="Identity Agent",
            instructions='''Verify courier identity and authenticate delivery personnel before package handoff.
            Validate courier credentials, employment verification, and authorized delivery zones.
            Perform liveness detection and identity verification for high-value or sensitive deliveries.
            Ensure only authorized personnel can access delivery vehicles and scan packages.
            Monitor for courier impersonation attempts or unauthorized delivery attempts.
            Integrate with biometric systems and verifiable credential platforms.
            Flag identity verification failures and trigger security protocols.
            Maintain audit trail of all courier verification activities for compliance.
            Output format: [Verification Status], [Courier ID], [Authentication Method], [Risk Assessment], [Compliance Status].
            Be thorough and security-focused with zero tolerance for identity irregularities.''',
            description='Manages courier identity verification and authentication for secure deliveries.',
            temperature=0.0,
        )

        # Print the comprehensive logistics agent IDs for use in workflows
        print("✅ Comprehensive Logistics Agent Suite Created Successfully!")
        print("=" * 60)
        print("\n📋 ORIGINAL WORKFLOW AGENTS:")
        print(f'📥 Parcel Intake Agent ID: {parcel_intake_agent.id}')
        print(f'📊 Sorting Facility Agent ID: {sorting_facility_agent.id}')
        print(f'🚚 Delivery Coordination Agent ID: {delivery_coordination_agent.id}')
        
        print("\n🎯 ENHANCED LOGISTICS AGENTS:")
        print(f'📊 Dispatcher Agent ID: {dispatcher_agent.id}')
        print(f'🚛 Driver Agent ID: {driver_agent.id}')
        print(f'🎯 Optimization Agent ID: {optimization_agent.id}')
        print(f'📞 Customer Service Agent ID: {customer_service_agent.id}')
        print(f'🛡️ Fraud & Risk Agent ID: {fraud_risk_agent.id}')
        print(f'🪪 Identity Agent ID: {identity_agent.id}')
        
        print("=" * 60)
        print("🔧 Copy these IDs into your workflow configuration files")
        print("📋 Ready for comprehensive logistics operations!")
        print("🚀 Total agents created: 9 (3 workflow + 6 enhanced)")

asyncio.run(main())