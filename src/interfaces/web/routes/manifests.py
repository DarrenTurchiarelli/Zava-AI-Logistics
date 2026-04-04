"""
Manifests Blueprint - Driver and Admin Manifest Management

Handles driver manifest views, admin manifest creation/management,
AI-powered auto-assignment, and real-time delivery tracking.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, Response, stream_with_context
from datetime import datetime
import re
import csv
from typing import Dict, Any, List
from pathlib import Path

from src.interfaces.web.middleware import login_required, role_required
from parcel_tracking_db import ParcelTrackingDB
from utils.async_helpers import run_async
from user_manager import UserManager
from src.infrastructure.agents import dispatcher_agent

manifests_bp = Blueprint('manifests', __name__)


@manifests_bp.route("/driver/manifest")
@login_required
def driver_manifest():
    """
    View driver's daily manifest
    
    Shows assigned parcels, optimized routes, and delivery progress.
    
    Access: Drivers see their own manifest, admin/depot managers can view any driver
    """
    try:
        user = session.get("user", {})

        # Determine driver_id based on user role
        if user.get("role") == UserManager.ROLE_DRIVER:
            driver_id = user.get("driver_id")
            if not driver_id:
                flash("Driver ID not configured. Contact administrator.", "danger")
                return render_template("driver_manifest.html", manifest=None)
        else:
            # Admin/depot manager can view any driver
            driver_id = request.args.get("driver_id", "driver-001")

        async def get_manifest():
            async with ParcelTrackingDB() as db:
                manifest = await db.get_driver_manifest(driver_id)

                # Handle Cosmos DB eventual consistency
                if manifest and not manifest.get("route_optimized"):
                    import time as time_module
                    for _ in range(4):
                        time_module.sleep(1.0)
                        manifest = await db.get_driver_manifest(driver_id)
                        if manifest.get("route_optimized"):
                            break

                return manifest

        manifest = run_async(get_manifest())

        if not manifest:
            flash(f"No active manifest for driver {driver_id}. Contact dispatch for assignment.", "info")
            return render_template("driver_manifest.html", manifest=None)

        # Check if initial route needs creation
        needs_initial_route = (not manifest.get("route_optimized")) and bool(manifest.get("items"))

        if needs_initial_route:
            # Create initial route synchronously
            manifest_id = manifest["id"]
            
            async def create_initial_route_sync():
                async with ParcelTrackingDB() as db:
                    addresses = list(set([item["recipient_address"] for item in manifest["items"]]))

                    from config.depots import get_depot_manager
                    from services.maps import BingMapsRouter

                    depot_mgr = get_depot_manager()
                    start_location = depot_mgr.get_closest_depot_to_address(addresses[0])

                    router = BingMapsRouter()
                    safest_route = router.optimize_route(addresses, start_location, route_type="safest")

                    if safest_route:
                        await db.update_manifest_route(
                            manifest_id,
                            safest_route["waypoints"],
                            safest_route["total_duration_minutes"],
                            safest_route["total_distance_km"],
                            is_optimized=safest_route.get("optimized", False),
                            traffic_considered=safest_route.get("traffic_considered", False),
                        )

                        # Refresh manifest
                        updated_manifest = await db.get_driver_manifest(driver_id)
                        return updated_manifest
                    
                    # Return original manifest if route creation failed
                    return manifest

            manifest = run_async(create_initial_route_sync())

        return render_template("driver_manifest.html", manifest=manifest)

    except Exception as e:
        flash(f"Error loading manifest: {str(e)}", "danger")
        return render_template("driver_manifest.html", manifest=None)


@manifests_bp.route("/driver/manifest/loading")
@login_required
def driver_manifest_loading():
    """
    Loading page with route optimization progress
    
    Redirects to manifest view when optimization completes.
    """
    return render_template("driver_manifest_loading.html")


@manifests_bp.route("/driver/manifest/<manifest_id>")
@login_required
def view_manifest(manifest_id: str):
    """
    View specific manifest by ID
    
    Access: Owner driver, admin, or depot manager
    """
    try:
        async def get_manifest_by_id():
            async with ParcelTrackingDB() as db:
                if not db.database:
                    await db.connect()

                container = db.database.get_container_client("driver_manifests")
                query = "SELECT * FROM c WHERE c.id = @manifest_id"
                parameters = [{"name": "@manifest_id", "value": manifest_id}]

                async for manifest in container.query_items(query=query, parameters=parameters):
                    return manifest
                return None

        manifest = run_async(get_manifest_by_id())

        if not manifest:
            flash("Manifest not found", "danger")
            return redirect(url_for("manifests.admin_manifests"))

        return render_template("manifest_details.html", manifest=manifest)

    except Exception as e:
        flash(f"Error loading manifest: {str(e)}", "danger")
        return redirect(url_for("manifests.admin_manifests"))


@manifests_bp.route("/driver/manifest/<manifest_id>/complete", methods=["POST"])
@login_required
def complete_delivery(manifest_id: str):
    """
    Mark parcel as delivered (placeholder for POST handler)
    
    Access: Driver who owns the manifest
    """
    # TODO: Implement delivery completion with photo proof
    flash("Delivery completion not yet implemented", "warning")
    return redirect(url_for("manifests.view_manifest", manifest_id=manifest_id))


@manifests_bp.route("/admin/manifests")
@role_required(UserManager.ROLE_ADMIN, UserManager.ROLE_DEPOT_MANAGER)
def admin_manifests():
    """
    View all active manifests (admin and depot managers only)
    
    Shows list of all driver manifests with status and parcel counts.
    """
    try:
        async def get_all_manifests():
            async with ParcelTrackingDB() as db:
                return await db.get_all_active_manifests()

        manifests = run_async(get_all_manifests())
        return render_template("admin_manifests.html", manifests=manifests)

    except Exception as e:
        flash(f"Error loading manifests: {str(e)}", "danger")
        return render_template("admin_manifests.html", manifests=[])


@manifests_bp.route("/admin/manifests/create", methods=["POST"])
@login_required
def create_manifest():
    """
    Create a new driver manifest
    
    Access: Admin and depot managers
    """
    try:
        driver_id = request.form.get("driver_id")
        driver_name = request.form.get("driver_name")
        manifest_reason = request.form.get("manifest_reason", "")
        barcode_list = request.form.get("barcodes", "").strip()

        # Parse barcodes (comma or newline separated)
        barcodes = [b.strip() for b in re.split(r"[,\n]", barcode_list) if b.strip()]

        if not barcodes:
            flash("No parcels selected for manifest", "warning")
            return redirect(url_for("manifests.admin_manifests"))

        async def create():
            async with ParcelTrackingDB() as db:
                # Look up driver's state from users database
                driver_state = await db.get_user_state(driver_id)
                return await db.create_driver_manifest(
                    driver_id, driver_name, barcodes, reason=manifest_reason, driver_state=driver_state
                )

        manifest_id = run_async(create())

        if manifest_id:
            flash(f"Manifest created successfully! ID: {manifest_id}", "success")
        else:
            flash("Error creating manifest", "danger")

        return redirect(url_for("manifests.admin_manifests"))

    except Exception as e:
        flash(f"Error: {str(e)}", "danger")
        return redirect(url_for("manifests.admin_manifests"))


@manifests_bp.route("/admin/manifests/auto_assign", methods=["POST"])
@role_required(UserManager.ROLE_ADMIN, UserManager.ROLE_DEPOT_MANAGER)
def auto_assign_manifests():
    """
    AI-powered automatic manifest creation using DISPATCHER_AGENT
    
    Intelligently assigns pending parcels to available drivers.
    
    Form Data:
        max_parcels (int): Maximum parcels to assign (default: 20)
        state_filter (str): Optional state filter for parcels
    """
    try:
        max_parcels = int(request.form.get("max_parcels", 20))
        state_filter = request.form.get("state_filter", "")

        async def auto_assign():
            async with ParcelTrackingDB() as db:
                # Get pending parcels
                pending_parcels = await db.get_pending_parcels(
                    status="at_depot", 
                    max_count=max_parcels, 
                    state=state_filter if state_filter else None
                )

                if not pending_parcels:
                    state_msg = f" in {state_filter}" if state_filter else ""
                    return {"success": False, "message": f"No pending parcels found{state_msg}"}

                # Get available drivers
                drivers = await db.get_available_drivers(state=state_filter if state_filter else None)

                if not drivers:
                    return {"success": False, "message": "No available drivers found"}

                # Filter drivers with existing manifests
                # TODO: Check for drivers with unfilled manifests
                
                # Prepare data for DISPATCHER_AGENT
                route_request = {
                    "parcel_count": len(pending_parcels),
                    "available_drivers": [d["driver_id"] for d in drivers],
                    "service_level": "standard",
                    "delivery_window": "08:00 - 18:00",
                    "zone": state_filter or "ALL",
                    "parcels": [
                        {
                            "barcode": p["barcode"],
                            "tracking_number": p.get("tracking_number", p["barcode"]),
                            "address": p["recipient_address"],
                            "postcode": p.get("postcode", ""),
                            "priority": p.get("priority", 2),
                            "recipient_name": p.get("recipient_name", ""),
                        }
                        for p in pending_parcels
                    ],
                }

                # Call DISPATCHER_AGENT
                agent_result = await dispatcher_agent(route_request)

                if not agent_result.get("success"):
                    # Fallback to round-robin
                    return await _fallback_round_robin_assignment(db, pending_parcels, drivers)

                # Parse AI recommendations and create manifests
                # TODO: Implement AI response parsing
                
                return {
                    "success": True,
                    "manifests_created": 0,
                    "parcels_assigned": 0,
                    "message": "Auto-assignment requires implementation"
                }

        result = run_async(auto_assign())

        if result.get("success"):
            flash(f"✅ Created {result.get('manifests_created', 0)} manifests", "success")
        else:
            flash(f"⚠️ {result.get('message', 'Auto-assign failed')}", "warning")

        return redirect(url_for("manifests.admin_manifests"))

    except Exception as e:
        flash(f"Error during auto-assign: {str(e)}", "danger")
        return redirect(url_for("manifests.admin_manifests"))


@manifests_bp.route("/admin/manifests/<manifest_id>", methods=["GET", "DELETE"])
@role_required(UserManager.ROLE_ADMIN, UserManager.ROLE_DEPOT_MANAGER)
def manage_manifest(manifest_id: str):
    """
    Get or delete specific manifest
    
    GET: Returns manifest details as JSON
    DELETE: Cancels and deletes the manifest
    """
    if request.method == "DELETE":
        # TODO: Implement manifest deletion
        return jsonify({"success": False, "message": "Delete not implemented"}), 501
    
    # GET
    try:
        async def get_manifest():
            async with ParcelTrackingDB() as db:
                if not db.database:
                    await db.connect()
                    
                container = db.database.get_container_client("driver_manifests")
                query = "SELECT * FROM c WHERE c.id = @manifest_id"
                parameters = [{"name": "@manifest_id", "value": manifest_id}]

                async for manifest in container.query_items(query=query, parameters=parameters):
                    return manifest
                return None

        manifest = run_async(get_manifest())
        
        if not manifest:
            return jsonify({"error": "Manifest not found"}), 404
        
        return jsonify(manifest), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@manifests_bp.route("/admin/manifests/<manifest_id>/edit", methods=["POST"])
@role_required(UserManager.ROLE_ADMIN, UserManager.ROLE_DEPOT_MANAGER)
def edit_manifest(manifest_id: str):
    """
    Edit manifest details (add/remove parcels)
    
    Access: Admin and depot managers
    """
    # TODO: Implement manifest editing
    flash("Manifest editing not yet implemented", "warning")
    return redirect(url_for("manifests.admin_manifests"))


@manifests_bp.route("/api/manifests")
@login_required
def api_list_manifests():
    """
    API: Get list of manifests as JSON
    
    Query Parameters:
        status (str): Filter by status (active, completed, cancelled)
        driver_id (str): Filter by driver ID
    """
    try:
        status_filter = request.args.get("status")
        driver_filter = request.args.get("driver_id")

        async def get_manifests():
            async with ParcelTrackingDB() as db:
                manifests = await db.get_all_active_manifests()
                
                # Apply filters
                if status_filter:
                    manifests = [m for m in manifests if m.get("status") == status_filter]
                if driver_filter:
                    manifests = [m for m in manifests if m.get("driver_id") == driver_filter]
                
                return manifests

        manifests = run_async(get_manifests())
        return jsonify({
            "success": True,
            "count": len(manifests),
            "manifests": manifests
        }), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@manifests_bp.route("/api/manifests/<manifest_id>/stream")
@login_required
def api_manifest_progress_stream(manifest_id: str):
    """
    SSE stream for real-time manifest progress updates
    
    Emits events for route optimization, delivery completions, etc.
    """
    def generate():
        # TODO: Implement SSE streaming for manifest updates
        yield f"data: {{\"type\": \"status\", \"message\": \"Streaming not yet implemented\"}}\n\n"
    
    return Response(stream_with_context(generate()), mimetype="text/event-stream")


# ============================================================================
# Helper Functions
# ============================================================================

async def _fallback_round_robin_assignment(db, parcels: List[Dict], drivers: List[Dict]) -> Dict[str, Any]:
    """
    Fallback assignment if AI agent fails - simple round-robin distribution
    
    Args:
        db: Database connection
        parcels: List of pending parcels
        drivers: List of available drivers
        
    Returns:
        Assignment result dictionary
    """
    # Distribute parcels evenly across drivers
    parcels_per_driver = len(parcels) // len(drivers)
    extra_parcels = len(parcels) % len(drivers)

    assignments = {}
    parcel_index = 0

    for i, driver in enumerate(drivers):
        count = parcels_per_driver + (1 if i < extra_parcels else 0)
        assignments[driver["driver_id"]] = parcels[parcel_index : parcel_index + count]
        parcel_index += count

    # Create manifests
    manifests_created = 0
    total_assigned = 0

    for driver_id, assigned_parcels in assignments.items():
        if assigned_parcels:
            driver = next(d for d in drivers if d["driver_id"] == driver_id)
            barcodes = [p["barcode"] for p in assigned_parcels]
            manifest_id = await db.create_driver_manifest(
                driver_id=driver_id,
                driver_name=driver["name"],
                parcel_barcodes=barcodes,
                driver_state=driver.get("location", "NSW"),
            )

            if manifest_id:
                manifests_created += 1
                total_assigned += len(barcodes)

    return {
        "success": True,
        "manifests_created": manifests_created,
        "parcels_assigned": total_assigned,
        "message": "Round-robin assignment completed",
    }


async def _generate_assignment_report(assignments: List[Dict[str, Any]]) -> str:
    """
    Generate CSV report of parcel assignments
    
    Args:
        assignments: List of assignment dictionaries
        
    Returns:
        Filename of generated report
    """
    # Create reports directory if it doesn't exist
    reports_dir = Path(__file__).parent.parent.parent.parent.parent / "static" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"assignment_report_{timestamp}.csv"
    filepath = reports_dir / filename

    # Write CSV report
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        fieldnames = [
            "driver_id",
            "driver_name",
            "manifest_id",
            "barcode",
            "tracking_number",
            "recipient",
            "address",
            "destination_city",
            "destination_state",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)

        writer.writeheader()
        for assignment in assignments:
            writer.writerow(assignment)

    return filename
