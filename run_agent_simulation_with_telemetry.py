#!/usr/bin/env python3
"""
AI Agent Simulation with Azure Application Insights Telemetry
Demonstrates all AI agents with real metrics tracking in Azure Monitor
"""

import asyncio
import os
import sys
import time
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

# Suppress encoding warnings for Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Try to import Application Insights
try:
    from opencensus.ext.azure.log_exporter import AzureLogHandler
    from opencensus.ext.azure import metrics_exporter
    from opencensus.stats import aggregation as aggregation_module
    from opencensus.stats import measure as measure_module
    from opencensus.stats import stats as stats_module
    from opencensus.stats import view as view_module
    from opencensus.tags import tag_map as tag_map_module
    import logging
    
    TELEMETRY_AVAILABLE = True
except ImportError:
    TELEMETRY_AVAILABLE = False
    print("\nNote: Application Insights telemetry not available")
    print("Install with: pip install opencensus-ext-azure opencensus")


class AzureAITelemetry:
    """Helper class to send telemetry to Azure Application Insights"""
    
    def __init__(self):
        self.connection_string = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
        self.enabled = bool(self.connection_string and TELEMETRY_AVAILABLE)
        self.logger = None
        self.stats = None
        self.exporter = None
        
        if not TELEMETRY_AVAILABLE:
            print("\nAzure Application Insights: NOT INSTALLED")
            print("To enable telemetry:")
            print("  1. Run: pip install opencensus-ext-azure opencensus")
            print("  2. Add APPLICATIONINSIGHTS_CONNECTION_STRING to .env")
            return
        
        if self.enabled:
            try:
                # Setup logging handler
                self.logger = logging.getLogger(__name__)
                self.logger.setLevel(logging.INFO)
                handler = AzureLogHandler(connection_string=self.connection_string)
                self.logger.addHandler(handler)
                
                # Setup metrics
                self.stats = stats_module.stats
                self.view_manager = self.stats.view_manager
                self.stats_recorder = self.stats.stats_recorder
                
                # Create metrics exporter
                self.exporter = metrics_exporter.new_metrics_exporter(
                    connection_string=self.connection_string
                )
                
                # Create measures
                self.agent_duration_measure = measure_module.MeasureFloat(
                    "agent_duration_ms",
                    "Agent execution duration",
                    "ms"
                )
                
                self.agent_invocation_measure = measure_module.MeasureInt(
                    "agent_invocations",
                    "Agent invocation count",
                    "1"
                )
                
                # Create views
                duration_view = view_module.View(
                    "agent_duration",
                    "Agent execution duration",
                    ["agent_name", "operation"],
                    self.agent_duration_measure,
                    aggregation_module.LastValueAggregation()
                )
                
                invocation_view = view_module.View(
                    "agent_invocation_count",
                    "Agent invocation count",
                    ["agent_name", "operation", "status"],
                    self.agent_invocation_measure,
                    aggregation_module.CountAggregation()
                )
                
                self.view_manager.register_view(duration_view)
                self.view_manager.register_view(invocation_view)
                self.view_manager.register_exporter(self.exporter)
                
                print(f"\nAzure Application Insights: ENABLED")
                print(f"Connection String: {self.connection_string[:50]}...")
                
            except Exception as e:
                print(f"\nAzure Application Insights: DISABLED ({e})")
                self.enabled = False
        else:
            print(f"\nAzure Application Insights: DISABLED")
            print("Set APPLICATIONINSIGHTS_CONNECTION_STRING in .env to enable")
    
    async def log_agent_invocation(self, agent_name: str, operation: str, properties: dict = None):
        """Log agent invocation to Azure Application Insights"""
        if not self.enabled:
            return
        
        try:
            # Log custom event
            props = {
                "agent_name": agent_name,
                "operation": operation,
                "timestamp": datetime.now().isoformat(),
                **(properties or {})
            }
            
            self.logger.info(
                f"Agent Invocation: {agent_name}",
                extra={"custom_dimensions": props}
            )
            
            print(f"  [Telemetry] Logged {agent_name} invocation")
            
        except Exception as e:
            print(f"  [Telemetry Error] {e}")
    
    async def log_agent_result(self, agent_name: str, success: bool, duration_ms: float, metrics: dict = None):
        """Log agent execution result"""
        if not self.enabled:
            return
        
        try:
            status = "success" if success else "failed"
            
            # Log result
            props = {
                "agent_name": agent_name,
                "success": success,
                "status": status,
                "duration_ms": duration_ms,
                "timestamp": datetime.now().isoformat(),
                **(metrics or {})
            }
            
            self.logger.info(
                f"Agent Result: {agent_name} - {status.upper()}",
                extra={"custom_dimensions": props}
            )
            
            # Record metrics
            mmap = self.stats_recorder.new_measurement_map()
            tmap = tag_map_module.TagMap()
            tmap.insert("agent_name", agent_name)
            tmap.insert("operation", metrics.get("operation", "execute") if metrics else "execute")
            tmap.insert("status", status)
            
            mmap.measure_float_put(self.agent_duration_measure, duration_ms)
            mmap.measure_int_put(self.agent_invocation_measure, 1)
            mmap.record(tmap)
            
            print(f"  [Telemetry] Logged {agent_name} result: {status.upper()} ({duration_ms:.0f}ms)")
            
        except Exception as e:
            print(f"  [Telemetry Error] {e}")


# Global telemetry instance
telemetry = AzureAITelemetry()


async def simulate_route_optimization_agent():
    """Simulate Route Optimization Agent with telemetry"""
    print("\n" + "="*70)
    print("AGENT 1: ROUTE OPTIMIZATION AGENT (Azure Maps)")
    print("="*70)
    
    start_time = time.time()
    
    from services.maps import BingMapsRouter
    from config.depots import get_depot_manager
    
    router = BingMapsRouter()
    depot_mgr = get_depot_manager()
    
    melbourne_addresses = [
        "100 Collins Street, Melbourne VIC 3000",
        "250 Flinders Street, Melbourne VIC 3000",
        "50 Bourke Street, Melbourne VIC 3000",
        "150 Lonsdale Street, Melbourne VIC 3000",
        "300 Queen Street, Melbourne VIC 3000",
        "75 Spencer Street, Melbourne VIC 3004",
        "200 Victoria Street, Carlton VIC 3053",
        "88 Acland Street, St Kilda VIC 3182",
    ]
    
    start_depot = depot_mgr.get_depot_for_addresses(melbourne_addresses)
    
    # Log invocation
    await telemetry.log_agent_invocation(
        "Route Optimization Agent",
        "optimize_route",
        {
            "delivery_count": len(melbourne_addresses),
            "depot": start_depot,
            "state": "VIC"
        }
    )
    
    print(f"\nScenario: Optimizing {len(melbourne_addresses)} Melbourne deliveries")
    print(f"Selected Depot: {start_depot}")
    print(f"Delivery Stops: {len(melbourne_addresses)}")
    print("\nOptimizing route with Azure Maps API...")
    
    route_info = router.optimize_route(melbourne_addresses, start_depot)
    
    duration_ms = (time.time() - start_time) * 1000
    
    if route_info:
        print(f"\nRoute Optimization Results:")
        print(f"  Total Distance: {route_info.get('total_distance_km', 0):.2f} km")
        print(f"  Total Duration: {route_info.get('total_duration_minutes', 0):.1f} minutes")
        print(f"  Route Optimized: {route_info.get('optimized', False)}")
        print(f"  Traffic Considered: {route_info.get('traffic_considered', False)}")
        
        # Log success
        await telemetry.log_agent_result(
            "Route Optimization Agent",
            True,
            duration_ms,
            {
                "distance_km": route_info.get('total_distance_km', 0),
                "duration_min": route_info.get('total_duration_minutes', 0),
                "optimized": route_info.get('optimized', False),
                "waypoint_count": len(route_info.get('waypoints', []))
            }
        )
        
        print("\nOptimized Route Order:")
        for i, waypoint in enumerate(route_info.get('waypoints', [])[:5], 1):
            print(f"  {i}. {waypoint}")
        if len(route_info.get('waypoints', [])) > 5:
            print(f"  ... and {len(route_info.get('waypoints', [])) - 5} more stops")
    else:
        await telemetry.log_agent_result(
            "Route Optimization Agent",
            False,
            duration_ms,
            {"error": "API unavailable"}
        )
    
    return route_info


async def simulate_smart_notification_agent():
    """Simulate Smart Notification Agent with telemetry"""
    print("\n" + "="*70)
    print("AGENT 2: SMART NOTIFICATION AGENT")
    print("="*70)
    
    from logistics_ai import SmartNotificationAgent
    
    agent = SmartNotificationAgent()
    
    scenarios = [
        {
            "parcel_id": "PKG123456",
            "customer_name": "Sarah Johnson",
            "customer_phone": "+61 2 9250 7111",
            "context": {"type": "delivery_window", "urgency": "medium"}
        },
        {
            "parcel_id": "PKG789012",
            "customer_name": "Michael Chen",
            "customer_phone": "+61 2 9240 8500",
            "context": {"type": "delay", "urgency": "high", "delay_minutes": 30, "delay_reason": "Traffic"}
        }
    ]
    
    print(f"\nGenerating {len(scenarios)} contextual notifications...\n")
    
    for scenario in scenarios:
        start_time = time.time()
        
        # Log invocation
        await telemetry.log_agent_invocation(
            "Smart Notification Agent",
            "generate_notification",
            {"parcel_id": scenario["parcel_id"], "notification_type": scenario["context"]["type"]}
        )
        
        notification = await agent.generate_proactive_notification(
            parcel_id=scenario["parcel_id"],
            customer_name=scenario["customer_name"],
            customer_phone=scenario["customer_phone"],
            context=scenario["context"]
        )
        
        duration_ms = (time.time() - start_time) * 1000
        
        print(f"Notification for {scenario['customer_name']}:")
        print(f"  Type: {notification.notification_type}")
        print(f"  Urgency: {notification.urgency}, Channel: {notification.channel}")
        print()
        
        # Log result
        await telemetry.log_agent_result(
            "Smart Notification Agent",
            True,
            duration_ms,
            {
                "notification_type": notification.notification_type,
                "urgency": notification.urgency,
                "channel": notification.channel,
                "confidence": notification.confidence_score
            }
        )


async def simulate_exception_resolution_agent():
    """Simulate Exception Resolution Agent with telemetry"""
    print("\n" + "="*70)
    print("AGENT 3: EXCEPTION RESOLUTION AGENT")
    print("="*70)
    
    from logistics_ai import ExceptionResolutionAgent, ExceptionType
    
    agent = ExceptionResolutionAgent()
    
    exceptions = [
        {"parcel_id": "PKG12345", "type": ExceptionType.ACCESS_ISSUE},
        {"parcel_id": "PKG67890", "type": ExceptionType.CUSTOMER_NOT_HOME},
        {"parcel_id": "PKG54321", "type": ExceptionType.WRONG_ADDRESS}
    ]
    
    print(f"\nResolving {len(exceptions)} delivery exceptions...\n")
    
    for exception in exceptions:
        start_time = time.time()
        
        # Log invocation
        await telemetry.log_agent_invocation(
            "Exception Resolution Agent",
            "resolve_exception",
            {"parcel_id": exception["parcel_id"], "exception_type": exception["type"].value}
        )
        
        resolution = await agent.analyze_and_resolve(
            parcel_id=exception["parcel_id"],
            exception_type=exception["type"]
        )
        
        duration_ms = (time.time() - start_time) * 1000
        
        print(f"Exception: {exception['type'].value}")
        print(f"  Resolution: {resolution.recommended_action.value}, Auto-executable: {resolution.auto_executable}")
        print()
        
        # Log result
        await telemetry.log_agent_result(
            "Exception Resolution Agent",
            True,
            duration_ms,
            {
                "exception_type": exception["type"].value,
                "resolution_action": resolution.recommended_action.value,
                "auto_executable": resolution.auto_executable,
                "confidence": resolution.confidence_score
            }
        )


async def simulate_manifest_generation_agent():
    """Simulate Manifest Generation Agent with telemetry"""
    print("\n" + "="*70)
    print("AGENT 4: MANIFEST GENERATION AGENT")
    print("="*70)
    
    start_time = time.time()
    
    from agents.manifest import ManifestGenerationAgent, Driver, ManifestParcel
    
    agent = ManifestGenerationAgent()
    
    drivers = [
        Driver(driver_id="DRV001", name="John Smith", max_capacity=20),
        Driver(driver_id="DRV002", name="Maria Garcia", max_capacity=20)
    ]
    
    parcels = [
        ManifestParcel(
            parcel_id=f"PKG{i:04d}",
            tracking_number=f"TRK{i:04d}",
            recipient_address=f"{100+i*50} Collins Street, Melbourne VIC 3000",
            postcode="3000",
            delivery_priority=1 if i % 3 == 0 else 2,
            estimated_delivery_time_min=15,
            requires_signature=i % 5 == 0,
            value_dollars=50.0 + i * 10
        )
        for i in range(1, 16)  # 15 parcels
    ]
    
    # Log invocation
    await telemetry.log_agent_invocation(
        "Manifest Generation Agent",
        "generate_manifests",
        {"driver_count": len(drivers), "parcel_count": len(parcels)}
    )
    
    print(f"\nGenerating manifests for {len(drivers)} drivers with {len(parcels)} parcels...")
    
    result = await agent.generate_optimized_manifests(
        parcels=parcels,
        available_drivers=drivers,
        date=datetime.now().strftime("%Y-%m-%d"),
        dc_location=None
    )
    
    duration_ms = (time.time() - start_time) * 1000
    
    print(f"\nManifest Generation Results:")
    print(f"  Manifests: {len(result.manifests)}, Parcels Assigned: {result.total_parcels_assigned}")
    print(f"  Efficiency: {result.average_route_efficiency:.0%}, Confidence: {result.confidence_score:.0%}")
    
    # Log result
    await telemetry.log_agent_result(
        "Manifest Generation Agent",
        True,
        duration_ms,
        {
            "manifests_generated": len(result.manifests),
            "parcels_assigned": result.total_parcels_assigned,
            "efficiency": result.average_route_efficiency,
            "confidence": result.confidence_score
        }
    )




async def main():
    """Run complete agent simulation with Azure Application Insights telemetry"""
    print("\n" + "="*70)
    print(" DT LOGISTICS - AI AGENT SIMULATION")
    print(" With Azure Application Insights Telemetry")
    print("="*70)
    print(f"\nSimulation Start: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Run agent simulations with telemetry
        await simulate_route_optimization_agent()
        await simulate_smart_notification_agent()
        await simulate_exception_resolution_agent()
        await simulate_manifest_generation_agent()
        
        print("\n" + "="*70)
        print("SIMULATION COMPLETE")
        print("="*70)
        print(f"\nEnd Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        if telemetry.enabled:
            print("\nTelemetry Status: SENT TO AZURE APPLICATION INSIGHTS")
            print(f"Connection String: {telemetry.connection_string[:50]}...")
            print("\nView metrics in Azure Portal:")
            print("  1. Go to Azure Portal")
            print("  2. Open Application Insights resource")
            print("  3. Check 'Logs' for custom events")
            print("  4. Check 'Metrics' for agent performance")
            print("  5. Use query: customEvents | where name contains 'Agent'")
        else:
            if not TELEMETRY_AVAILABLE:
                print("\nTelemetry Status: NOT INSTALLED")
                print("To enable telemetry:")
                print("  1. Run: pip install opencensus-ext-azure opencensus")
                print("  2. Add APPLICATIONINSIGHTS_CONNECTION_STRING to .env")
                print("  3. Get connection string from Azure Portal > Application Insights")
            else:
                print("\nTelemetry Status: LOCAL ONLY (Application Insights not configured)")
                print("To enable telemetry, set APPLICATIONINSIGHTS_CONNECTION_STRING in .env")
        
        print("\n" + "="*70)
        
        # Give telemetry time to flush
        if telemetry.enabled:
            print("\nFlushing telemetry to Azure...")
            await asyncio.sleep(5)
            print("Telemetry flush complete")
        
    except Exception as e:
        print(f"\nSimulation Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

