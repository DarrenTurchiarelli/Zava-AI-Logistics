"""
DT Logistics Web Application
Flask web interface for the logistics operations center
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
import asyncio
import os
from datetime import datetime
from functools import wraps

# Import company configuration
from company_config import get_company_info, COMPANY_NAME, COMPANY_PHONE, COMPANY_EMAIL

# Import all logistics modules
from logistics_common import setup_warning_suppression
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
from parcel_tracking_db import ParcelTrackingDB
from fraud_risk_agent import analyze_with_fraud_agent, fraud_risk_agent

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dt-logistics-secret-key-change-in-production')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload

# Initialize warning suppression
setup_warning_suppression()

# Make company info available to all templates
@app.context_processor
def inject_company_info():
    """Inject company information into all templates"""
    return {
        'company': get_company_info()
    }

# Helper function to run async functions in Flask
def run_async(coro):
    """Run async coroutine in Flask context"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

# Authentication decorator (simple version - enhance for production)
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Routes

@app.route('/')
def index():
    """Home page with dashboard"""
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Simple login page"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Simple auth (replace with proper authentication in production)
        if username == 'admin' and password == 'admin123':
            session['logged_in'] = True
            session['username'] = username
            flash('Successfully logged in!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Logout"""
    session.clear()
    flash('Successfully logged out', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard"""
    try:
        # Get statistics from database
        async def get_stats():
            async with ParcelTrackingDB() as db:
                parcels = await db.get_all_parcels()
                approvals = await db.get_all_pending_approvals()
                return {
                    'total_parcels': len(parcels),
                    'pending_approvals': len(approvals),
                    'parcels': parcels[:10]  # Latest 10
                }
        
        stats = run_async(get_stats())
        return render_template('dashboard.html', stats=stats)
    except Exception as e:
        flash(f'Error loading dashboard: {str(e)}', 'danger')
        return render_template('dashboard.html', stats={'total_parcels': 0, 'pending_approvals': 0, 'parcels': []})

# Parcel Operations

@app.route('/parcels/register', methods=['GET', 'POST'])
@login_required
def register_parcel():
    """Register new parcel"""
    if request.method == 'POST':
        try:
            from logistics_parcel import get_state_from_postcode
            import uuid
            
            # Get form data
            sender_name = request.form.get('sender_name')
            sender_address = request.form.get('sender_address')
            sender_phone = request.form.get('sender_phone')
            recipient_name = request.form.get('recipient_name')
            recipient_address = request.form.get('recipient_address')
            recipient_phone = request.form.get('recipient_phone')
            destination_postcode = request.form.get('destination_postcode')
            service_type = request.form.get('service_type', 'standard')
            weight = float(request.form.get('weight', 0))
            dimensions = request.form.get('dimensions', '')
            declared_value = float(request.form.get('declared_value', 0))
            special_instructions = request.form.get('special_instructions', '')
            
            # Determine destination state from postcode
            destination_state = get_state_from_postcode(destination_postcode)
            
            # Generate a barcode
            barcode = f"BC{uuid.uuid4().hex[:12].upper()}"
            
            # Register parcel in database
            async def register():
                async with ParcelTrackingDB() as db:
                    result = await db.register_parcel(
                        barcode=barcode,
                        sender_name=sender_name,
                        sender_address=sender_address,
                        sender_phone=sender_phone,
                        recipient_name=recipient_name,
                        recipient_address=recipient_address,
                        recipient_phone=recipient_phone,
                        destination_postcode=destination_postcode,
                        destination_state=destination_state,
                        service_type=service_type.lower(),
                        weight=weight,
                        dimensions=dimensions,
                        declared_value=declared_value,
                        special_instructions=special_instructions,
                        store_location=session.get('store_location', 'WebPortal')
                    )
                    return result['tracking_number']
            
            tracking_number = run_async(register())
            flash(f'Parcel registered successfully! Tracking: {tracking_number}', 'success')
            return redirect(url_for('track_parcel_page', tracking_number=tracking_number))
            
        except Exception as e:
            flash(f'Error registering parcel: {str(e)}', 'danger')
    
    return render_template('register_parcel.html')

@app.route('/parcels/track')
@app.route('/parcels/track/<tracking_number>')
@login_required
def track_parcel_page(tracking_number=None):
    """Track parcel"""
    # Check for tracking number from query parameter or URL path
    if not tracking_number:
        tracking_number = request.args.get('tracking_number')
    
    parcel = None
    if tracking_number:
        try:
            async def get_parcel():
                async with ParcelTrackingDB() as db:
                    return await db.get_parcel_by_tracking_number(tracking_number)
            
            parcel = run_async(get_parcel())
            if not parcel:
                flash(f'Parcel not found: {tracking_number}', 'warning')
        except Exception as e:
            flash(f'Error tracking parcel: {str(e)}', 'danger')
    
    return render_template('track_parcel.html', parcel=parcel, tracking_number=tracking_number)

@app.route('/parcels/all')
@login_required
def all_parcels():
    """View all parcels"""
    try:
        async def get_all():
            async with ParcelTrackingDB() as db:
                return await db.get_all_parcels()
        
        parcels = run_async(get_all())
        return render_template('all_parcels.html', parcels=parcels)
    except Exception as e:
        flash(f'Error loading parcels: {str(e)}', 'danger')
        return render_template('all_parcels.html', parcels=[])

# Fraud Detection

@app.route('/fraud/report', methods=['GET', 'POST'])
@login_required
def report_fraud():
    """Report suspicious message"""
    analysis = None
    
    if request.method == 'POST':
        try:
            message_content = request.form.get('message_content')
            sender_info = request.form.get('sender_info')
            
            # Analyze with AI agent
            analysis = run_async(analyze_with_fraud_agent(message_content, sender_info))
            
            # Store in database
            async def store_report():
                async with ParcelTrackingDB() as db:
                    ai_data = {
                        "threat_level": analysis.threat_level.value,
                        "fraud_category": analysis.fraud_category.value,
                        "confidence_score": analysis.confidence_score,
                        "recommended_actions": analysis.recommended_actions,
                        "alert_security_team": analysis.alert_security_team,
                        "related_patterns": analysis.related_patterns
                    }
                    return await db.store_suspicious_message(
                        message_content=message_content,
                        sender_info=sender_info,
                        risk_indicators=analysis.risk_indicators,
                        ai_analysis=ai_data
                    )
            
            report_id = run_async(store_report())
            flash(f'Report submitted successfully! ID: {report_id}', 'success')
            
        except Exception as e:
            flash(f'Error analyzing message: {str(e)}', 'danger')
    
    return render_template('report_fraud.html', analysis=analysis)

# Approvals

@app.route('/approvals')
@login_required
def approvals():
    """View pending approvals"""
    try:
        async def get_approvals():
            async with ParcelTrackingDB() as db:
                return await db.get_all_pending_approvals()
        
        pending = run_async(get_approvals())
        return render_template('approvals.html', approvals=pending)
    except Exception as e:
        flash(f'Error loading approvals: {str(e)}', 'danger')
        return render_template('approvals.html', approvals=[])

@app.route('/approvals/<approval_id>/process', methods=['POST'])
@login_required
def process_approval(approval_id):
    """Process approval decision"""
    try:
        decision = request.form.get('decision')  # 'approve' or 'reject'
        notes = request.form.get('notes', '')
        approver = session.get('username', 'web-user')
        
        async def process():
            async with ParcelTrackingDB() as db:
                if decision == 'approve':
                    await db.approve_request(
                        request_id=approval_id,
                        approved_by=approver,
                        comments=notes
                    )
                else:
                    await db.reject_request(
                        request_id=approval_id,
                        rejected_by=approver,
                        comments=notes
                    )
        
        run_async(process())
        flash(f'Request {decision}d successfully!', 'success')
    except Exception as e:
        flash(f'Error processing approval: {str(e)}', 'danger')
    
    return redirect(url_for('approvals'))

# AI & Intelligence

@app.route('/ai/insights')
@login_required
def ai_insights():
    """AI Insights Dashboard"""
    # Generate insights data
    import random
    insights = {
        'total_processed': random.randint(450, 550),
        'in_transit': random.randint(80, 120),
        'delivered': random.randint(350, 450),
        'success_rate': random.randint(94, 98),
        'active_drivers': random.randint(15, 20),
        'avg_delivery_time': random.randint(22, 28),
        'on_time_rate': random.randint(92, 97),
        'nps_score': random.randint(68, 78)
    }
    return render_template('ai_insights.html', insights=insights)

# API Endpoints

@app.route('/api/parcels/search')
@login_required
def api_search_parcels():
    """API: Search parcels"""
    query = request.args.get('q', '')
    try:
        async def search():
            async with ParcelTrackingDB() as db:
                parcels = await db.get_all_parcels()
                # Simple search by tracking number or recipient
                return [p for p in parcels if query.lower() in str(p).lower()]
        
        results = run_async(search())
        return jsonify({'success': True, 'results': results[:20]})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/stats')
@login_required
def api_stats():
    """API: Get current statistics"""
    try:
        async def get_stats():
            async with ParcelTrackingDB() as db:
                parcels = await db.get_all_parcels()
                approvals = await db.get_pending_approvals()
                return {
                    'total_parcels': len(parcels),
                    'pending_approvals': len(approvals),
                    'timestamp': datetime.now().isoformat()
                }
        
        stats = run_async(get_stats())
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Error handlers

@app.errorhandler(404)
def not_found(error):
    return render_template('error.html', error='Page not found'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('error.html', error='Internal server error'), 500

# Health check for Azure
@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=os.getenv('FLASK_ENV') == 'development')
