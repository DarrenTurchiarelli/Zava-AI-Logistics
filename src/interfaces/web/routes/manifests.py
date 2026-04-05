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
                            route_type="safest",
                            all_routes={"safest": safest_route},
                        )

                        # Refresh manifest
                        updated_manifest = await db.get_driver_manifest(driver_id)
                        return updated_manifest
                    
                    # Return original manifest if route creation failed
                    return manifest

            manifest = run_async(create_initial_route_sync())

        # ── Regenerate embed_url and route_options at render time ──────────
        if manifest and manifest.get("route_optimized") and manifest.get("optimized_route"):
            manifest["embed_url"] = url_for("manifests.render_map", manifest_id=manifest["id"])

            all_routes = manifest.get("all_routes") or {}
            manifest["multi_route_enabled"] = True
            manifest["route_options"] = {}

            for rtype in ["fastest", "shortest", "safest"]:
                if rtype in all_routes:
                    manifest["route_options"][rtype] = all_routes[rtype]
                else:
                    manifest["route_options"][rtype] = {
                        "calculated": False,
                        "total_duration_minutes": None,
                        "total_distance_km": None,
                    }

            if not manifest.get("selected_route_type"):
                manifest["selected_route_type"] = "safest"
                manifest["route_type_display"] = "Initial Nearest-Neighbor Route"
            else:
                manifest["route_type_display"] = manifest["selected_route_type"].capitalize() + " Route"

        # Enrich manifest items with address notes from previous deliveries
        if manifest and manifest.get("items"):
            async def load_address_notes():
                async with ParcelTrackingDB() as db:
                    for item in manifest["items"]:
                        addr = item.get("recipient_address", "")
                        if addr:
                            item["address_notes"] = await db.get_address_notes(addr)
            run_async(load_address_notes())

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


@manifests_bp.route("/driver/manifest/<manifest_id>/complete/<barcode>", methods=["POST"])
@login_required
def mark_delivery_complete(manifest_id: str, barcode: str):
    """
    Mark a delivery as complete or carded (drivers only).

    Access: Driver who owns the manifest, or admin/depot manager.
    """
    import base64

    user = session.get("user", {})

    try:
        driver_note = request.form.get("driver_note", "").strip()
        delivery_status = request.form.get("delivery_status", "delivered")
        post_office = request.form.get("post_office", "").strip()
        card_reason = request.form.get("card_reason", "No one home")

        # Handle optional photo upload
        delivery_photo_base64 = None
        if "delivery_photo" in request.files:
            photo_file = request.files["delivery_photo"]
            if photo_file and photo_file.filename != "":
                try:
                    photo_bytes = photo_file.read()
                    delivery_photo_base64 = base64.b64encode(photo_bytes).decode("utf-8")
                except Exception as photo_err:
                    flash(f"Warning: photo could not be saved ({photo_err})", "warning")

        if delivery_status == "carded" and not post_office:
            flash("Post office selection is required for carded deliveries", "danger")
            return redirect(url_for("manifests.driver_manifest"))

        async def _complete():
            async with ParcelTrackingDB() as db:
                manifest = await db.get_manifest_by_id(manifest_id)
                if not manifest:
                    return False, "Manifest not found"

                # Drivers may only complete their own deliveries
                if user.get("role") == UserManager.ROLE_DRIVER:
                    if manifest.get("driver_id") != user.get("driver_id"):
                        return False, "You can only complete your own deliveries"

                actor = user.get("username", "driver")

                delivery_address = next(
                    (item.get("recipient_address", "Unknown")
                     for item in manifest.get("items", [])
                     if item.get("barcode") == barcode),
                    "Unknown"
                )

                if delivery_status == "carded":
                    card_note = f"Card left - {card_reason}. Collect from: {post_office}"
                    if driver_note:
                        card_note += f". Driver note: {driver_note}"
                    success = await db.mark_delivery_complete(manifest_id, barcode, card_note)
                    if success:
                        await db.update_parcel_status(barcode, "carded", post_office, actor)
                        if delivery_photo_base64:
                            await db.store_delivery_photo(barcode, delivery_photo_base64, actor)
                else:
                    success = await db.mark_delivery_complete(
                        manifest_id, barcode, driver_note if driver_note else None
                    )
                    if success:
                        await db.update_parcel_status(barcode, "delivered", delivery_address, actor)
                        if delivery_photo_base64:
                            await db.store_delivery_photo(barcode, delivery_photo_base64, actor)

                return success, None

        success, error_msg = run_async(_complete())

        if error_msg:
            flash(error_msg, "danger")
        elif success:
            if delivery_status == "carded":
                flash(
                    f"Parcel {barcode} marked as carded – awaiting collection at "
                    f"{post_office.split(' - ')[0]}",
                    "success",
                )
            else:
                flash(f"Delivery {barcode} marked as complete!", "success")
        else:
            flash("Error marking delivery complete", "danger")

    except Exception as e:
        flash(f"Error: {str(e)}", "danger")

    return redirect(url_for("manifests.driver_manifest"))


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
        yield f"data: {{\"type\": \"status\", \"message\": \"Streaming not yet implemented\"}}\n\n"
    
    return Response(stream_with_context(generate()), mimetype="text/event-stream")


# ── Azure Maps routes ───────────────────────────────────────────────────────

@manifests_bp.route("/map/<manifest_id>")
@login_required
def render_map(manifest_id: str):
    """Render Azure Maps iframe HTML for a manifest's optimized route."""
    try:
        async def get_manifest_data():
            async with ParcelTrackingDB() as db:
                return await db.get_manifest_by_id(manifest_id)

        manifest = run_async(get_manifest_data())

        if not manifest or not manifest.get("optimized_route"):
            return "No route data available", 404

        from services.maps import BingMapsRouter
        router = BingMapsRouter()

        subscription_key = router.subscription_key
        if not subscription_key:
            return "Azure Maps not configured", 500

        addresses = manifest.get("optimized_route", [])
        if not addresses:
            return "No addresses to display", 404

        # ── Try to use pre-stored geometry (no live API calls needed) ────────
        all_routes_data = manifest.get("all_routes", {})
        selected_route_type = manifest.get("selected_route_type", "safest")
        route_data = all_routes_data.get(selected_route_type, {})

        route_coordinates = route_data.get("route_points", [])  # [lon, lat] pairs

        # Pre-stored pin coordinates (avoid geocoding at render time)
        pin_coords = route_data.get("waypoint_coords", [])  # [lon, lat] pairs

        # ── Fallback: geocode + live Directions API call ──────────────────────
        if not route_coordinates or not pin_coords:
            coordinates = []
            for addr in addresses:
                coords = router.geocode_address(addr)
                if coords:
                    coordinates.append(coords)

            if not coordinates:
                return "Failed to geocode addresses", 500

            if not pin_coords:
                pin_coords = [[lon, lat] for lat, lon in coordinates]

            if not route_coordinates and len(coordinates) <= 25:
                import requests as _req
                query_coords = ":".join([f"{lat},{lon}" for lat, lon in coordinates])
                try:
                    resp = _req.get(
                        "https://atlas.microsoft.com/route/directions/json",
                        params={
                            "api-version": "1.0",
                            "subscription-key": subscription_key,
                            "query": query_coords,
                            "traffic": "true",
                            "travelMode": "car",
                            "routeType": "fastest",
                        },
                        timeout=15,
                    )
                    resp.raise_for_status()
                    rdata = resp.json()
                    if rdata.get("routes"):
                        for leg in rdata["routes"][0].get("legs", []):
                            for pt in leg.get("points", []):
                                route_coordinates.append([pt["longitude"], pt["latitude"]])
                except Exception as e:
                    print(f"[render_map] Route API failed: {e} — using straight lines")

            if not route_coordinates:
                route_coordinates = [[lon, lat] for lat, lon in coordinates]

        center_lon, center_lat = pin_coords[0] if pin_coords else (151.2, -33.8)
        pins_js = ", ".join([f"[{c[0]}, {c[1]}]" for c in pin_coords])
        route_coords_js = ", ".join([f"[{c[0]}, {c[1]}]" for c in route_coordinates])

        return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <link rel="stylesheet" href="https://atlas.microsoft.com/sdk/javascript/mapcontrol/2/atlas.min.css" />
    <script src="https://atlas.microsoft.com/sdk/javascript/mapcontrol/2/atlas.min.js"></script>
    <style>body {{ margin: 0; padding: 0; }} #map {{ width: 100%; height: 100vh; }}</style>
</head>
<body>
    <div id="map"></div>
    <script>
        var centerLon = {center_lon};
        var centerLat = {center_lat};
        var pins = [{pins_js}];
        var routeCoords = [{route_coords_js}];

        var map = new atlas.Map('map', {{
            center: [centerLon, centerLat],
            zoom: 12,
            language: 'en-US',
            style: 'road',
            authOptions: {{ authType: 'subscriptionKey', subscriptionKey: '{subscription_key}' }}
        }});

        map.events.add('ready', function() {{
            var dataSource = new atlas.source.DataSource();
            map.sources.add(dataSource);

            if (routeCoords.length > 1) {{
                dataSource.add(new atlas.data.Feature(new atlas.data.LineString(routeCoords), {{ isRoute: true }}));
                map.layers.add(new atlas.layer.LineLayer(dataSource, null, {{
                    filter: ['==', ['get', 'isRoute'], true],
                    strokeColor: '#2196F3', strokeWidth: 5, lineJoin: 'round', lineCap: 'round'
                }}));
            }}

            pins.forEach(function(pin, index) {{
                dataSource.add(new atlas.data.Feature(new atlas.data.Point(pin), {{
                    title: 'Stop ' + (index + 1), isWaypoint: true
                }}));
            }});

            map.layers.add(new atlas.layer.SymbolLayer(dataSource, null, {{
                filter: ['==', ['get', 'isWaypoint'], true],
                iconOptions: {{ image: 'marker-blue', size: 0.8 }},
                textOptions: {{ textField: ['get', 'title'], offset: [0, -2.5], color: '#ffffff', size: 12 }}
            }}));
        }});
    </script>
</body>
</html>"""

    except Exception as e:
        import traceback
        return f"<pre>Error: {str(e)}\n\n{traceback.format_exc()}</pre>", 500


@manifests_bp.route("/driver/manifest/<manifest_id>/calculate-route/<route_type>", methods=["POST"])
@login_required
def calculate_additional_route(manifest_id: str, route_type: str):
    """Calculate a specific route type on-demand (fastest, shortest, safest)."""
    user = session.get("user", {})

    if route_type not in ["fastest", "shortest", "safest"]:
        return jsonify({"success": False, "error": "Invalid route type"}), 400

    try:
        async def get_and_calculate():
            async with ParcelTrackingDB() as db:
                manifest = await db.get_manifest_by_id(manifest_id)

                if user.get("role") == UserManager.ROLE_DRIVER:
                    if not manifest or manifest.get("driver_id") != user.get("driver_id"):
                        return {"success": False, "error": "Unauthorized"}

                all_routes = manifest.get("all_routes", {})
                if route_type in all_routes and all_routes[route_type].get("total_duration_minutes"):
                    return {"success": True, "message": "Route already calculated", "cached": True,
                            "route": all_routes[route_type]}

                from config.depots import get_depot_manager
                from services.maps import BingMapsRouter

                router = BingMapsRouter()
                depot_mgr = get_depot_manager()
                addresses = list(dict.fromkeys([item["recipient_address"] for item in manifest["items"]]))
                start_location = depot_mgr.get_closest_depot_to_address(addresses[0])

                new_route = router.optimize_route(addresses, start_location, route_type=route_type)
                if new_route:
                    new_route["split_into_runs"] = False
                    new_route["total_runs"] = 1

                if new_route:
                    all_routes[route_type] = new_route
                    manifest["all_routes"] = all_routes
                    manifest["selected_route_type"] = route_type
                    manifest["optimized_route"] = new_route["waypoints"]
                    manifest["estimated_duration_minutes"] = new_route["total_duration_minutes"]
                    manifest["estimated_distance_km"] = new_route["total_distance_km"]

                    container = db.database.get_container_client("driver_manifests")
                    await container.replace_item(item=manifest["id"], body=manifest)

                    return {"success": True, "message": f"{route_type.capitalize()} route calculated",
                            "route": new_route}
                return {"success": False, "error": "Failed to calculate route"}

        return jsonify(run_async(get_and_calculate()))

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@manifests_bp.route("/driver/manifest/<manifest_id>/recalculate-routes", methods=["POST"])
@login_required
def recalculate_routes(manifest_id: str):
    """Recalculate all three route types with current Azure Maps data."""
    user = session.get("user", {})

    try:
        async def do_recalculate(manifest):
            from config.depots import get_depot_manager
            from services.maps import BingMapsRouter

            addresses = list(dict.fromkeys([item["recipient_address"] for item in manifest.get("items", [])]))
            if not addresses:
                return False, "No addresses found in manifest"

            depot_mgr = get_depot_manager()
            start_location = depot_mgr.get_closest_depot_to_address(addresses[0])
            router = BingMapsRouter()
            all_routes = router.optimize_all_route_types(addresses, start_location)

            if not all_routes or len(all_routes) < 3:
                return False, "Failed to calculate routes with Azure Maps"

            current_route_type = manifest.get("selected_route_type", "safest")
            if current_route_type not in all_routes:
                current_route_type = "safest"
            selected = all_routes[current_route_type]

            async with ParcelTrackingDB() as db:
                await db.update_manifest_route(
                    manifest_id,
                    selected["waypoints"],
                    selected["total_duration_minutes"],
                    selected["total_distance_km"],
                    True,
                    selected.get("traffic_considered", False),
                    route_type=current_route_type,
                    all_routes=all_routes,
                )

            return True, {
                rt: f"{all_routes[rt]['total_duration_minutes']} min, {all_routes[rt]['total_distance_km']} km"
                for rt in ["fastest", "shortest", "safest"]
            }

        async def run():
            async with ParcelTrackingDB() as db:
                manifest = await db.get_manifest_by_id(manifest_id)
            if not manifest:
                return False, "Manifest not found"
            if user.get("role") == UserManager.ROLE_DRIVER and manifest.get("driver_id") != user.get("driver_id"):
                return False, "You can only modify your own manifest"
            return await do_recalculate(manifest)

        success, result = run_async(run())
        if success:
            return jsonify({"success": True, "routes": result})
        return jsonify({"success": False, "error": result}), (403 if "only modify" in str(result) else 500)

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@manifests_bp.route("/driver/manifest/<manifest_id>/switch-route", methods=["POST"])
@login_required
def switch_route(manifest_id: str):
    """Allow driver to switch between calculated route options."""
    user = session.get("user", {})

    try:
        route_type = request.json.get("route_type")
        if not route_type or route_type not in ["fastest", "shortest", "safest"]:
            return jsonify({"success": False, "error": "Invalid route type"}), 400

        async def run():
            async with ParcelTrackingDB() as db:
                manifest = await db.get_manifest_by_id(manifest_id)
                if user.get("role") == UserManager.ROLE_DRIVER:
                    if not manifest or manifest.get("driver_id") != user.get("driver_id"):
                        return False, "You can only modify your own manifest"

                success = await db.update_driver_route_preference(manifest_id, route_type)
                if not success:
                    return False, "Failed to switch route"
                updated = await db.get_manifest_by_id(manifest_id)
                return True, updated

        success, result = run_async(run())
        if success:
            manifest = result
            return jsonify({
                "success": True,
                "route_type": route_type,
                "duration": manifest.get("estimated_duration_minutes", 0),
                "distance": manifest.get("estimated_distance_km", 0),
                "map_url": url_for("manifests.render_map", manifest_id=manifest_id),
            })
        return jsonify({"success": False, "error": result}), (403 if "only modify" in str(result) else 500)

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


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
