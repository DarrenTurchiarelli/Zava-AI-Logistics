# main.py
# Main entry point for the modular logistics operations center

import asyncio
from logistics_common import setup_warning_suppression
from logistics_menu import display_menu, check_environment, print_header

# Import all feature modules
from logistics_core import (
    register_parcel_manually, register_sample_parcels, view_all_parcels,
    track_parcel, scan_parcel_at_location_demo, generate_test_data,
    simulate_logistics_operations, run_agent_workflow
)
from logistics_customer import (
    manage_delivery_preferences, subscribe_to_notifications,
    report_suspicious_message, post_delivery_feedback
)
from logistics_driver import (
    verify_courier_identity, complete_proof_of_delivery,
    offline_mode_operations
)
from logistics_depot import (
    build_close_manifest, exception_resolution, system_integrations
)
from logistics_ai import (
    recalculate_route_eta, chaos_simulator, insights_dashboard
)
from logistics_admin import (
    bulk_import_parcels, export_manifests, rbac_audit,
    synthetic_scenario_builder, view_pending_approvals
)

async def main():
    """Main application loop with modular feature routing"""
    print_header()
    
    # Check environment variables
    if not check_environment():
        return

    try:
        while True:
            display_menu()
            
            choice = input("\n👉 Select an option (0-25): ").strip()
            
            try:
                if choice == '0':
                    print("👋 Exiting advanced logistics operations center...")
                    break
                    
                # Core Operations (1-6)
                elif choice == "1":
                    await register_parcel_manually()
                elif choice == "2":
                    await register_sample_parcels()
                elif choice == "3":
                    await view_all_parcels()
                elif choice == "4":
                    await track_parcel()
                elif choice == "5":
                    await scan_parcel_at_location_demo()
                elif choice == "6":
                    await generate_test_data()
                
                # Customer & Delivery Experience (7-10)
                elif choice == "7":
                    await manage_delivery_preferences()
                elif choice == "8":
                    await subscribe_to_notifications()
                elif choice == "9":
                    await report_suspicious_message()
                elif choice == "10":
                    await post_delivery_feedback()
                
                # Driver & Proof-of-Delivery (11-13)
                elif choice == "11":
                    await verify_courier_identity()
                elif choice == "12":
                    await complete_proof_of_delivery()
                elif choice == "13":
                    await offline_mode_operations()
                
                # Depot & Operations (14-16)
                elif choice == "14":
                    await build_close_manifest()
                elif choice == "15":
                    await exception_resolution()
                elif choice == "16":
                    await system_integrations()
                
                # AI & Intelligence (17-20)
                elif choice == "17":
                    await run_agent_workflow()
                elif choice == "18":
                    await recalculate_route_eta()
                elif choice == "19":
                    await chaos_simulator()
                elif choice == "20":
                    await insights_dashboard()
                
                # Data & Administration (21-25)
                elif choice == "21":
                    await bulk_import_parcels()
                elif choice == "22":
                    await export_manifests()
                elif choice == "23":
                    await rbac_audit()
                elif choice == "24":
                    await synthetic_scenario_builder()
                elif choice == "25":
                    await view_pending_approvals()
                
                else:
                    print("❌ Invalid choice. Please select 0-25.")
                    
            except KeyboardInterrupt:
                print("\n\n👋 Operations interrupted. Goodbye!")
                break
            except Exception as e:
                # Filter out connection cleanup warnings
                if "SSL shutdown timed out" not in str(e) and "Connection lost" not in str(e):
                    print(f"❌ Error: {e}")
                    
            # Pause before showing menu again
            input("\n⏸️ Press Enter to continue...")
                    
    finally:
        # Clean exit - allow time for connection cleanup
        await asyncio.sleep(0.2)
        print("🎉 Operations session completed cleanly.")

if __name__ == "__main__":
    # Initialize warning suppression
    setup_warning_suppression()
    
    # Run the application
    asyncio.run(main())