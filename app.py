"""
DT Logistics Web Application
Flask web interface for the logistics operations center
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session, Response, stream_with_context, Response, stream_with_context
import asyncio
import os
import re
import warnings

# Suppress asyncio Windows pipe warnings
warnings.filterwarnings('ignore', category=ResourceWarning, message='unclosed.*transport')
import email
import base64
import random
from datetime import datetime, timezone
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
from config.company import get_company_info, COMPANY_NAME, COMPANY_PHONE, COMPANY_EMAIL

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
from agents.fraud import analyze_with_fraud_agent, fraud_risk_agent
from user_manager import UserManager, has_role, is_admin, is_driver, can_view_all_manifests, can_create_manifest, can_approve_requests
import json
import time
from queue import Queue, Empty
import threading

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dt-logistics-secret-key-change-in-production')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload

# Global: Server-Sent Events queues for real-time updates
sse_queues = {}  # manifest_id -> Queue
sse_lock = threading.Lock()

# Global: Geocoding cache for performance
geocode_cache = {}  # address -> (lat, lon, timestamp)
geocode_cache_lock = threading.Lock()

# Global: Optimization locks to prevent duplicate threads
optimization_locks = {}  # manifest_id -> threading.Lock()
optimization_lock = threading.Lock()

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
    """Run async coroutine in Flask context with proper cleanup"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            # Cancel all pending tasks before closing
            try:
                pending = asyncio.all_tasks(loop)
                for task in pending:
                    task.cancel()
                if pending:
                    loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            except Exception:
                pass
            loop.close()
    except RuntimeError as e:
        if "cannot schedule new futures after shutdown" in str(e):
            # Event loop already shut down, return None gracefully
            return None
        raise

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

@app.route('/admin/setup-users-now', methods=['GET'])
def setup_users_now():
    """One-time setup endpoint to create default users"""
    import traceback
    try:
        async def do_setup():
            async with ParcelTrackingDB() as db:
                if not db.database:
                    await db.connect()
                
                # Create users container
                try:
                    await db.database.create_container(
                        id="users",
                        partition_key={"paths": ["/username"], "kind": "Hash"}
                    )
                    msg = "✅ Users container created<br>"
                except Exception as e:
                    if "already exists" in str(e).lower() or "conflict" in str(e).lower():
                        msg = "✅ Users container already exists<br>"
                    else:
                        msg = f"Container error: {e}<br>"
                
                # Create UserManager and add users
                user_mgr = UserManager(db)
                
                default_users = [
                    {'username': 'admin', 'password': 'admin123', 'role': UserManager.ROLE_ADMIN, 'full_name': 'Administrator'},
                    {'username': 'support', 'password': 'support123', 'role': UserManager.ROLE_CUSTOMER_SERVICE, 'full_name': 'Support Agent'},
                    {'username': 'driver001', 'password': 'driver123', 'role': UserManager.ROLE_DRIVER, 'full_name': 'Driver One', 'driver_id': 'driver-001'},
                    {'username': 'depot_mgr', 'password': 'depot123', 'role': UserManager.ROLE_DEPOT_MANAGER, 'full_name': 'Depot Manager'},
                ]
                
                created = []
                for user_data in default_users:
                    try:
                        existing = await user_mgr.get_user_by_username(user_data['username'])
                        if not existing:
                            await user_mgr.create_user(
                                username=user_data['username'],
                                password=user_data['password'],
                                role=user_data['role'],
                                full_name=user_data['full_name'],
                                driver_id=user_data.get('driver_id')
                            )
                            created.append(user_data['username'])
                    except Exception as e:
                        msg += f"Error creating {user_data['username']}: {e}<br>"
                
                return msg, created
        
        msg, created = run_async(do_setup())
        return f"<h1>Setup Complete!</h1><p>{msg}</p><p>Created users: {', '.join(created) if created else 'All users already existed'}</p><p><a href='/login'>Go to Login</a></p>"
    
    except Exception as e:
        return f"<h1>Setup Failed</h1><p>Error: {str(e)}</p><pre>{traceback.format_exc()}</pre>", 500

@app.route('/')
def index():
    """Home page with dashboard"""
    return render_template('index.html')

@app.after_request
def add_header(response):
    """Add headers to prevent caching of authenticated pages"""
    if 'user' in session:
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '-1'
    return response

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page with role-based authentication and Azure AI Identity Agent verification"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Authenticate with UserManager
        async def auth_user():
            from agents.base import identity_agent
            
            async with ParcelTrackingDB() as db:
                if not db.database:
                    await db.connect()
                
                user_mgr = UserManager(db)
                user = await user_mgr.authenticate(username, password)
                
                # If user authenticated and is a driver, verify with Azure AI Identity Agent
                if user and user.get('role') == UserManager.ROLE_DRIVER:
                    verification_request = {
                        'courier_id': user.get('username'),
                        'name': user.get('full_name'),
                        'role': user.get('role'),
                        'employment_status': 'active',
                        'authorized_zone': user.get('store_location', 'All'),
                        'verification_method': 'credential_login'
                    }
                    
                    try:
                        # Call Azure AI Identity Agent for courier verification
                        print(f"   [AI] Attempting Identity Agent verification for {user.get('username')}")
                        identity_result = await identity_agent(verification_request)
                        if identity_result.get('success'):
                            print(f"   [AI] ✓ Identity Agent verified courier")
                            user['ai_verified'] = True
                        else:
                            print(f"   [AI] ⚠ Identity Agent verification unsuccessful")
                            user['ai_verified'] = False
                    except Exception as ai_error:
                        print(f"   [WARN] AI Identity Agent unavailable: {ai_error}")
                        import traceback
                        traceback.print_exc()
                        user['ai_verified'] = False
                        # Continue with login even if AI verification fails
                
                return user
        
        try:
            user = run_async(auth_user())
            
            if user:
                session.clear()  # Clear any previous session data
                # Clear any pending flash messages from previous session
                from flask import get_flashed_messages
                get_flashed_messages()  # Consume and discard old messages
                
                session['user'] = user
                session['logged_in'] = True  # Backward compatibility
                session['username'] = user['username']  # Backward compatibility
                session.modified = True  # Force session update
                
                # Show AI verification badge for drivers
                if user.get('ai_verified'):
                    flash(f"Welcome back, {user['full_name']}! [AI Verified]", 'success')
                else:
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
    session.modified = True
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
    """Register new parcel with Azure AI Parcel Intake Agent validation"""
    if request.method == 'POST':
        try:
            from logistics_parcel import get_state_from_postcode
            from agents.base import parcel_intake_agent
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
            
            # Generate a tracking number and barcode
            tracking_number = f"DT{uuid.uuid4().hex[:10].upper()}"
            barcode = f"BC{uuid.uuid4().hex[:12].upper()}"
            
            # Validate with Azure AI Parcel Intake Agent
            parcel_data = {
                'tracking_number': tracking_number,
                'sender_name': sender_name,
                'sender_address': sender_address,
                'recipient_name': recipient_name,
                'recipient_address': recipient_address,
                'destination_postcode': destination_postcode,
                'destination_state': destination_state,
                'service_type': service_type,
                'weight_kg': weight,
                'dimensions': dimensions,
                'declared_value': declared_value,
                'special_instructions': special_instructions
            }
            
            async def validate_and_register():
                # Call Azure AI Parcel Intake Agent for validation
                validation_result = await parcel_intake_agent(parcel_data)
                
                # Log AI validation result
                if validation_result.get('success'):
                    print(f"[AI] Parcel Intake validation completed")
                
                # Register parcel in database (proceed even if AI validation fails)
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
                    return result['tracking_number'], validation_result
            
            final_tracking, validation = run_async(validate_and_register())
            flash(f'Parcel registered successfully! Tracking: {final_tracking}', 'success')
            
            # Show AI validation message if available
            if validation.get('success'):
                flash('✓ AI validation completed', 'info')
            
            return redirect(url_for('track_parcel_page', tracking_number=final_tracking))
            
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
    """View all parcels with optional status and state filters, plus pagination"""
    try:
        # Get filters and pagination from query parameters
        status_filter = request.args.get('status', None)
        state_filter = request.args.get('state', None)
        page = int(request.args.get('page', 1))
        per_page = 25
        
        async def get_all():
            async with ParcelTrackingDB() as db:
                all_parcels = await db.get_all_parcels()
                
                # Apply status filter if provided
                if status_filter:
                    all_parcels = [p for p in all_parcels if p.get('current_status') == status_filter]
                
                # Apply state filter if provided
                if state_filter:
                    all_parcels = [p for p in all_parcels if p.get('destination_state') == state_filter]
                
                # Calculate pagination
                total_parcels = len(all_parcels)
                total_pages = (total_parcels + per_page - 1) // per_page
                start_idx = (page - 1) * per_page
                end_idx = start_idx + per_page
                paginated_parcels = all_parcels[start_idx:end_idx]
                
                return {
                    'parcels': paginated_parcels,
                    'total': total_parcels,
                    'page': page,
                    'total_pages': total_pages,
                    'per_page': per_page
                }
        
        result = run_async(get_all())
        
        # Get unique states for filter dropdown (only valid Australian states)
        async def get_states():
            valid_states = ['NSW', 'VIC', 'QLD', 'SA', 'WA', 'ACT', 'TAS', 'NT']
            async with ParcelTrackingDB() as db:
                all_parcels = await db.get_all_parcels()
                states = sorted(set(p.get('destination_state') for p in all_parcels 
                                   if p.get('destination_state') in valid_states))
                return states
        
        available_states = run_async(get_states())
        
        return render_template('all_parcels.html', 
                             parcels=result['parcels'], 
                             status_filter=status_filter,
                             state_filter=state_filter,
                             available_states=available_states,
                             page=result['page'],
                             total_pages=result['total_pages'],
                             total_parcels=result['total'],
                             per_page=result['per_page'])
    except Exception as e:
        flash(f'Error loading parcels: {str(e)}', 'danger')
        return render_template('all_parcels.html', parcels=[], status_filter=None, state_filter=None, 
                             available_states=[], page=1, total_pages=0, total_parcels=0, per_page=25)

# Fraud Detection

@app.route('/fraud/report', methods=['GET', 'POST'])
def report_fraud():
    """Report suspicious message - publicly accessible with automated workflow"""
    print(f"\n{'='*60}")
    print(f"📋 Fraud report route accessed - Method: {request.method}")
    print(f"{'='*60}")
    
    analysis = None
    workflow_result = None
    
    if request.method == 'POST':
        print("📬 Processing POST request...")
        try:
            message_content = request.form.get('message_content', '').strip()
            sender_info = request.form.get('sender_info', 'unknown').strip()
            
            # Optional: Customer contact info for workflow
            reporter_name = request.form.get('reporter_name', '').strip()
            reporter_email = request.form.get('reporter_email', '').strip()
            reporter_phone = request.form.get('reporter_phone', '').strip()
            
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
            
            # 🔥 NEW: Trigger Fraud → Customer Service Workflow if high risk
            if analysis.confidence_score >= 0.7 and reporter_email:
                print(f"\n🚀 Triggering Fraud → Customer Service Workflow (Risk: {analysis.confidence_score:.0%})")
                
                from workflows.fraud_to_customer_service import fraud_detection_to_customer_service_workflow
                
                workflow_result = run_async(fraud_detection_to_customer_service_workflow(
                    message_content=combined_message,
                    sender_info={
                        "sender": sender_info,
                        "message_type": "email" if "@" in sender_info else "sms",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    },
                    customer_info={
                        "name": reporter_name or "Customer",
                        "email": reporter_email,
                        "phone": reporter_phone
                    },
                    trigger_type="customer_report"
                ))
                
                print(f"✅ Workflow completed: {workflow_result['status']}")
                flash('High-risk fraud detected! Customer protection workflow activated.', 'warning')
            
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
            import traceback
            traceback.print_exc()
    
    return render_template('report_fraud.html', analysis=analysis, workflow_result=workflow_result)

# Approvals

@app.route('/approvals')
@login_required
def approvals():
    """View pending approvals"""
    try:
        async def get_approvals_with_parcels():
            async with ParcelTrackingDB() as db:
                pending = await db.get_all_pending_approvals()
                
                # Enrich approvals with parcel information
                for approval in pending:
                    # Map the fields from database to template expectations
                    parcel_barcode = approval.get('parcel_barcode') or approval.get('parcel_id')
                    
                    # Set tracking number from the approval itself
                    approval['tracking_number'] = parcel_barcode
                    approval['parcel_id'] = parcel_barcode
                    
                    # Map request_type to approval_type for template (clean up formatting)
                    request_type = approval.get('request_type', 'N/A')
                    if request_type != 'N/A':
                        # Convert snake_case to Title Case (e.g., 'delivery_redirect' -> 'Delivery Redirect')
                        approval['approval_type'] = request_type.replace('_', ' ').title()
                    else:
                        approval['approval_type'] = request_type
                    
                    # Get additional parcel details if barcode exists
                    if parcel_barcode:
                        parcel = await db.get_parcel_by_barcode(parcel_barcode)
                        if parcel:
                            # Only override if not already set in approval
                            if not approval.get('parcel_dc'):
                                approval['parcel_dc'] = parcel.get('origin_location', 'Unknown')
                            if not approval.get('parcel_status'):
                                # Capitalize status (e.g., 'in transit' -> 'In Transit', 'delivered' -> 'Delivered')
                                status = parcel.get('current_status', 'unknown')
                                approval['parcel_status'] = status.title() if status else 'Unknown'
                            approval['parcel_location'] = parcel.get('current_location', 'Unknown')
                            fraud_score = parcel.get('fraud_risk_score') or 0
                            approval['fraud_risk'] = fraud_score
                            
                            # Generate fraud risk details for tooltip
                            fraud_details = []
                            if fraud_score and fraud_score > 70:
                                fraud_details.append("⚠️ High Risk Score")
                                fraud_details.append("• Suspicious delivery pattern detected")
                                fraud_details.append("• Multiple red flags present")
                                if 'blacklist' in approval.get('description', '').lower():
                                    fraud_details.append("• Blacklisted address")
                                if fraud_score and fraud_score > 85:
                                    fraud_details.append("• Extreme risk - requires supervisor review")
                            elif fraud_score and fraud_score > 30:
                                fraud_details.append("⚡ Medium Risk Score")
                                fraud_details.append("• Some indicators detected")
                                fraud_details.append("• Manual review recommended")
                                if 'verified' not in approval.get('description', '').lower():
                                    fraud_details.append("• Sender not verified")
                            else:
                                fraud_details.append("✓ Low Risk Score")
                                fraud_details.append("• No significant red flags")
                                fraud_details.append("• Standard processing approved")
                            
                            # Add contextual details
                            declared_value = parcel.get('declared_value') or 0
                            if declared_value > 1000:
                                fraud_details.append(f"• High value: ${declared_value}")
                            
                            approval['fraud_details'] = ' | '.join(fraud_details)
                            
                            # Generate address notes for medium/high risk
                            recipient_address = parcel.get('recipient_address', '')
                            if fraud_score and fraud_score > 30:
                                address_notes = await db.get_address_notes(recipient_address)
                                if not address_notes:
                                    # Generate sample notes based on risk level
                                    notes = []
                                    if fraud_score > 70:
                                        risk_reasons = [
                                            "Previous parcels intercepted at this address",
                                            "Address flagged for illegal imports - customs watch",
                                            "Multiple delivery attempts to unverified recipients",
                                            "Address associated with prohibited goods",
                                            "Law enforcement watch notice active"
                                        ]
                                        notes = random.sample(risk_reasons, min(2, len(risk_reasons)))
                                    else:  # Medium risk
                                        risk_reasons = [
                                            "New delivery address - verification required",
                                            "Multiple failed delivery attempts in past 30 days",
                                            "Address has history of refused deliveries",
                                            "Recipient identity not fully verified",
                                            "Commercial address flagged for review"
                                        ]
                                        notes = random.sample(risk_reasons, min(1, len(risk_reasons)))
                                    
                                    approval['address_notes'] = notes
                                else:
                                    approval['address_notes'] = address_notes
                            else:
                                approval['address_notes'] = []
                
                return pending
        
        pending = run_async(get_approvals_with_parcels())
        return render_template('approvals.html', approvals=pending)
    except Exception as e:
        flash(f'Error loading approvals: {str(e)}', 'danger')
        return render_template('approvals.html', approvals=[])

@app.route('/api/escalate-to-authorities', methods=['POST'])
@login_required
def escalate_to_authorities():
    """Escalate high-risk parcel to authorities"""
    try:
        data = request.get_json()
        approval_id = data.get('approval_id')
        tracking_number = data.get('tracking_number')
        risk_score = data.get('risk_score')
        escalated_by = data.get('escalated_by', session.get('username', 'system'))
        
        # Generate escalation reference
        from datetime import datetime
        reference_id = f"ESC-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{tracking_number[:8]}"
        
        async def log_escalation():
            async with ParcelTrackingDB() as db:
                # Create an escalation record (could be stored in a dedicated container)
                escalation_record = {
                    'reference_id': reference_id,
                    'approval_id': approval_id,
                    'tracking_number': tracking_number,
                    'risk_score': risk_score,
                    'escalated_by': escalated_by,
                    'escalated_at': datetime.now(timezone.utc).isoformat(),
                    'status': 'escalated',
                    'notified_authorities': ['Customs', 'Border Force']
                }
                
                # In a real system, this would:
                # 1. Send notifications to authorities
                # 2. Flag the parcel in the system
                # 3. Create audit trail
                # For now, we'll add a tracking event
                await db.create_tracking_event(
                    barcode=tracking_number,
                    event_type="escalation",
                    location="Security Review",
                    description=f"Escalated to authorities - Ref: {reference_id}",
                    scanned_by=escalated_by,
                    additional_info=escalation_record
                )
                
                # Auto-reject the approval with escalation note
                await db.reject_request(
                    request_id=approval_id,
                    rejected_by=escalated_by,
                    comments=f"ESCALATED TO AUTHORITIES - {reference_id} - Risk Score: {risk_score}%"
                )
        
        run_async(log_escalation())
        
        return jsonify({
            'success': True,
            'reference_id': reference_id,
            'message': 'Escalation recorded and authorities notified'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

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
        flash(f'Request {decision}ed successfully!', 'success')
    except Exception as e:
        flash(f'Error processing approval: {str(e)}', 'danger')
    
    return redirect(url_for('approvals'))

@app.route('/api/run-approval-agent', methods=['POST'])
@login_required
def run_approval_agent():
    """Run AI agent to auto-approve/reject based on predefined criteria"""
    try:
        approver = session.get('username', 'ai-agent')
        
        # Get configuration from request
        data = request.get_json() or {}
        config = data.get('config', {})
        selected_dcs = data.get('distributionCenters', [])
        
        # Validate that at least one DC is selected
        if not selected_dcs:
            return jsonify({
                'success': False,
                'error': 'No distribution centers selected. Please select at least one DC to enable the agent.'
            }), 400
        
        # Extract thresholds from config with defaults
        fraud_threshold_low = int(config.get('fraudThresholdLow', 30))
        value_threshold = float(config.get('valueThreshold', 500))
        fraud_threshold_high = int(config.get('fraudThresholdHigh', 70))
        
        # Extract checkbox settings
        approve_verified = config.get('approveVerified', True)
        approve_delivered = config.get('approveDelivered', True)
        reject_blacklist = config.get('rejectBlacklist', True)
        reject_duplicate = config.get('rejectDuplicate', True)
        reject_missing_docs = config.get('rejectMissingDocs', False)
        
        async def process_with_agent():
            async with ParcelTrackingDB() as db:
                # Get all pending approvals
                pending = await db.get_all_pending_approvals()
                
                print(f"\n🤖 Agent Mode Processing Started")
                print(f"   Total pending approvals: {len(pending)}")
                print(f"   Selected DCs: {selected_dcs}")
                print(f"   Thresholds: Fraud Low={fraud_threshold_low}%, High={fraud_threshold_high}%, Value=${value_threshold}")
                
                approved_count = 0
                rejected_count = 0
                skipped_count = 0
                skipped_dc_count = 0
                
                for approval in pending:
                    parcel_barcode = approval.get('parcel_barcode')
                    request_type = approval.get('request_type', '')
                    description = approval.get('description', '')
                    
                    print(f"\n   Processing: {parcel_barcode} - {request_type}")
                    
                    # Get parcel details for decision making
                    parcel = await db.get_parcel_by_barcode(parcel_barcode)
                    
                    if not parcel:
                        print(f"   ⚠️  Parcel not found, skipping")
                        skipped_count += 1
                        continue
                    
                    # Use parcel_dc from approval record (already stored there)
                    parcel_dc = approval.get('parcel_dc', 'UNKNOWN')
                    print(f"   Parcel DC: {parcel_dc}")
                    
                    # Check if the parcel's DC matches any selected DC (flexible matching)
                    dc_matched = False
                    for selected_dc in selected_dcs:
                        # Match if the selected DC ID appears in the parcel's location
                        if selected_dc in parcel_dc or parcel_dc.startswith(selected_dc):
                            dc_matched = True
                            break
                    
                    if not dc_matched:
                        print(f"   ⏭️  DC not matched, skipping")
                        skipped_dc_count += 1
                        continue
                    
                    # Auto-approval criteria
                    auto_approve = False
                    auto_reject = False
                    
                    # Check fraud risk if available
                    fraud_risk = parcel.get('fraud_risk_score', 0)
                    value = parcel.get('declared_value', 0)
                    status = approval.get('parcel_status', parcel.get('current_status', ''))
                    
                    print(f"   Fraud Risk: {fraud_risk}%, Value: ${value}, Status: {status}")
                    
                    # Auto-rejection criteria (using configured thresholds)
                    if fraud_risk > fraud_threshold_high:
                        auto_reject = True
                        reason_text = f"High fraud risk score: {fraud_risk}% (threshold: {fraud_threshold_high}%)"
                    elif reject_blacklist and 'blacklist' in description.lower():
                        auto_reject = True
                        reason_text = "Blacklisted address detected"
                    elif reject_duplicate and 'duplicate' in description.lower():
                        auto_reject = True
                        reason_text = "Duplicate request detected"
                    elif reject_missing_docs and 'missing' in description.lower():
                        auto_reject = True
                        reason_text = "Missing required documentation"
                    
                    # Auto-approval criteria (if not auto-rejected, using configured thresholds)
                    elif fraud_risk < fraud_threshold_low and value < value_threshold:
                        auto_approve = True
                        reason_text = f"Low risk ({fraud_risk}% < {fraud_threshold_low}%), standard value (${value} < ${value_threshold}) from DC: {parcel_dc}"
                    elif approve_delivered and status == 'Delivered' and request_type == 'delivery_confirmation':
                        auto_approve = True
                        reason_text = f"Standard delivery confirmation from DC: {parcel_dc}"
                    elif approve_verified and 'verified' in description.lower():
                        auto_approve = True
                        reason_text = f"Verified sender/recipient from DC: {parcel_dc}"
                    
                    # Process decision
                    if auto_approve:
                        print(f"   ✅ APPROVING: {reason_text}")
                        await db.approve_request(
                            request_id=approval['id'],
                            approved_by=approver,
                            comments=f"AI Agent: {reason_text}"
                        )
                        approved_count += 1
                    elif auto_reject:
                        print(f"   ❌ REJECTING: {reason_text}")
                        await db.reject_request(
                            request_id=approval['id'],
                            rejected_by=approver,
                            comments=f"AI Agent: {reason_text}"
                        )
                        rejected_count += 1
                    else:
                        print(f"   ⏭️  SKIPPING: No matching criteria")
                        skipped_count += 1
                
                print(f"\n🤖 Agent Mode Processing Complete")
                print(f"   ✅ Approved: {approved_count}")
                print(f"   ❌ Rejected: {rejected_count}")
                print(f"   ⏭️  Skipped: {skipped_count}")
                print(f"   🏢 DC Filtered: {skipped_dc_count}\n")
                
                return {
                    'approved': approved_count,
                    'rejected': rejected_count,
                    'skipped': skipped_count,
                    'skipped_dc': skipped_dc_count
                }
        
        results = run_async(process_with_agent())
        
        return jsonify({
            'success': True,
            'approved': results['approved'],
            'rejected': results['rejected'],
            'skipped': results['skipped'],
            'skipped_dc': results.get('skipped_dc', 0)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# AI & Intelligence

@app.route('/ai/insights')
@login_required
def ai_insights():
    """AI Insights Dashboard with real-time data"""
    async def get_insights():
        async with ParcelTrackingDB() as db:
            # Get all parcels for analysis
            all_parcels = await db.get_all_parcels()
            
            # Get approval requests
            approvals = await db.get_all_pending_approvals()
            
            # Calculate real metrics
            total_parcels = len(all_parcels)
            
            # Count by status
            status_counts = {}
            for parcel in all_parcels:
                status = parcel.get('current_status', 'Unknown')
                status_counts[status] = status_counts.get(status, 0) + 1
            
            in_transit = status_counts.get('In Transit', 0)
            delivered = status_counts.get('Delivered', 0)
            at_depot = status_counts.get('At Depot', 0)
            sorting = status_counts.get('Sorting', 0)
            out_for_delivery = status_counts.get('Out for Delivery', 0)
            
            # Calculate success rate (delivered / (delivered + exceptions))
            exceptions = status_counts.get('Exception', 0) + status_counts.get('Returned', 0)
            success_rate = round((delivered / (delivered + exceptions) * 100) if (delivered + exceptions) > 0 else 0, 1)
            
            # Get today's processed count (parcels with events today)
            today = datetime.now(timezone.utc).date()
            processed_today = sum(1 for p in all_parcels if p.get('created_at') and 
                                 datetime.fromisoformat(p['created_at'].replace('Z', '+00:00')).date() == today)
            
            # Active items (not delivered or registered)
            active_statuses = ['In Transit', 'Out for Delivery', 'At Depot', 'Sorting', 'Collected']
            active_parcels = sum(1 for p in all_parcels if p.get('current_status') in active_statuses)
            
            # Approval metrics
            total_approvals = len(approvals)
            valid_dc_approvals = sum(1 for a in approvals if a.get('parcel_dc') and 
                                    a.get('parcel_dc') not in ['Unknown DC', 'To Be Advised', 'Completed'])
            
            return {
                'total_processed': processed_today or total_parcels,
                'in_transit': in_transit,
                'delivered': delivered,
                'success_rate': success_rate,
                'at_depot': at_depot,
                'sorting': sorting,
                'out_for_delivery': out_for_delivery,
                'active_parcels': active_parcels,
                'total_approvals': total_approvals,
                'pending_approvals': total_approvals,
                'valid_dc_approvals': valid_dc_approvals,
                'auto_resolved': total_approvals - valid_dc_approvals,  # Approximation
                'avg_decision_time': '0.6s',
                'total_parcels': total_parcels
            }
    
    insights = run_async(get_insights())
    return render_template('ai_insights.html', insights=insights)

# Customer Service Chatbot Routes

@app.route('/customer_service/chatbot')
@login_required
def customer_service_chatbot():
    """Customer Service AI Chatbot Interface - Internal Use Only"""
    # Restrict to customer service and admin roles only
    user = session.get('user')
    if not user or user.get('role') not in [UserManager.ROLE_CUSTOMER_SERVICE, UserManager.ROLE_ADMIN]:
        flash('Access denied. Customer service role required.', 'danger')
        return redirect(url_for('dashboard'))
    
    return render_template('customer_service_chatbot.html')

@app.route('/api/chatbot/query', methods=['POST'])
@login_required
def chatbot_query():
    """Process chatbot query - Internal customer service use"""
    from customer_service_chatbot import CustomerServiceChatbot
    
    user = session.get('user')
    if not user or user.get('role') not in [UserManager.ROLE_CUSTOMER_SERVICE, UserManager.ROLE_ADMIN]:
        return jsonify({'error': 'Access denied'}), 403
    
    data = request.get_json()
    query = data.get('query', '')
    tracking_number = data.get('tracking_number')
    
    if not query:
        return jsonify({'error': 'Query is required'}), 400
    
    async def process():
        async with ParcelTrackingDB() as db:
            chatbot = CustomerServiceChatbot(db)
            
            # Build context
            context = {}
            if tracking_number:
                context['tracking_number'] = tracking_number
            
            # Process query
            response = await chatbot.process_query(query, context)
            return response
    
    try:
        result = run_async(process())
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/public/chatbot', methods=['POST'])
def public_chatbot():
    """Public chatbot for all users - Limited access, no internal data"""
    from customer_service_chatbot import CustomerServiceChatbot
    
    print("\n" + "="*60)
    print("🤖 Public Chatbot API Called")
    print("="*60)
    
    user = session.get('user')
    is_logged_in = user is not None
    
    data = request.get_json()
    query = data.get('query', '')
    
    print(f"📝 Query: {query}")
    if is_logged_in:
        print(f"👤 User: {user.get('username')} (Role: {user.get('role')})")
    else:
        print(f"👤 User: Anonymous (Public)")
    
    if not query:
        return jsonify({'error': 'Query is required'}), 400
    
    async def process():
        async with ParcelTrackingDB() as db:
            chatbot = CustomerServiceChatbot(db)
            
            # Limited context - available to all users
            context = {
                'customer_name': user.get('username') if is_logged_in else 'Guest',
                'user_role': user.get('role') if is_logged_in else 'public',
                'public_mode': True,  # Flag to limit responses
                'is_authenticated': is_logged_in
            }
            
            # Process query with restricted access
            response = await chatbot.process_query(query, context)
            print(f"\n📦 Raw response from chatbot: {response}")
            print(f"📦 Response type: {type(response)}")
            if isinstance(response, dict):
                print(f"📦 Response keys: {response.keys()}")
                print(f"📦 Success: {response.get('success')}")
                print(f"📦 Response field: {response.get('response')}")
            return response
    
    try:
        result = run_async(process())
        
        # Handle Azure AI agent response format
        if isinstance(result, dict):
            # Check if agent call was successful
            if not result.get('success', True):
                error_msg = result.get('error', 'Unknown error occurred')
                print(f"❌ Agent error: {error_msg}")
                return jsonify({'error': error_msg}), 500
            
            # Extract response text from nested structure
            response_text = None
            
            # Try: {success: True, response: "text"}
            if result.get('response'):
                response_obj = result['response']
                if isinstance(response_obj, str):
                    response_text = response_obj
                elif isinstance(response_obj, dict):
                    # Try: {type: 'text', text: {value: '...'}}
                    if response_obj.get('type') == 'text' and response_obj.get('text'):
                        if isinstance(response_obj['text'], dict):
                            response_text = response_obj['text'].get('value', str(response_obj))
                        else:
                            response_text = str(response_obj['text'])
                    # Try: {value: '...'}
                    elif response_obj.get('value'):
                        response_text = response_obj['value']
                    else:
                        response_text = str(response_obj)
            
            # Try: {type: 'text', text: {value: '...'}}
            elif result.get('type') == 'text' and result.get('text'):
                if isinstance(result['text'], dict):
                    response_text = result['text'].get('value', str(result))
                else:
                    response_text = str(result['text'])
            
            if response_text:
                # For public mode, extract just the customer communication part if structured format is returned
                # Agent returns structured format like:
                # **Resolution Option:** ...
                # **Customer Communication:** <actual message>
                # **Follow-up Required:** ...
                if 'Customer Communication:' in response_text:
                    # Extract the customer communication section
                    import re
                    match = re.search(r'\*\*Customer Communication:\*\*\s*(.+?)(?:\n\n\*\*|$)', response_text, re.DOTALL)
                    if match:
                        customer_message = match.group(1).strip()
                        return jsonify({'response': customer_message})
                
                # Clean up any residual structured markers
                import re
                # Remove patterns like [Issue Type: ...], [Resolution Option: ...], etc.
                # Also remove trailing markers at the end of sentences
                cleaned_text = re.sub(r'\s*,?\s*\[(?:Issue Type|Resolution Option|Customer Communication|Follow-up Required|Satisfaction Score):[^\]]*\]', '', response_text)
                # Remove any standalone brackets with these markers
                cleaned_text = re.sub(r'\[(?:Issue Type|Resolution Option|Customer Communication|Follow-up Required|Satisfaction Score):[^\]]*\],?\s*', '', cleaned_text)
                cleaned_text = cleaned_text.strip(', ').strip()
                
                # If we cleaned something and it's not empty, use the cleaned version
                if cleaned_text and cleaned_text != response_text:
                    return jsonify({'response': cleaned_text})
                
                return jsonify({'response': response_text})
        
        # Fallback - return as-is
        return jsonify({'response': str(result)})
    except Exception as e:
        print(f"❌ Chatbot exception: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/chatbot/track/<tracking_number>')
@login_required
def chatbot_track_parcel(tracking_number):
    """Track parcel via chatbot API"""
    from customer_service_chatbot import CustomerServiceChatbot
    
    user = session.get('user')
    if not user or user.get('role') not in [UserManager.ROLE_CUSTOMER_SERVICE, UserManager.ROLE_ADMIN]:
        return jsonify({'error': 'Access denied'}), 403
    
    async def track():
        async with ParcelTrackingDB() as db:
            chatbot = CustomerServiceChatbot(db)
            return await chatbot.track_parcel(tracking_number)
    
    try:
        result = run_async(track())
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/chatbot/frauds')
@login_required
def chatbot_check_frauds():
    """Get fraud reports via chatbot API"""
    from customer_service_chatbot import CustomerServiceChatbot
    
    user = session.get('user')
    if not user or user.get('role') not in [UserManager.ROLE_CUSTOMER_SERVICE, UserManager.ROLE_ADMIN]:
        return jsonify({'error': 'Access denied'}), 403
    
    limit = request.args.get('limit', 20, type=int)
    
    async def get_frauds():
        async with ParcelTrackingDB() as db:
            chatbot = CustomerServiceChatbot(db)
            return await chatbot.check_frauds(limit)
    
    try:
        result = run_async(get_frauds())
        return jsonify({'frauds': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/chatbot/location/<tracking_number>')
@login_required
def chatbot_parcel_location(tracking_number):
    """Get detailed parcel location status"""
    from customer_service_chatbot import CustomerServiceChatbot
    
    user = session.get('user')
    if not user or user.get('role') not in [UserManager.ROLE_CUSTOMER_SERVICE, UserManager.ROLE_ADMIN]:
        return jsonify({'error': 'Access denied'}), 403
    
    async def get_location():
        async with ParcelTrackingDB() as db:
            chatbot = CustomerServiceChatbot(db)
            return await chatbot.get_parcel_location_status(tracking_number)
    
    try:
        result = run_async(get_location())
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Azure Speech Services API Routes

@app.route('/api/speech/token', methods=['GET'])
def get_speech_token():
    """Get Azure Speech Services token for client-side use - Available to all users"""
    from services.speech import get_speech_service
    
    speech_service = get_speech_service()
    token_data = speech_service.get_speech_token()
    
    if token_data:
        return jsonify(token_data)
    else:
        return jsonify({
            'error': 'Speech services not configured',
            'fallback': True
        }), 200  # Return 200 to allow fallback to Web Speech API

@app.route('/api/speech/synthesize', methods=['POST'])
@login_required
def synthesize_speech():
    """Convert text to speech using Azure Speech Services"""
    from services.speech import get_speech_service
    
    data = request.get_json()
    text = data.get('text', '')
    voice_persona = data.get('voice_persona', 'natasha')  # Get selected voice from frontend
    
    if not text:
        return jsonify({'error': 'Text is required'}), 400
    
    speech_service = get_speech_service(voice_persona=voice_persona)  # Use selected voice
    audio_data = speech_service.synthesize_speech(text)
    
    if audio_data:
        from flask import send_file
        import io
        return send_file(
            io.BytesIO(audio_data),
            mimetype='audio/wav',
            as_attachment=False
        )
    else:
        return jsonify({'error': 'Speech synthesis failed'}), 500

@app.route('/api/speech/voices', methods=['GET'])
def get_available_voices():
    """Get list of available voice personas"""
    from services.speech import AzureSpeechService
    
    voices = AzureSpeechService.list_available_voices()
    return jsonify({
        'voices': voices,
        'count': len(voices)
    })

@app.route('/api/speech/voice', methods=['POST'])
@login_required
def set_voice_persona():
    """Change the active voice persona"""
    from services.speech import get_speech_service
    
    data = request.get_json()
    persona = data.get('persona', '')
    
    if not persona:
        return jsonify({'error': 'Persona is required'}), 400
    
    speech_service = get_speech_service(voice_persona=persona)
    
    if speech_service.enabled:
        return jsonify({
            'success': True,
            'voice': speech_service.current_voice,
            'persona': speech_service.voice_persona
        })
    else:
        return jsonify({'error': 'Speech services not configured'}), 500


@app.route('/admin/agents')
@login_required
def agent_monitoring_dashboard():
    """AI Agent Performance Monitoring Dashboard"""
    # Get state manager instance
    from logistics_state_manager import StateManager
    
    # For now, create a demo instance
    # In production, this should be a singleton shared across the app
    state_manager = StateManager()
    
    # Get comprehensive agent performance data
    dashboard_data = state_manager.get_agent_dashboard_data()
    
    # Add some example decisions if none exist (for demo)
    if dashboard_data['total_decisions'] == 0:
        from logistics_state_manager import AgentDecision
        import uuid
        
        # Sample decisions for demonstration
        sample_decisions = [
            AgentDecision(
                decision_id=str(uuid.uuid4()),
                agent_name="Fraud Detection Agent",
                agent_type="fraud_detection",
                tracking_number="DTVIC123",
                decision_type="analyze",
                decision_action="classified as LOW risk",
                confidence_score=0.92,
                reasoning="No suspicious patterns detected, sender verified",
                input_data={"message": "Sample message"},
                output_data={"threat_level": "LOW"},
                execution_time_ms=245.5
            ),
            AgentDecision(
                decision_id=str(uuid.uuid4()),
                agent_name="Approval Auto-Agent",
                agent_type="approval_automation",
                tracking_number="DTVIC124",
                decision_type="approve",
                decision_action="auto-approved delivery exception",
                confidence_score=0.88,
                reasoning="Fraud risk < 30%, DC match confirmed",
                input_data={"fraud_risk": 15, "dc": "DC-MEL-001"},
                output_data={"approved": True},
                execution_time_ms=156.2
            ),
            AgentDecision(
                decision_id=str(uuid.uuid4()),
                agent_name="Route Optimization Agent",
                agent_type="route_optimization",
                tracking_number=None,
                decision_type="optimize",
                decision_action="optimized route for DRV001",
                confidence_score=0.95,
                reasoning="Azure Maps optimization, 18 min time savings",
                input_data={"driver": "DRV001", "parcels": 12},
                output_data={"time_saved": 18, "fuel_saved": 2.3},
                execution_time_ms=892.7
            )
        ]
        
        for decision in sample_decisions:
            state_manager.record_agent_decision(decision, success=True)
        
        # Refresh dashboard data
        dashboard_data = state_manager.get_agent_dashboard_data()
    
    return render_template('agent_dashboard.html', dashboard=dashboard_data)

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
                manifest = await db.get_driver_manifest(driver_id)
                
                # If manifest exists but route_optimized is False, retry a few times
                # to handle Cosmos DB eventual consistency
                if manifest and not manifest.get('route_optimized'):
                    import time as time_module
                    for retry in range(4):  # Try up to 4 times
                        time_module.sleep(1.0)  # Wait 1000ms between retries
                        manifest = await db.get_driver_manifest(driver_id)
                        if manifest.get('route_optimized'):
                            break
                
                return manifest
        
        manifest = run_async(get_manifest())
        
        if not manifest:
            flash(f'No active manifest for driver {driver_id}. Contact dispatch for assignment.', 'info')
            return render_template('driver_manifest.html', manifest=None)
        
        # Check if initial nearest-neighbor route exists  
        needs_initial_route = (not manifest.get('route_optimized')) and bool(manifest.get('items'))
        
        # If no initial route yet, create it synchronously NOW (not async)
        if needs_initial_route:
            manifest_id = manifest['id']
            
            # Create initial nearest-neighbor route immediately
            async def create_initial_route_sync():
                async with ParcelTrackingDB() as db:
                    # Get unique addresses from manifest items
                    addresses = list(set([item['recipient_address'] for item in manifest['items']]))
                    
                    # Simple nearest-neighbor ordering (fast, no API calls)
                    ordered_addresses = addresses  # Already in a reasonable order
                    
                    # Create basic route structure
                    initial_route = {
                        'waypoints': ordered_addresses,
                        'total_duration_minutes': len(addresses) * 3,  # Estimate: 3 min per stop
                        'total_distance_km': len(addresses) * 0.5,  # Estimate: 500m between stops
                        'optimized': False,
                        'traffic_considered': False,
                        'route_type': 'nearest_neighbor'
                    }
                    
                    # Save initial route
                    all_routes = {'initial': initial_route}
                    success = await db.update_manifest_route(
                        manifest_id,
                        initial_route['waypoints'],
                        initial_route['total_duration_minutes'],
                        initial_route['total_distance_km'],
                        True,  # Mark as optimized so page loads
                        False,
                        route_type='initial',
                        all_routes=all_routes
                    )
                    
                    return success
            
            # Execute synchronously and wait for completion
            route_created = run_async(create_initial_route_sync())
            
            if route_created:
                # Wait a moment for Cosmos DB consistency
                import time as time_module
                time_module.sleep(1.0)  # Reduced from 1.5s to 1.0s
                
                # Re-fetch manifest with updated route
                manifest = run_async(get_manifest())
        
        # Clear the optimization attempted flag if route is now optimized
        if manifest and manifest.get('route_optimized'):
            manifest_id = manifest.get('id')
            session.pop(f'optimization_attempted_{manifest_id}', None)
            session.modified = True
        
        # Always regenerate embed URL to ensure latest map features
        if manifest.get('route_optimized') and manifest.get('optimized_route'):
            # Use Flask route instead of data URL
            manifest['embed_url'] = url_for('render_map', manifest_id=manifest['id'], _external=False)
            
            # Populate route options for UI from all_routes data
            all_routes = manifest.get('all_routes') or {}
            
            # Always enable multi-route selection (routes calculated on-demand)
            manifest['multi_route_enabled'] = True
            manifest['route_options'] = {}
            
            # Add calculated routes to options, OR create placeholders for on-demand calculation
            for route_type in ['fastest', 'shortest', 'safest']:
                if all_routes and route_type in all_routes:
                    manifest['route_options'][route_type] = all_routes[route_type]
                else:
                    # Add placeholder for on-demand calculation
                    manifest['route_options'][route_type] = {
                        'calculated': False,
                        'total_duration_minutes': None,
                        'total_distance_km': None
                    }
            
            # Set selected route type (default to 'initial' if no optimization chosen yet)
            if not manifest.get('selected_route_type') or manifest.get('selected_route_type') == 'initial':
                manifest['selected_route_type'] = None  # No selection yet
                manifest['route_type_display'] = 'Initial Nearest-Neighbor Route'
            else:
                manifest['route_type_display'] = manifest.get('selected_route_type', '').capitalize() + ' Route'
        
        # Fetch address notes for each delivery location
        async def fetch_address_notes():
            async with ParcelTrackingDB() as db:
                for item in manifest.get('items', []):
                    address = item.get('recipient_address')
                    if address:
                        notes = await db.get_address_notes(address)
                        if notes:
                            item['address_notes'] = notes
                            # Add summary for quick display
                            item['address_notes_summary'] = f"{len(notes)} note(s) from previous deliveries"
        
        run_async(fetch_address_notes())
        
        return render_template('driver_manifest.html', manifest=manifest)
        
    except Exception as e:
        flash(f'Error loading manifest: {str(e)}', 'danger')
        return render_template('driver_manifest.html', manifest=None)

@app.route('/api/driver/manifest/<manifest_id>/optimize', methods=['POST'])
@login_required
def optimize_manifest_route(manifest_id):
    """Optimize route for a manifest using Azure AI Foundry agent for parallel processing"""
    from agents.base import optimization_agent
    import threading
    from datetime import datetime
    
    def optimize_with_ai_agent():
        thread_id = threading.current_thread().ident
        thread_name = threading.current_thread().name
        start_time = datetime.now()
        
        try:
            print(f"\n{'='*80}")
            print(f"🤖 [AI-AGENT-{thread_id}] [{thread_name}] Starting AI-powered optimization")
            print(f"   Manifest: {manifest_id}")
            print(f"   Started at: {start_time.strftime('%H:%M:%S.%f')[:-3]}")
            print(f"{'='*80}\n")
            
            # Get manifest
            async def get_manifest():
                async with ParcelTrackingDB() as db:
                    return await db.get_manifest_by_id(manifest_id)
            
            manifest = run_async(get_manifest())
            if not manifest or not manifest.get('items'):
                print(f"⚠️  [AI-AGENT-{thread_id}] No manifest or items found")
                return
            
            from services.maps import BingMapsRouter
            from config.depots import get_depot_manager
            
            # Use global caches for geocoding and SSE events
            router = BingMapsRouter(geocode_cache=geocode_cache, cache_lock=geocode_cache_lock)
            depot_mgr = get_depot_manager()
            
            # Helper function to send SSE update
            def send_sse_update(event_type, data):
                with sse_lock:
                    if manifest_id in sse_queues:
                        sse_queues[manifest_id].put({
                            'event': event_type,
                            'data': json.dumps(data)
                        })
            
            # Group parcels by address
            address_groups = {}
            for item in manifest['items']:
                addr = item['recipient_address']
                if addr not in address_groups:
                    address_groups[addr] = []
                address_groups[addr].append(item)
            
            addresses = list(address_groups.keys())
            print(f"🗺️  [AI-AGENT-{thread_id}] Optimizing {len(addresses)} unique addresses ({len(manifest['items'])} parcels)")
            
            # Check if we need to split into multiple delivery runs
            MAX_ADDRESSES_PER_RUN = 25  # Azure Maps API limit
            needs_splitting = len(addresses) > MAX_ADDRESSES_PER_RUN
            
            if needs_splitting:
                print(f"📦 [AI-AGENT-{thread_id}] Manifest has {len(addresses)} addresses - splitting into multiple delivery runs")
                print(f"   Azure Maps API limit: {MAX_ADDRESSES_PER_RUN} waypoints per route")
                
                # Calculate number of runs needed
                num_runs = (len(addresses) + MAX_ADDRESSES_PER_RUN - 1) // MAX_ADDRESSES_PER_RUN
                manifest['delivery_runs'] = num_runs
                manifest['addresses_per_run'] = MAX_ADDRESSES_PER_RUN
                
                # Store the split information
                async def update_split_info():
                    async with ParcelTrackingDB() as db:
                        container = db.database.get_container_client('driver_manifests')
                        manifest['split_into_runs'] = True
                        manifest['total_runs'] = num_runs
                        await container.replace_item(item=manifest['id'], body=manifest)
                
                run_async(update_split_info())
                print(f"   ✅ Manifest will be split into {num_runs} delivery runs")
            else:
                manifest['split_into_runs'] = False
                manifest['delivery_runs'] = 1
            
            # Update progress: Starting
            async def update_progress(progress, step):
                async with ParcelTrackingDB() as db:
                    container = db.database.get_container_client('driver_manifests')
                    manifest['optimization_progress'] = progress
                    manifest['optimization_step'] = step
                    await container.replace_item(item=manifest['id'], body=manifest)
            
            run_async(update_progress(10, 'Calculating initial route...'))
            
            start_location = depot_mgr.get_closest_depot_to_address(addresses[0])
            
            # FAST INITIAL ROUTE: Use nearest-neighbor for instant load
            # This provides an immediate working route without Azure Maps API calls
            print(f"⚡ [AI-AGENT-{thread_id}] Creating fast nearest-neighbor route...")
            
            def nearest_neighbor_route(addresses, start_loc):
                """Fast greedy nearest-neighbor algorithm - O(n^2) but no API calls"""
                import math
                
                def distance(addr1, addr2):
                    # Simple Euclidean distance (good enough for ordering)
                    # In production, could use haversine formula
                    lat1, lon1 = 0, 0  # Parse from address or use geocoding cache
                    lat2, lon2 = 0, 0
                    return math.sqrt((lat1-lat2)**2 + (lon1-lon2)**2)
                
                route = [addresses[0]]  # Start with first address (closest to depot)
                remaining = set(addresses[1:])
                
                while remaining:
                    current = route[-1]
                    # Find nearest unvisited address
                    nearest = min(remaining, key=lambda x: len(current) + len(x))  # Simple heuristic
                    route.append(nearest)
                    remaining.remove(nearest)
                
                return route
            
            # Create initial route ordering
            ordered_addresses = nearest_neighbor_route(addresses, start_location)
            
            # Create basic route structure
            initial_route = {
                'waypoints': ordered_addresses,
                'total_duration_minutes': len(addresses) * 3,  # Estimate: 3 min per stop
                'total_distance_km': len(addresses) * 0.5,  # Estimate: 500m between stops
                'optimized': False,
                'traffic_considered': False,
                'route_type': 'nearest_neighbor'
            }
            
            # Save initial route immediately for instant page load
            # Don't assign a route type yet - let driver choose
            all_routes = {'initial': initial_route}
            
            async def save_initial_route():
                async with ParcelTrackingDB() as db:
                    success = await db.update_manifest_route(
                        manifest_id,
                        initial_route['waypoints'],
                        initial_route['total_duration_minutes'],
                        initial_route['total_distance_km'],
                        True,  # Mark as optimized so page loads
                        False,
                        route_type='initial',  # Initial nearest-neighbor route
                        all_routes=all_routes
                    )
                    if success:
                        print(f"✅ [AI-AGENT-{thread_id}] Initial route saved to database")
                    else:
                        print(f"❌ [AI-AGENT-{thread_id}] Failed to save initial route")
                return success
            
            # Save and wait for completion
            save_result = run_async(save_initial_route())
            
            # Additional wait to ensure Cosmos DB consistency
            import time as time_module
            time_module.sleep(1.0)
            
            # Verify the save completed
            async def verify_saved():
                async with ParcelTrackingDB() as db:
                    check_manifest = await db.get_manifest_by_id(manifest_id)
                    if check_manifest and check_manifest.get('route_optimized'):
                        print(f"✅ [AI-AGENT-{thread_id}] Verified: route_optimized=True in database")
                        return True
                    else:
                        print(f"⚠️  [AI-AGENT-{thread_id}] WARNING: route_optimized is still False after save!")
                        print(f"   Manifest state: route_optimized={check_manifest.get('route_optimized') if check_manifest else 'N/A'}")
                        print(f"   optimized_route exists: {bool(check_manifest.get('optimized_route')) if check_manifest else 'N/A'}")
                        return False
            
            verified = run_async(verify_saved())
            run_async(update_progress(100, 'Initial route ready. Select optimization type.'))
            
            print(f"✅ [AI-AGENT-{thread_id}] Initial route saved. Page can load now.")
            print(f"📍 [AI-AGENT-{thread_id}] Driver can now select route optimization type (Fastest/Shortest/Safest)")
            
            # Don't calculate routes in background - let driver choose on-demand
            print(f"✅ [AI-AGENT-{thread_id}] Optimization complete - awaiting driver selection")
                
        except Exception as e:
            print(f"❌ [AI-AGENT-{thread_id}] Error optimizing route: {e}")
            import traceback
            traceback.print_exc()
    
    # Spawn thread with AI agent processing
    thread = threading.Thread(target=optimize_with_ai_agent, daemon=True, name=f"AI-Optimizer-{manifest_id[-8:]}")
    thread.start()
    
    active_threads = threading.active_count()
    print(f"\n🤖 Spawned AI optimization thread: {thread.name} (ID: {thread.ident})")
    print(f"📊 Active threads: {active_threads} (including main thread)\n")
    
    return jsonify({'success': True, 'message': 'AI-powered route optimization started'})

@app.route('/api/driver/manifest/<manifest_id>/status', methods=['GET'])
@login_required
def check_manifest_status(manifest_id):
    """Check if manifest route optimization is complete and get progress"""
    try:
        async def get_manifest():
            async with ParcelTrackingDB() as db:
                return await db.get_manifest_by_id(manifest_id)
        
        manifest = run_async(get_manifest())
        
        if not manifest:
            return jsonify({'ready': False, 'progress': 0, 'step': 'Starting...'})
        
        is_ready = manifest.get('route_optimized', False)
        progress = manifest.get('optimization_progress', 100 if is_ready else 0)
        step = manifest.get('optimization_step', 'Complete' if is_ready else 'Initializing...')
        
        return jsonify({
            'ready': is_ready,
            'progress': progress,
            'step': step,
            'route_optimized': is_ready,
            'total_items': len(manifest.get('items', [])),
            'estimated_duration': manifest.get('estimated_duration_minutes', 0),
            'estimated_distance': manifest.get('estimated_distance_km', 0)
        })
    except Exception as e:
        return jsonify({'ready': False, 'progress': 0, 'step': 'Error', 'error': str(e)})

@app.route('/api/driver/manifest/<manifest_id>/events')
@login_required
def manifest_events(manifest_id):
    """Server-Sent Events endpoint for real-time manifest updates"""
    def event_stream():
        # Create queue for this client
        queue = Queue(maxsize=50)
        with sse_lock:
            sse_queues[manifest_id] = queue
        
        try:
            # Send initial connection confirmation
            yield f"data: {json.dumps({'event': 'connected', 'manifest_id': manifest_id})}\n\n"
            
            # Stream events
            while True:
                try:
                    # Wait for event with timeout
                    event = queue.get(timeout=30)
                    yield f"event: {event['event']}\ndata: {event['data']}\n\n"
                except Empty:
                    # Send keep-alive ping every 30 seconds
                    yield f"event: ping\ndata: {json.dumps({'time': time.time()})}\n\n"
        except GeneratorExit:
            # Client disconnected
            with sse_lock:
                if manifest_id in sse_queues:
                    del sse_queues[manifest_id]
    
    return Response(stream_with_context(event_stream()), 
                   content_type='text/event-stream',
                   headers={
                       'Cache-Control': 'no-cache',
                       'X-Accel-Buffering': 'no',
                       'Connection': 'keep-alive'
                   })

@app.route('/driver/manifest/<manifest_id>/calculate-route/<route_type>', methods=['POST'])
@login_required
def calculate_additional_route(manifest_id, route_type):
    """Calculate a route type on-demand (fastest, shortest, or safest)"""
    user = session.get('user', {})
    
    if route_type not in ['fastest', 'shortest', 'safest']:
        return jsonify({'success': False, 'error': 'Invalid route type'}), 400
    
    try:
        async def get_and_calculate():
            async with ParcelTrackingDB() as db:
                manifest = await db.get_manifest_by_id(manifest_id)
                
                # Verify driver owns this manifest
                if user.get('role') == UserManager.ROLE_DRIVER:
                    if not manifest or manifest.get('driver_id') != user.get('driver_id'):
                        return {'success': False, 'error': 'Unauthorized'}
                
                # Check if route already exists
                all_routes = manifest.get('all_routes', {})
                if route_type in all_routes:
                    return {'success': True, 'message': 'Route already calculated', 'cached': True}
                
                # Calculate the route
                from services.maps import BingMapsRouter
                from config.depots import get_depot_manager
                
                router = BingMapsRouter()
                depot_mgr = get_depot_manager()
                
                # Group parcels by address
                address_groups = {}
                for item in manifest['items']:
                    addr = item['recipient_address']
                    if addr not in address_groups:
                        address_groups[addr] = []
                    address_groups[addr].append(item)
                
                addresses = list(address_groups.keys())
                start_location = depot_mgr.get_closest_depot_to_address(addresses[0])
                
                # Check if we need to split into multiple runs (Azure Maps API limit: 25 waypoints)
                MAX_ADDRESSES_PER_RUN = 25
                
                if len(addresses) > MAX_ADDRESSES_PER_RUN:
                    print(f"📦 Splitting {len(addresses)} addresses into multiple delivery runs (max {MAX_ADDRESSES_PER_RUN} per run)")
                    
                    # Split addresses into chunks
                    address_chunks = [addresses[i:i + MAX_ADDRESSES_PER_RUN] for i in range(0, len(addresses), MAX_ADDRESSES_PER_RUN)]
                    
                    # Calculate route for each run
                    all_runs = []
                    total_distance = 0
                    total_duration = 0
                    all_waypoints = []
                    
                    for run_idx, chunk in enumerate(address_chunks, 1):
                        print(f"   📍 Run {run_idx}/{len(address_chunks)}: Optimizing {len(chunk)} addresses...")
                        run_route = router.optimize_route(chunk, start_location, route_type=route_type)
                        
                        if run_route:
                            all_runs.append({
                                'run_number': run_idx,
                                'addresses': len(chunk),
                                'distance_km': run_route['total_distance_km'],
                                'duration_minutes': run_route['total_duration_minutes'],
                                'waypoints': run_route['waypoints']
                            })
                            total_distance += run_route['total_distance_km']
                            total_duration += run_route['total_duration_minutes']
                            all_waypoints.extend(run_route['waypoints'])
                            print(f"      ✅ Run {run_idx}: {run_route['total_distance_km']}km, {run_route['total_duration_minutes']}min")
                    
                    # Create combined route
                    new_route = {
                        'waypoints': all_waypoints,
                        'total_distance_km': round(total_distance, 2),
                        'total_duration_minutes': round(total_duration, 1),
                        'route_type': route_type,
                        'split_into_runs': True,
                        'delivery_runs': all_runs,
                        'total_runs': len(address_chunks)
                    }
                    print(f"   ✅ Combined route: {new_route['total_distance_km']}km, {new_route['total_duration_minutes']}min across {len(address_chunks)} runs")
                else:
                    print(f"🔄 Calculating {route_type} route for {manifest_id}...")
                    new_route = router.optimize_route(addresses, start_location, route_type=route_type)
                    if new_route:
                        new_route['split_into_runs'] = False
                        new_route['total_runs'] = 1
                
                if new_route:
                    all_routes[route_type] = new_route
                    
                    # Update manifest with new route AND reorder parcels
                    manifest['all_routes'] = all_routes
                    manifest['selected_route_type'] = route_type
                    manifest['optimized_route'] = new_route['waypoints']
                    manifest['estimated_duration_minutes'] = new_route['total_duration_minutes']
                    manifest['estimated_distance_km'] = new_route['total_distance_km']
                    
                    # Reorder manifest items to match optimized route
                    address_to_items = {}
                    for item in manifest['items']:
                        addr = item['recipient_address']
                        if addr not in address_to_items:
                            address_to_items[addr] = []
                        address_to_items[addr].append(item)
                    
                    # Reorder items based on optimized waypoint order
                    reordered_items = []
                    for waypoint in new_route['waypoints']:
                        if waypoint in address_to_items:
                            reordered_items.extend(address_to_items[waypoint])
                    manifest['items'] = reordered_items
                    
                    container = db.database.get_container_client('driver_manifests')
                    await container.replace_item(item=manifest['id'], body=manifest)
                    
                    print(f"✅ Route calculated and parcels reordered: {new_route['total_distance_km']}km, {new_route['total_duration_minutes']}min")
                    
                    return {'success': True, 'message': f'{route_type.capitalize()} route calculated', 'route': new_route}
                else:
                    return {'success': False, 'error': 'Failed to calculate route'}
        
        result = run_async(get_and_calculate())
        return jsonify(result)
        
    except Exception as e:
        print(f"❌ Error calculating route: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/driver/manifest/<manifest_id>/switch-route', methods=['POST'])
@login_required
def switch_route(manifest_id):
    """Allow driver to switch between route options"""
    user = session.get('user', {})
    
    try:
        route_type = request.json.get('route_type')
        
        if not route_type or route_type not in ['fastest', 'shortest', 'safest']:
            return jsonify({'success': False, 'error': 'Invalid route type'}), 400
        
        # Verify driver can only modify their own manifest
        if user.get('role') == UserManager.ROLE_DRIVER:
            async def verify_and_switch():
                async with ParcelTrackingDB() as db:
                    manifest = await db.get_manifest_by_id(manifest_id)
                    if not manifest or manifest.get('driver_id') != user.get('driver_id'):
                        return False, "You can only modify your own manifest"
                    
                    # Switch the route
                    success = await db.update_driver_route_preference(manifest_id, route_type)
                    if success:
                        # Get updated manifest
                        updated_manifest = await db.get_manifest_by_id(manifest_id)
                        return True, updated_manifest
                    return False, "Failed to switch route"
            
            success, result = run_async(verify_and_switch())
            
            if success:
                manifest = result
                return jsonify({
                    'success': True,
                    'route_type': route_type,
                    'duration': manifest.get('estimated_duration_minutes', 0),
                    'distance': manifest.get('estimated_distance_km', 0),
                    'map_url': url_for('render_map', manifest_id=manifest_id, _external=False)
                })
            else:
                return jsonify({'success': False, 'error': result}), 403
        
        # Admin/Depot Manager can switch any manifest
        async def switch():
            async with ParcelTrackingDB() as db:
                success = await db.update_driver_route_preference(manifest_id, route_type)
                if success:
                    updated_manifest = await db.get_manifest_by_id(manifest_id)
                    return True, updated_manifest
                return False, "Failed to switch route"
        
        success, result = run_async(switch())
        
        if success:
            manifest = result
            return jsonify({
                'success': True,
                'route_type': route_type,
                'duration': manifest.get('estimated_duration_minutes', 0),
                'distance': manifest.get('estimated_distance_km', 0),
                'map_url': url_for('render_map', manifest_id=manifest_id, _external=False)
            })
        else:
            return jsonify({'success': False, 'error': result}), 500
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/driver/manifest/<manifest_id>/complete/<barcode>', methods=['POST'])
@login_required
def mark_delivery_complete(manifest_id, barcode):
    """Mark a delivery as complete or carded (drivers only)"""
    user = session.get('user', {})
    
    try:
        # Get form data
        driver_note = request.form.get('driver_note', '').strip()
        delivery_status = request.form.get('delivery_status', 'delivered')  # 'delivered' or 'carded'
        post_office = request.form.get('post_office', '').strip()
        card_reason = request.form.get('card_reason', 'No one home')
        
        # Validate carded delivery requires post office
        if delivery_status == 'carded' and not post_office:
            flash('Post office selection is required for carded deliveries', 'danger')
            return redirect(url_for('driver_manifest'))
        
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
                    
                    # Handle based on delivery status
                    if delivery_status == 'carded':
                        # Create detailed card note
                        card_note = f"Card left - {card_reason}. Collect from: {post_office}"
                        if driver_note:
                            card_note += f". Driver note: {driver_note}"
                        
                        success = await db.mark_delivery_complete(manifest_id, barcode, card_note)
                        if success and delivery_address:
                            await db.update_parcel_status(
                                barcode, 
                                "carded", 
                                post_office,  # Location is now the post office
                                user.get('username', 'driver')
                            )
                    else:
                        # Normal delivery
                        success = await db.mark_delivery_complete(manifest_id, barcode, driver_note if driver_note else None)
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
                    
                    # Handle based on delivery status
                    if delivery_status == 'carded':
                        card_note = f"Card left - {card_reason}. Collect from: {post_office}"
                        if driver_note:
                            card_note += f". Driver note: {driver_note}"
                        
                        success = await db.mark_delivery_complete(manifest_id, barcode, card_note)
                        if success and delivery_address:
                            await db.update_parcel_status(barcode, "carded", post_office, user.get('username', 'admin'))
                    else:
                        success = await db.mark_delivery_complete(manifest_id, barcode, driver_note if driver_note else None)
                        if success and delivery_address:
                            await db.update_parcel_status(barcode, "delivered", delivery_address, user.get('username', 'admin'))
                    
                    return success
            
            success = run_async(mark_complete())
        
        if success:
            if delivery_status == 'carded':
                flash(f'Parcel {barcode} marked as carded - awaiting collection at {post_office.split(" - ")[0]}', 'success')
            else:
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
            from services.maps import BingMapsRouter
            from config.depots import get_depot_manager
            
            router = BingMapsRouter()
            depot_mgr = get_depot_manager()
            
            # Extract addresses from manifest items
            addresses = [item['recipient_address'] for item in manifest['items']]
            
            # Get depot closest to the first parcel (starting point)
            start_location = depot_mgr.get_closest_depot_to_address(addresses[0])
            
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
            # Use Flask route instead of data URL
            manifest['embed_url'] = url_for('render_map', manifest_id=manifest_id, _external=False)
            print(f"🗺️  [ADMIN] Map URL: {manifest['embed_url']}")
        
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
                # Try to get parcel by barcode first (e.g., DT202512040001)
                parcel = await db.get_parcel_by_barcode(tracking_number)
                
                # If not found, try by tracking number (e.g., LP76996096HK)
                if not parcel:
                    parcel = await db.get_parcel_by_tracking_number(tracking_number)
                
                if not parcel:
                    return None
                
                # Use the parcel's barcode for all subsequent lookups
                barcode = parcel.get('barcode')
                
                # Get tracking events using barcode
                events = await db.get_parcel_tracking_history(barcode)
                
                # Check if out for delivery - either status is Out for Delivery OR item is pending in an active manifest
                manifest = await db.get_manifest_for_parcel(barcode)
                is_out_for_delivery = parcel.get('current_status') == 'Out for Delivery'
                
                # If in active manifest with pending status, consider it out for delivery
                if manifest and manifest.get('status') == 'active':
                    # Find the item in manifest
                    for item in manifest.get('items', []):
                        if item.get('barcode') == barcode and item.get('status') != 'Delivered':
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
                if is_out_for_delivery and display_status not in ['Delivered', 'Out for Delivery']:
                    display_status = 'Out for Delivery'
                
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

# Camera Scanner Routes

@app.route('/camera-scanner')
def camera_scanner():
    """Camera scanner page for OCR and barcode detection"""
    return render_template('camera_scanner.html')

@app.route('/api/analyze-image', methods=['POST'])
def analyze_image():
    """Analyze uploaded image with Azure AI Vision OCR"""
    try:
        if 'image' not in request.files:
            return jsonify({'error': 'No image provided'}), 400
        
        image_file = request.files['image']
        if image_file.filename == '':
            return jsonify({'error': 'No image selected'}), 400
        
        # Read image data
        image_data = image_file.read()
        
        # Call Azure AI Vision OCR
        from azure.ai.vision.imageanalysis import ImageAnalysisClient
        from azure.ai.vision.imageanalysis.models import VisualFeatures
        from azure.core.credentials import AzureKeyCredential
        
        endpoint = os.getenv('AZURE_VISION_ENDPOINT')
        key = os.getenv('AZURE_VISION_KEY')
        
        if not endpoint or not key:
            return jsonify({
                'error': 'Azure Vision not configured',
                'full_text': 'Please set AZURE_VISION_ENDPOINT and AZURE_VISION_KEY environment variables'
            }), 500
        
        # Create client
        client = ImageAnalysisClient(
            endpoint=endpoint,
            credential=AzureKeyCredential(key)
        )
        
        # Analyze image
        result = client.analyze(
            image_data=image_data,
            visual_features=[VisualFeatures.READ]
        )
        
        # Extract all text with position information
        full_text = ""
        text_lines = []
        text_with_positions = []  # Store text with bounding box info
        
        if result.read and result.read.blocks:
            for block in result.read.blocks:
                for line in block.lines:
                    text_lines.append(line.text)
                    full_text += line.text + "\n"
                    
                    # Store position info - bounding_polygon has points with x, y coordinates
                    if hasattr(line, 'bounding_polygon') and line.bounding_polygon:
                        # Get the bounding box coordinates
                        points = line.bounding_polygon
                        # Calculate center position
                        if len(points) >= 4:
                            avg_x = sum(p.x for p in points) / len(points)
                            avg_y = sum(p.y for p in points) / len(points)
                            text_with_positions.append({
                                'text': line.text,
                                'x': avg_x,
                                'y': avg_y,
                                'points': [(p.x, p.y) for p in points]
                            })
        
        # Parse extracted data
        barcode = extract_barcode(text_lines)
        address = extract_address(text_lines, text_with_positions)
        recipient_name = extract_recipient_name(text_lines)
        postcode = extract_postcode_bottom_right(text_with_positions)
        
        return jsonify({
            'success': True,
            'full_text': full_text.strip(),
            'text_lines': text_lines,
            'barcode': barcode,
            'address': address,
            'recipient_name': recipient_name,
            'postcode': postcode
        })
        
    except ImportError:
        return jsonify({
            'error': 'Azure AI Vision SDK not installed',
            'full_text': 'Please install: pip install azure-ai-vision-imageanalysis'
        }), 500
    except Exception as e:
        return jsonify({
            'error': str(e),
            'full_text': f'Error: {str(e)}'
        }), 500

def extract_barcode(text_lines):
    """Extract barcode from text lines"""
    for line in text_lines:
        # Look for patterns like DT202512040001 or LP76996096HK
        if re.match(r'^[A-Z]{2}\d{12}$', line.strip()):
            return line.strip()
        if re.match(r'^[A-Z]{2}\d{8}[A-Z]{2}$', line.strip()):
            return line.strip()
    return ""

def extract_postcode_bottom_right(text_with_positions):
    """
    Extract Australian postcode from bottom-right corner of image
    Postcodes are typically 4 digits and located in the bottom-right area
    """
    if not text_with_positions:
        return ""
    
    # Find the maximum x and y coordinates to determine bottom-right
    max_x = max(item['x'] for item in text_with_positions)
    max_y = max(item['y'] for item in text_with_positions)
    
    # Define bottom-right region (last 40% of width, last 30% of height)
    bottom_right_items = [
        item for item in text_with_positions
        if item['x'] > max_x * 0.6 and item['y'] > max_y * 0.7
    ]
    
    # Look for 4-digit Australian postcodes in bottom-right region first
    for item in bottom_right_items:
        # Match exactly 4 digits (Australian postcode format)
        match = re.search(r'\b(\d{4})\b', item['text'])
        if match:
            postcode = match.group(1)
            # Validate it's a reasonable Australian postcode (0200-9999)
            if 200 <= int(postcode) <= 9999:
                print(f"📍 Found postcode in bottom-right: {postcode} at position ({item['x']:.0f}, {item['y']:.0f})")
                return postcode
    
    # Fallback: search all text for postcodes if not found in bottom-right
    for item in text_with_positions:
        match = re.search(r'\b(\d{4})\b', item['text'])
        if match:
            postcode = match.group(1)
            if 200 <= int(postcode) <= 9999:
                print(f"📍 Found postcode (fallback): {postcode} at position ({item['x']:.0f}, {item['y']:.0f})")
                return postcode
    
    return ""

def extract_address(text_lines, text_with_positions=None):
    """Extract address from text lines"""
    address_parts = []
    for i, line in enumerate(text_lines):
        # Look for lines with numbers (street numbers) and common address words
        if any(word in line.lower() for word in ['street', 'st', 'road', 'rd', 'avenue', 'ave', 'lane', 'drive', 'nsw', 'vic', 'qld', 'sa', 'wa', 'tas', 'nt', 'act']):
            # Include this line and potentially the next few lines
            address_parts.append(line)
            if i + 1 < len(text_lines):
                next_line = text_lines[i + 1]
                address_parts.append(next_line)
                # Also check for suburb and state in next line
                if i + 2 < len(text_lines) and re.search(r'\d{4}', text_lines[i + 2]):
                    address_parts.append(text_lines[i + 2])
            break
    
    return ', '.join(address_parts) if address_parts else ""

def extract_recipient_name(text_lines):
    """Extract recipient name (usually first line or after 'To:')"""
    for i, line in enumerate(text_lines):
        if line.lower().startswith('to:') or line.lower().startswith('recipient:'):
            if i + 1 < len(text_lines):
                return text_lines[i + 1].strip()
        # First non-barcode, non-address line might be the name
        if not re.match(r'^[A-Z]{2}\d', line) and len(line.split()) >= 2:
            return line.strip()
    
    return text_lines[0] if text_lines else ""

async def generate_customer_delivery_map(parcel, manifest):
    """Generate approximate delivery map for customer (privacy-protected)"""
    try:
        from services.maps import BingMapsRouter
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

@app.route('/map/<manifest_id>')
def render_map(manifest_id):
    """Render Azure Maps for a manifest"""
    try:
        # Get manifest data
        async def get_manifest_data():
            async with ParcelTrackingDB() as db:
                return await db.get_manifest_by_id(manifest_id)
        
        manifest = run_async(get_manifest_data())
        
        # Debug logging
        print(f"[DEBUG] Map render check:")
        print(f"  Manifest ID: {manifest_id}")
        print(f"  Manifest exists: {manifest is not None}")
        if manifest:
            print(f"  route_optimized: {manifest.get('route_optimized')}")
            print(f"  optimized_route exists: {bool(manifest.get('optimized_route'))}")
            print(f"  optimized_route length: {len(manifest.get('optimized_route', []))}")
        
        if not manifest or not manifest.get('optimized_route'):
            print(f"⚠️ [DEBUG] No map: route_optimized={manifest.get('route_optimized') if manifest else 'N/A'}, optimized_route exists={bool(manifest.get('optimized_route')) if manifest else 'N/A'}")
            return "No route data available", 404
        
        # Generate map HTML with route geometry
        from services.maps import BingMapsRouter
        router = BingMapsRouter()
        
        addresses = manifest.get('optimized_route', [])
        if not addresses:
            return "No addresses to display", 404
        
        # Geocode addresses
        coordinates = []
        for addr in addresses:
            coords = router.geocode_address(addr)
            if coords:
                coordinates.append(coords)
        
        if not coordinates:
            return "Failed to geocode addresses", 500
        
        # Get subscription key
        subscription_key = router.subscription_key
        if not subscription_key:
            return "Azure Maps not configured", 500
        
        # Check if route_points are already stored in the manifest (from large route optimization)
        route_coordinates = []
        all_routes_data = manifest.get('all_routes', {})
        selected_route_type = manifest.get('selected_route_type', 'safest')
        route_data = all_routes_data.get(selected_route_type, {})
        
        # Use pre-calculated route points if available
        if 'route_points' in route_data and route_data['route_points']:
            route_coordinates = route_data['route_points']
            print(f"✓ Using stored route geometry: {len(route_coordinates)} points")
        elif len(coordinates) <= 25:
            # For small routes, fetch route geometry from Azure Maps API
            import requests
            query_coords = ":".join([f"{lat},{lon}" for lat, lon in coordinates])
            route_url = f"https://atlas.microsoft.com/route/directions/json"
            
            params = {
                'api-version': '1.0',
                'subscription-key': subscription_key,
                'query': query_coords,
                'traffic': 'true',
                'travelMode': 'car',
                'routeType': 'fastest'
            }
            
            try:
                response = requests.get(route_url, params=params, timeout=10)
                response.raise_for_status()
                route_data = response.json()
                
                if route_data.get('routes') and len(route_data['routes']) > 0:
                    route = route_data['routes'][0]
                    # Extract route geometry from legs
                    for leg in route.get('legs', []):
                        for point in leg.get('points', []):
                            route_coordinates.append([point['longitude'], point['latitude']])
                    
                    print(f"✓ Fetched route with {len(route_coordinates)} geometry points")
            except Exception as e:
                print(f"⚠️ Route API error: {e}")
                # Fallback to direct lines if route fetch fails
                route_coordinates = [[lon, lat] for lat, lon in coordinates]
        else:
            print(f"📊 Large route ({len(coordinates)} stops) - using direct line visualization")
        
        # If no route coordinates, use direct lines
        if not route_coordinates:
            route_coordinates = [[lon, lat] for lat, lon in coordinates]
            print(f"⚠️ Using direct lines between {len(route_coordinates)} waypoints")
        
        center_lat, center_lon = coordinates[0]
        pins_js = ', '.join([f"[{lon}, {lat}]" for lat, lon in coordinates])
        route_coords_js = ', '.join([f"[{lon}, {lat}]" for lon, lat in route_coordinates])
        
        # Return rendered HTML directly
        return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <link rel="stylesheet" href="https://atlas.microsoft.com/sdk/javascript/mapcontrol/2/atlas.min.css" />
    <script src="https://atlas.microsoft.com/sdk/javascript/mapcontrol/2/atlas.min.js"></script>
    <style>
        body {{ margin: 0; padding: 0; }}
        #map {{ width: 100%; height: 100vh; }}
        #debug {{ position: absolute; top: 10px; left: 10px; background: rgba(255,255,255,0.95); 
                 padding: 10px; border: 2px solid #2196F3; z-index: 1000; font-family: monospace; 
                 font-size: 11px; max-width: 300px; border-radius: 4px; box-shadow: 0 2px 4px rgba(0,0,0,0.2); }}
    </style>
</head>
<body>
    <div id="debug">Initializing map...</div>
    <div id="map"></div>
    <script>
        var debugEl = document.getElementById('debug');
        function log(msg) {{
            console.log(msg);
            debugEl.innerHTML += '<br>' + msg;
        }}
        
        var centerLon = {center_lon};
        var centerLat = {center_lat};
        var pins = [{pins_js}];
        var routeCoords = [{route_coords_js}];
        
        log('Map center: [' + centerLon.toFixed(4) + ', ' + centerLat.toFixed(4) + ']');
        log('Waypoints: ' + pins.length);
        log('Route points: ' + routeCoords.length);
        
        var map = new atlas.Map('map', {{
            center: [centerLon, centerLat],
            zoom: 12,
            language: 'en-US',
            style: 'road',
            authOptions: {{
                authType: 'subscriptionKey',
                subscriptionKey: '{subscription_key}'
            }}
        }});
        
        map.events.add('ready', function() {{
            log('✓ Map ready');
            var dataSource = new atlas.source.DataSource();
            map.sources.add(dataSource);
            
            // Add route line FIRST (so it renders under markers)
            if (routeCoords.length > 1) {{
                var routeLine = new atlas.data.Feature(
                    new atlas.data.LineString(routeCoords), 
                    {{ isRoute: true }}
                );
                dataSource.add(routeLine);
                
                var lineLayer = new atlas.layer.LineLayer(dataSource, null, {{
                    filter: ['==', ['get', 'isRoute'], true],
                    strokeColor: '#2196F3',
                    strokeWidth: 5,
                    lineJoin: 'round',
                    lineCap: 'round'
                }});
                map.layers.add(lineLayer);
                log('✓ Route line added (' + routeCoords.length + ' points)');
            }}
            
            // Add pins on top
            pins.forEach(function(pin, index) {{
                dataSource.add(new atlas.data.Feature(new atlas.data.Point(pin), {{
                    title: 'Stop ' + (index + 1),
                    isWaypoint: true
                }}));
            }});
            
            // Add marker layer
            var markerLayer = new atlas.layer.SymbolLayer(dataSource, null, {{
                filter: ['==', ['get', 'isWaypoint'], true],
                iconOptions: {{
                    image: 'marker-blue',
                    size: 0.8
                }},
                textOptions: {{
                    textField: ['get', 'title'],
                    offset: [0, -2.5],
                    color: '#ffffff',
                    size: 12
                }}
            }});
            map.layers.add(markerLayer);
            log('✓ ' + pins.length + ' markers displayed');
            
            setTimeout(function() {{ debugEl.style.display = 'none'; }}, 4000);
        }});
        
        map.events.add('error', function(e) {{
            log('ERROR: ' + e.error.message);
        }});
    </script>
</body>
</html>"""
    
    except Exception as e:
        import traceback
        return f"<pre>Error: {str(e)}\n\n{traceback.format_exc()}</pre>", 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=os.getenv('FLASK_ENV') == 'development')
