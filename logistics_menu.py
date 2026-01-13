"""
Zava - Menu and Environment Setup
Provides the main menu display and environment validation
"""

import os


def print_header():
    """Print the Zava header"""
    print("\n" + "=" * 70)
    print("🚚 Zava - Advanced Operations Center")
    print("=" * 70)
    print("AI-Powered Last-Mile Delivery Management System")
    print()


def check_environment():
    """Check if required environment variables are set"""
    required_vars = {
        "COSMOS_CONNECTION_STRING": "Azure Cosmos DB connection",
        "AZURE_AI_PROJECT_CONNECTION_STRING": "Azure AI Foundry project",
    }

    missing = []
    for var, description in required_vars.items():
        if not os.getenv(var):
            missing.append(f"  ❌ {var} ({description})")

    if missing:
        print("⚠️  Warning: Missing environment variables:")
        for msg in missing:
            print(msg)
        print("\nSome features may not work without proper configuration.")
        print("Set environment variables in PowerShell:")
        print('  $env:COSMOS_CONNECTION_STRING = "your_connection_string"')
        print('  $env:AZURE_AI_PROJECT_CONNECTION_STRING = "your_ai_connection"')
        print()

        response = input("Continue anyway? (y/n): ").strip().lower()
        if response != "y":
            return False
    else:
        print("✅ Environment variables configured")

    return True


def display_menu():
    """Display the main menu"""
    print("\n" + "=" * 70)
    print("📋 MAIN MENU")
    print("=" * 70)

    print("\n🔷 Core Operations (1-6)")
    print("  1. Register Parcel Manually")
    print("  2. Register Sample Parcels")
    print("  3. View All Parcels")
    print("  4. Track Parcel")
    print("  5. Scan Parcel at Location")
    print("  6. Generate Test Data")

    print("\n🔷 Customer & Delivery Experience (7-10)")
    print("  7. Manage Delivery Preferences")
    print("  8. Subscribe to Notifications")
    print("  9. Report Suspicious Message (Fraud Detection)")
    print(" 10. Post-Delivery Feedback")

    print("\n🔷 Driver & Proof-of-Delivery (11-13)")
    print(" 11. Verify Courier Identity")
    print(" 12. Complete Proof of Delivery")
    print(" 13. Offline Mode Operations")

    print("\n🔷 Depot & Operations (14-16)")
    print(" 14. Build & Close Manifest")
    print(" 15. Exception Resolution")
    print(" 16. System Integrations")

    print("\n🔷 AI & Intelligence (17-20)")
    print(" 17. Run AI Agent Workflow")
    print(" 18. Recalculate Route & ETA")
    print(" 19. Chaos Simulator")
    print(" 20. Insights Dashboard")

    print("\n🔷 Data & Administration (21-25)")
    print(" 21. Bulk Import Parcels")
    print(" 22. Export Manifests")
    print(" 23. RBAC Audit")
    print(" 24. Synthetic Scenario Builder")
    print(" 25. View Pending Approvals")

    print("\n🔷 Exit")
    print("  0. Exit Application")
    print("=" * 70)
