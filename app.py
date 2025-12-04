"""
DT Logistics Web Application
Flask web interface for the logistics operations center
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
import asyncio
import os
import re
import email
import base64
from datetime import datetime
from functools import wraps
from werkzeug.utils import secure_filename
from pathlib import Path

# Optional OCR support
try:
    import pytesseract
    from PIL import Image
    import io
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

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
from user_manager import UserManager, has_role, is_admin, is_driver, can_view_all_manifests, can_create_manifest, can_approve_requests

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

# File processing utilities for fraud detection

def allowed_file(filename):
    """Check if file extension is allowed"""
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'eml', 'msg', 'txt'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text_from_eml(file_content):
    """Extract text and metadata from .eml email file"""
    try:
        msg = email.message_from_bytes(file_content)
        
        # Extract sender
        sender = msg.get('From', 'unknown')
        subject = msg.get('Subject', '')
        
        # Extract body
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    try:
                        body += part.get_payload(decode=True).decode('utf-8', errors='ignore')
                    except:
                        body += str(part.get_payload())
        else:
            try:
                body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
            except:
                body = str(msg.get_payload())
        
        # Combine for analysis
        full_text = f"Subject: {subject}\\n\\n{body}"
        
        return full_text, sender
    except Exception as e:
        return f"[Error extracting email: {str(e)}]", "unknown"

def extract_text_from_msg(file_content):
    """Extract text from .msg Outlook file using extract_msg library"""
    try:
        import extract_msg
        import io
        
        # Create a file-like object from bytes
        msg_file = io.BytesIO(file_content)
        
        # Parse the MSG file
        msg = extract_msg.Message(msg_file)
        
        # Extract metadata
        sender = msg.sender or "unknown"
        subject = msg.subject or ""
        body = msg.body or ""
        
        # Clean up
        msg.close()
        
        # Combine for analysis
        full_text = f"Subject: {subject}\\n\\nFrom: {sender}\\n\\n{body}"
        
        return full_text, sender
    except Exception as e:
        print(f"⚠️ Error extracting MSG file with extract_msg: {str(e)}")
        # Fallback to basic extraction
        try:
            text = file_content.decode('utf-8', errors='ignore')
            sender_match = re.search(r'From:?\\s*([^\\n]+)', text)
            sender = sender_match.group(1).strip() if sender_match else "unknown"
            subject_match = re.search(r'Subject:?\\s*([^\\n]+)', text)
            subject = subject_match.group(1).strip() if subject_match else ""
            return f"Subject: {subject}\\n\\n{text[:2000]}", sender
        except Exception as e2:
            return f"[Error extracting Outlook message: {str(e)}. Try saving as .EML format]", "unknown"

def process_uploaded_file(file):
    """Process uploaded file and extract text content"""
    try:
        filename = secure_filename(file.filename)
        file_ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
        file_content = file.read()
        
        extracted_text = ""
        sender_info = "unknown"
        
        if file_ext == 'eml':
            extracted_text, sender_info = extract_text_from_eml(file_content)
            flash(f'✅ Email file analyzed. Sender: {sender_info}', 'info')
        
        elif file_ext == 'msg':
            extracted_text, sender_info = extract_text_from_msg(file_content)
            flash('ℹ️ Outlook .MSG file processed. For better results, save as .EML format.', 'info')
        
        elif file_ext == 'txt':
            extracted_text = file_content.decode('utf-8', errors='ignore')
            flash('📄 Text file loaded successfully', 'info')
        
        elif file_ext in ['png', 'jpg', 'jpeg', 'gif', 'bmp']:
            # Try OCR if available, otherwise use image description
            if OCR_AVAILABLE:
                try:
                    image = Image.open(io.BytesIO(file_content))
                    extracted_text = pytesseract.image_to_string(image)
                    if extracted_text.strip():
                        flash(f'📸 Screenshot analyzed using OCR - {len(extracted_text)} characters extracted', 'success')
                    else:
                        extracted_text = f"[Screenshot {filename} uploaded but no text detected. Image may be unclear or contain only graphics.]"
                        flash('📸 Screenshot uploaded but no readable text found. Please ensure image is clear.', 'warning')
                except Exception as ocr_error:
                    extracted_text = f"[Screenshot {filename} uploaded. OCR error: {str(ocr_error)}. Please ensure Tesseract is installed.]"
                    flash('⚠️ OCR processing failed. Analyzing image metadata instead.', 'warning')
            else:
                # Fallback: provide image metadata for AI to understand context
                extracted_text = f"[SCREENSHOT UPLOADED: {filename}]\n\n"
                extracted_text += "A screenshot image was uploaded containing a suspicious message. "
                extracted_text += "OCR is not currently installed. To enable automatic text extraction from screenshots:\n"
                extracted_text += "1. Install: pip install pytesseract Pillow\n"
                extracted_text += "2. Install Tesseract OCR: https://github.com/UB-Mannheim/tesseract/wiki\n\n"
                extracted_text += "For now, please also paste the text visible in the screenshot in the message field above."
                flash('📸 Screenshot uploaded. OCR not available - please also paste the visible text in the message field.', 'warning')
        
        return extracted_text, sender_info
        
    except Exception as e:
        flash(f'Error processing file: {str(e)}', 'danger')
        return "", "unknown"

# Authentication decorators

def login_required(f):
    """Require user to be logged in"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user'):
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(*roles):
    """Require user to have one of the specified roles"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = session.get('user')
            if not user:
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('login'))
            
            if user.get('role') not in roles:
                flash('You do not have permission to access this page.', 'danger')
                return redirect(url_for('dashboard'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Routes

@app.route('/')
def index():
    """Home page with dashboard"""
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page with role-based authentication"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Authenticate with UserManager
        async def auth_user():
            async with ParcelTrackingDB() as db:
                if not db.database:
                    await db.connect()
                
                user_mgr = UserManager(db)
                return await user_mgr.authenticate(username, password)
        
        try:
            user = run_async(auth_user())
            
            if user:
                session['user'] = user
                session['logged_in'] = True  # Backward compatibility
                session['username'] = user['username']  # Backward compatibility
                
                flash(f"Welcome back, {user['full_name']}!", 'success')
                
                # Redirect based on role
                if user['role'] == UserManager.ROLE_DRIVER:
                    return redirect(url_for('driver_manifest'))
                else:
                    return redirect(url_for('dashboard'))
            else:
                flash('Invalid credentials', 'danger')
        except Exception as e:
            flash(f'Login error: {str(e)}', 'danger')
    
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
    print(f"\n{'='*60}")
    print(f"📋 Fraud report route accessed - Method: {request.method}")
    print(f"{'='*60}")
    
    analysis = None
    
    if request.method == 'POST':
        print("📬 Processing POST request...")
        try:
            message_content = request.form.get('message_content', '').strip()
            sender_info = request.form.get('sender_info', 'unknown').strip()
            
            # Check if file was uploaded
            file_text = ""
            file_sender = ""
            if 'fraud_file' in request.files:
                file = request.files['fraud_file']
                if file and file.filename and allowed_file(file.filename):
                    print(f"📁 Processing uploaded file: {file.filename}")
                    file_text, file_sender = process_uploaded_file(file)
                    print(f"📄 Extracted {len(file_text)} characters from file")
                    
                    # Use file sender if not provided manually
                    if sender_info == 'unknown' and file_sender != 'unknown':
                        sender_info = file_sender
                        print(f"✉️ Sender extracted from file: {sender_info}")
            
            # Combine manual text and file text
            combined_message = ""
            if message_content and file_text:
                combined_message = f"{message_content}\\n\\n--- From uploaded file ---\\n{file_text}"
                print(f"📝 Combined manual text ({len(message_content)} chars) + file text ({len(file_text)} chars)")
            elif file_text:
                combined_message = file_text
                print(f"📂 Using file text only ({len(file_text)} chars)")
            elif message_content:
                combined_message = message_content
                print(f"✍️ Using manual text only ({len(message_content)} chars)")
            else:
                flash('Please provide either a message or upload a file to analyze.', 'warning')
                return render_template('report_fraud.html', analysis=None)
            
            print(f"🤖 Analyzing message with AI agent...")
            print(f"   Message preview: {combined_message[:200]}...")
            
            # Analyze with AI agent
            analysis = run_async(analyze_with_fraud_agent(combined_message, sender_info))
            
            print(f"✅ Analysis complete: {analysis.threat_level.value} threat, {len(analysis.risk_indicators)} indicators")
            
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
                        message_content=combined_message,  # Store the combined message
                        sender_info=sender_info,
                        risk_indicators=analysis.risk_indicators,
                        ai_analysis=ai_data
                    )
            
            report_id = run_async(store_report())
            # Don't flash message - analysis is displayed on page
            print(f"✅ Report stored with ID: {report_id}")
            
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

# Driver Manifest Routes

@app.route('/driver/manifest')
@login_required
def driver_manifest():
    """View driver's daily manifest"""
    try:
        user = session.get('user', {})
        
        # Determine driver_id based on user role
        if user.get('role') == UserManager.ROLE_DRIVER:
            # Driver sees their own manifest
            driver_id = user.get('driver_id')
            if not driver_id:
                flash('Driver ID not configured. Contact administrator.', 'danger')
                return render_template('driver_manifest.html', manifest=None)
        else:
            # Admin/depot manager can view any driver (use query param or default)
            driver_id = request.args.get('driver_id', 'driver-001')
        
        async def get_manifest():
            async with ParcelTrackingDB() as db:
                return await db.get_driver_manifest(driver_id)
        
        manifest = run_async(get_manifest())
        
        if not manifest:
            flash(f'No active manifest for driver {driver_id}. Contact dispatch for assignment.', 'info')
            return render_template('driver_manifest.html', manifest=None)
        
        # If route not optimized yet, optimize it now
        if not manifest.get('route_optimized') and manifest.get('items'):
            from bing_maps_routes import BingMapsRouter
            router = BingMapsRouter()
            
            # Extract addresses from manifest items
            addresses = [item['recipient_address'] for item in manifest['items']]
            
            # Get depot/starting location from env or use first address
            start_location = os.getenv('DEPOT_ADDRESS', 'Sydney, NSW 2000, Australia')
            
            # Optimize route
            route_info = router.optimize_route(addresses, start_location)
            
            if route_info:
                # Update manifest with optimized route
                async def update_route():
                    async with ParcelTrackingDB() as db:
                        await db.update_manifest_route(
                            manifest['id'],
                            route_info['waypoints'],
                            route_info['total_duration_minutes'],
                            route_info['total_distance_km'],
                            route_info.get('optimized', False),
                            route_info.get('traffic_considered', False)
                        )
                
                run_async(update_route())
                
                # Update local manifest object
                manifest['route_optimized'] = True
                manifest['optimized_route'] = route_info['waypoints']
                manifest['estimated_duration_minutes'] = route_info['total_duration_minutes']
                manifest['estimated_distance_km'] = route_info['total_distance_km']
                manifest['route_url'] = route_info['route_url']
                manifest['embed_url'] = router.generate_embed_url(route_info['waypoints'])
                manifest['optimized'] = route_info.get('optimized', False)
                manifest['traffic_considered'] = route_info.get('traffic_considered', False)
        
        # Always regenerate embed URL to ensure latest map features
        if manifest.get('route_optimized') and manifest.get('optimized_route'):
            from bing_maps_routes import BingMapsRouter
            router = BingMapsRouter()
            print(f"🗺️  [DRIVER] Generating embed URL for {len(manifest['optimized_route'])} addresses")
            print(f"🗺️  [DRIVER] First address: {manifest['optimized_route'][0] if manifest['optimized_route'] else 'None'}")
            manifest['embed_url'] = router.generate_embed_url(manifest['optimized_route'])
            print(f"🗺️  [DRIVER] Embed URL length: {len(manifest.get('embed_url', ''))} chars")
        
        return render_template('driver_manifest.html', manifest=manifest)
        
    except Exception as e:
        flash(f'Error loading manifest: {str(e)}', 'danger')
        return render_template('driver_manifest.html', manifest=None)

@app.route('/driver/manifest/<manifest_id>/complete/<barcode>', methods=['POST'])
@login_required
def mark_delivery_complete(manifest_id, barcode):
    """Mark a delivery as complete (drivers only)"""
    user = session.get('user', {})
    
    try:
        # Verify driver can only complete their own deliveries
        if user.get('role') == UserManager.ROLE_DRIVER:
            # Check manifest belongs to this driver
            async def verify_and_complete():
                async with ParcelTrackingDB() as db:
                    manifest = await db.get_manifest_by_id(manifest_id)
                    if not manifest or manifest.get('driver_id') != user.get('driver_id'):
                        return False, "You can only complete your own deliveries"
                    
                    # Find the item to get delivery address
                    delivery_address = None
                    for item in manifest.get('items', []):
                        if item.get('barcode') == barcode:
                            delivery_address = item.get('recipient_address', 'Unknown')
                            break
                    
                    success = await db.mark_delivery_complete(manifest_id, barcode)
                    if success and delivery_address:
                        await db.update_parcel_status(barcode, "delivered", delivery_address, user.get('username', 'driver'))
                    return success, None
            
            success, error_msg = run_async(verify_and_complete())
            if error_msg:
                flash(error_msg, 'danger')
                return redirect(url_for('driver_manifest'))
        else:
            # Admin can complete any delivery
            async def mark_complete():
                async with ParcelTrackingDB() as db:
                    manifest = await db.get_manifest_by_id(manifest_id)
                    if not manifest:
                        return False
                    
                    # Find the item to get delivery address
                    delivery_address = None
                    for item in manifest.get('items', []):
                        if item.get('barcode') == barcode:
                            delivery_address = item.get('recipient_address', 'Unknown')
                            break
                    
                    success = await db.mark_delivery_complete(manifest_id, barcode)
                    if success and delivery_address:
                        await db.update_parcel_status(barcode, "delivered", delivery_address, user.get('username', 'admin'))
                    return success
            
            success = run_async(mark_complete())
        
        if success:
            flash(f'Delivery {barcode} marked as complete!', 'success')
        else:
            flash(f'Error marking delivery complete', 'danger')
            
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
    
    return redirect(url_for('driver_manifest'))

@app.route('/admin/manifests')
@role_required(UserManager.ROLE_ADMIN, UserManager.ROLE_DEPOT_MANAGER)
def admin_manifests():
    """View all active manifests (admin and depot managers only)"""
    try:
        async def get_all_manifests():
            async with ParcelTrackingDB() as db:
                return await db.get_all_active_manifests()
        
        manifests = run_async(get_all_manifests())
        return render_template('admin_manifests.html', manifests=manifests)
        
    except Exception as e:
        flash(f'Error loading manifests: {str(e)}', 'danger')
        return render_template('admin_manifests.html', manifests=[])

@app.route('/admin/manifests/view/<manifest_id>')
@role_required(UserManager.ROLE_ADMIN, UserManager.ROLE_DEPOT_MANAGER)
def view_manifest_details(manifest_id):
    """View detailed manifest information (admin and depot managers only)"""
    try:
        async def get_manifest_by_id():
            async with ParcelTrackingDB() as db:
                # Ensure database is connected
                if not db.database:
                    await db.connect()
                
                # Get manifest from database
                container = db.database.get_container_client("driver_manifests")
                query = "SELECT * FROM c WHERE c.id = @manifest_id"
                parameters = [{"name": "@manifest_id", "value": manifest_id}]
                
                async for manifest in container.query_items(query=query, parameters=parameters):
                    return manifest
                return None
        
        manifest = run_async(get_manifest_by_id())
        
        if not manifest:
            flash('Manifest not found', 'danger')
            return redirect(url_for('admin_manifests'))
        
        # If route not optimized yet, optimize it now
        if not manifest.get('route_optimized') and manifest.get('items'):
            from bing_maps_routes import BingMapsRouter
            router = BingMapsRouter()
            
            # Extract addresses from manifest items
            addresses = [item['recipient_address'] for item in manifest['items']]
            
            # Get depot/starting location from env
            start_location = os.getenv('DEPOT_ADDRESS', 'Sydney, NSW 2000, Australia')
            
            # Optimize route
            route_info = router.optimize_route(addresses, start_location)
            
            if route_info:
                # Update manifest with optimized route
                async def update_route():
                    async with ParcelTrackingDB() as db:
                        await db.update_manifest_route(
                            manifest['id'],
                            route_info['waypoints'],
                            route_info['total_duration_minutes'],
                            route_info['total_distance_km'],
                            route_info.get('optimized', False),
                            route_info.get('traffic_considered', False)
                        )
                
                run_async(update_route())
                
                # Update local manifest object
                manifest['route_optimized'] = True
                manifest['optimized_route'] = route_info['waypoints']
                manifest['estimated_duration_minutes'] = route_info['total_duration_minutes']
                manifest['estimated_distance_km'] = route_info['total_distance_km']
                manifest['route_url'] = route_info['route_url']
                manifest['embed_url'] = router.generate_embed_url(route_info['waypoints'])
                manifest['optimized'] = route_info.get('optimized', False)
                manifest['traffic_considered'] = route_info.get('traffic_considered', False)
        
        # Always regenerate embed URL to ensure latest map features
        if manifest.get('route_optimized') and manifest.get('optimized_route'):
            from bing_maps_routes import BingMapsRouter
            router = BingMapsRouter()
            print(f"🗺️  [ADMIN] Generating embed URL for {len(manifest['optimized_route'])} addresses")
            print(f"🗺️  [ADMIN] First address: {manifest['optimized_route'][0] if manifest['optimized_route'] else 'None'}")
            manifest['embed_url'] = router.generate_embed_url(manifest['optimized_route'])
            print(f"🗺️  [ADMIN] Embed URL length: {len(manifest.get('embed_url', ''))} chars")
        
        # Reorder items according to optimized route if available
        if manifest.get('route_optimized') and manifest.get('optimized_route') and manifest.get('items'):
            optimized_route = manifest['optimized_route']
            original_items = manifest['items']
            
            # Create a mapping of addresses to items
            address_to_item = {item['recipient_address']: item for item in original_items}
            
            # Reorder items based on optimized route
            reordered_items = []
            for address in optimized_route:
                # Skip the depot/starting location (first in route)
                if address in address_to_item:
                    reordered_items.append(address_to_item[address])
            
            # Add any items that weren't in the optimized route (shouldn't happen, but safe)
            for item in original_items:
                if item not in reordered_items:
                    reordered_items.append(item)
            
            manifest['items'] = reordered_items
        
        return render_template('manifest_details.html', manifest=manifest)
        
    except Exception as e:
        flash(f'Error loading manifest details: {str(e)}', 'danger')
        return redirect(url_for('admin_manifests'))

@app.route('/admin/manifests/create', methods=['POST'])
@login_required
def create_manifest():
    """Create a new driver manifest"""
    try:
        driver_id = request.form.get('driver_id')
        driver_name = request.form.get('driver_name')
        barcode_list = request.form.get('barcodes', '').strip()
        
        # Parse barcodes (comma or newline separated)
        barcodes = [b.strip() for b in re.split(r'[,\n]', barcode_list) if b.strip()]
        
        if not barcodes:
            flash('No parcels selected for manifest', 'warning')
            return redirect(url_for('admin_manifests'))
        
        async def create():
            async with ParcelTrackingDB() as db:
                return await db.create_driver_manifest(driver_id, driver_name, barcodes)
        
        manifest_id = run_async(create())
        
        if manifest_id:
            flash(f'Manifest created successfully! ID: {manifest_id}', 'success')
        else:
            flash('Error creating manifest', 'danger')
            
        return redirect(url_for('admin_manifests'))
        
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('admin_manifests'))

# Public Parcel Tracking (Customer-Facing)

@app.route('/track', methods=['GET', 'POST'])
def track_parcel_public():
    """Public parcel tracking page for customers"""
    if request.method == 'GET':
        return render_template('track_parcel_public.html', tracking_results=None)
    
    tracking_input = request.form.get('tracking_number', '').strip()
    
    if not tracking_input:
        flash('Please enter at least one tracking number', 'warning')
        return render_template('track_parcel_public.html', tracking_results=None)
    
    # Parse multiple barcodes separated by comma or semicolon
    import re
    barcodes = [b.strip() for b in re.split(r'[,;]', tracking_input) if b.strip()]
    
    if not barcodes:
        flash('Please enter valid tracking numbers', 'warning')
        return render_template('track_parcel_public.html', tracking_results=None)
    
    try:
        async def get_tracking_info(tracking_number):
            async with ParcelTrackingDB() as db:
                # Get parcel details by barcode (what customers see on labels)
                parcel = await db.get_parcel_by_barcode(tracking_number)
                if not parcel:
                    return None
                
                # Barcode is the input tracking number
                barcode = tracking_number
                
                # Get tracking events using barcode
                events = await db.get_parcel_tracking_history(barcode)
                
                # Check if out for delivery - either status is out_for_delivery OR item is pending in an active manifest
                manifest = await db.get_manifest_for_parcel(barcode)
                is_out_for_delivery = parcel.get('current_status') == 'out_for_delivery'
                
                # If in active manifest with pending status, consider it out for delivery
                if manifest and manifest.get('status') == 'active':
                    # Find the item in manifest
                    for item in manifest.get('items', []):
                        if item.get('barcode') == barcode and item.get('status') != 'delivered':
                            is_out_for_delivery = True
                            break
                
                delivery_map_url = None
                deliveries_away = None
                
                print(f"🔍 Tracking Debug - Barcode: {barcode}, Status: {parcel.get('current_status')}, Manifest: {manifest is not None}, Out for delivery: {is_out_for_delivery}")
                
                if is_out_for_delivery and manifest:
                    print(f"🔍 Generating customer delivery map...")
                    deliveries_away, delivery_map_url = await generate_customer_delivery_map(
                        parcel, manifest
                    )
                    print(f"🔍 Map generated - Deliveries away: {deliveries_away}, Map URL exists: {delivery_map_url is not None}")
                
                # Determine display status - override if in active manifest
                display_status = parcel.get('current_status')
                if is_out_for_delivery and display_status not in ['delivered', 'out_for_delivery']:
                    display_status = 'out_for_delivery'
                
                # Set last_updated to current time if None
                last_updated = parcel.get('last_updated')
                if not last_updated:
                    from datetime import datetime, timezone
                    last_updated = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
                
                # Set expected delivery to today if in active manifest
                expected_delivery = parcel.get('expected_delivery_date')
                if is_out_for_delivery and manifest:
                    from datetime import datetime
                    expected_delivery = datetime.now().strftime('%Y-%m-%d')
                
                return {
                    'barcode': parcel.get('barcode'),
                    'current_status': display_status,  # Use computed status for display
                    'recipient_name': parcel.get('recipient_name'),
                    'expected_delivery': expected_delivery,
                    'last_updated': last_updated,
                    'events': events[::-1] if events else [],  # Reverse to show newest first
                    'delivery_map_url': delivery_map_url,
                    'deliveries_away': deliveries_away
                }
        
        # Get tracking info for all barcodes
        async def get_all_tracking():
            results = []
            not_found = []
            for barcode in barcodes:
                data = await get_tracking_info(barcode)
                if data:
                    results.append(data)
                else:
                    not_found.append(barcode)
            return results, not_found
        
        tracking_results, not_found = run_async(get_all_tracking())
        
        # Show warnings for not found barcodes
        if not_found:
            flash(f'Tracking number(s) not found: {", ".join(not_found)}', 'warning')
        
        if not tracking_results:
            flash('No tracking information found for the provided barcode(s)', 'danger')
            return render_template('track_parcel_public.html', tracking_results=None)
        
        return render_template('track_parcel_public.html', tracking_results=tracking_results)
        
    except Exception as e:
        flash(f'Error retrieving tracking information: {str(e)}', 'danger')
        return render_template('track_parcel_public.html', tracking_data=None)

async def generate_customer_delivery_map(parcel, manifest):
    """Generate approximate delivery map for customer (privacy-protected)"""
    try:
        from bing_maps_routes import BingMapsRouter
        import random
        
        print(f"🗺️ Starting map generation for barcode: {parcel.get('barcode')}")
        
        # Find parcel position in manifest
        items = manifest.get('items', [])
        print(f"🗺️ Manifest has {len(items)} items")
        
        completed_count = sum(1 for item in items if item.get('status') == 'delivered')
        parcel_index = next((i for i, item in enumerate(items) if item.get('barcode') == parcel.get('barcode')), None)
        
        print(f"🗺️ Parcel index in manifest: {parcel_index}, Completed: {completed_count}")
        
        if parcel_index is None:
            print(f"❌ Parcel not found in manifest items")
            return None, None
        
        # Calculate deliveries away
        deliveries_away = parcel_index - completed_count
        if deliveries_away < 0:
            deliveries_away = 0
        
        print(f"🗺️ Deliveries away: {deliveries_away}")
        
        # Get delivery address
        delivery_address = parcel.get('recipient_address')
        if not delivery_address:
            print(f"❌ No recipient address found")
            return deliveries_away, None
        
        print(f"🗺️ Delivery address: {delivery_address}")
        
        router = BingMapsRouter()
        
        # Geocode the actual delivery address
        coords = router.geocode_address(delivery_address)
        if not coords:
            print(f"❌ Geocoding failed for address: {delivery_address}")
            return deliveries_away, None
        
        lat, lon = coords
        print(f"🗺️ Geocoded coordinates: {lat}, {lon}")
        
        # Add random offset for privacy (5km radius)
        # 1 degree ≈ 111km, so 5km ≈ 0.045 degrees
        lat_offset = random.uniform(-0.045, 0.045)
        lon_offset = random.uniform(-0.045, 0.045)
        
        approximate_lat = lat + lat_offset
        approximate_lon = lon + lon_offset
        
        print(f"🗺️ Approximate coordinates (with privacy offset): {approximate_lat}, {approximate_lon}")
        
        # Generate map centered on approximate location with 5km radius circle
        map_url = router.generate_approximate_delivery_map(
            approximate_lat, approximate_lon, 
            actual_lat=lat, actual_lon=lon,
            radius_km=5
        )
        
        print(f"🗺️ Map URL generated: {len(map_url) if map_url else 0} characters")
        
        return f"{deliveries_away} stop{'s' if deliveries_away != 1 else ''}", map_url
        
    except Exception as e:
        print(f"❌ Error generating customer delivery map: {e}")
        import traceback
        traceback.print_exc()
        return None, None

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
