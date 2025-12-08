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
    """Login page with role-based authentication and Azure AI Identity Agent verification"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Authenticate with UserManager
        async def auth_user():
            from azure_ai_agents import identity_agent
            
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
                        identity_result = await identity_agent(verification_request)
                        if identity_result.get('success'):
                            print(f"   [AI] Identity Agent verified courier")
                            user['ai_verified'] = True
                        else:
                            user['ai_verified'] = False
                    except Exception as ai_error:
                        print(f"   [WARN] AI Identity Agent unavailable: {ai_error}")
                        user['ai_verified'] = False
                
                return user
        
        try:
            user = run_async(auth_user())
            
            if user:
                session['user'] = user
                session['logged_in'] = True  # Backward compatibility
                session['username'] = user['username']  # Backward compatibility
                
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
            from azure_ai_agents import parcel_intake_agent
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
    """View all parcels with optional status filter"""
    try:
        # Get status filter from query parameter
        status_filter = request.args.get('status', None)
        
        async def get_all():
            async with ParcelTrackingDB() as db:
                all_parcels = await db.get_all_parcels()
                
                # Apply status filter if provided
                if status_filter:
                    all_parcels = [p for p in all_parcels if p.get('current_status') == status_filter]
                
                return all_parcels
        
        parcels = run_async(get_all())
        return render_template('all_parcels.html', parcels=parcels, status_filter=status_filter)
    except Exception as e:
        flash(f'Error loading parcels: {str(e)}', 'danger')
        return render_template('all_parcels.html', parcels=[], status_filter=None)

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
        async def get_approvals_with_parcels():
            async with ParcelTrackingDB() as db:
                pending = await db.get_all_pending_approvals()
                
                # Enrich approvals with parcel information
                for approval in pending:
                    parcel_id = approval.get('parcel_id')
                    if parcel_id:
                        parcel = await db.get_parcel_by_barcode(parcel_id)
                        if parcel:
                            approval['parcel_dc'] = parcel.get('origin_location', 'Unknown')
                            approval['parcel_status'] = parcel.get('current_status', 'unknown')
                            approval['parcel_location'] = parcel.get('current_location', 'Unknown')
                            approval['fraud_risk'] = parcel.get('fraud_risk_score', 0)
                
                return pending
        
        pending = run_async(get_approvals_with_parcels())
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
    """Customer Service AI Chatbot Interface"""
    # Check if user has customer service role
    user = session.get('user')
    if not user or user.get('role') not in [UserManager.ROLE_CUSTOMER_SERVICE, UserManager.ROLE_ADMIN]:
        flash('Access denied. Customer service role required.', 'danger')
        return redirect(url_for('dashboard'))
    
    return render_template('customer_service_chatbot.html')

@app.route('/api/chatbot/query', methods=['POST'])
@login_required
def chatbot_query():
    """Process chatbot query"""
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
                return await db.get_driver_manifest(driver_id)
        
        manifest = run_async(get_manifest())
        
        if not manifest:
            flash(f'No active manifest for driver {driver_id}. Contact dispatch for assignment.', 'info')
            return render_template('driver_manifest.html', manifest=None)
        
        # If route not optimized yet, optimize it now
        if not manifest.get('route_optimized') and manifest.get('items'):
            from bing_maps_routes import BingMapsRouter
            from depot_manager import get_depot_manager
            
            router = BingMapsRouter()
            depot_mgr = get_depot_manager()
            
            # Extract addresses from manifest items
            addresses = [item['recipient_address'] for item in manifest['items']]
            
            # Get optimal depot based on delivery addresses
            start_location = depot_mgr.get_depot_for_addresses(addresses)
            
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
            print(f"🗺️  [DRIVER] Map URL: {manifest['embed_url']}")
        
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
            from depot_manager import get_depot_manager
            
            router = BingMapsRouter()
            depot_mgr = get_depot_manager()
            
            # Extract addresses from manifest items
            addresses = [item['recipient_address'] for item in manifest['items']]
            
            # Get optimal depot based on delivery addresses
            start_location = depot_mgr.get_depot_for_addresses(addresses)
            
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
        
        # Extract all text
        full_text = ""
        text_lines = []
        
        if result.read and result.read.blocks:
            for block in result.read.blocks:
                for line in block.lines:
                    text_lines.append(line.text)
                    full_text += line.text + "\n"
        
        # Parse extracted data
        barcode = extract_barcode(text_lines)
        address = extract_address(text_lines)
        recipient_name = extract_recipient_name(text_lines)
        
        return jsonify({
            'success': True,
            'full_text': full_text.strip(),
            'text_lines': text_lines,
            'barcode': barcode,
            'address': address,
            'recipient_name': recipient_name
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

def extract_address(text_lines):
    """Extract address from text lines"""
    address_parts = []
    for i, line in enumerate(text_lines):
        # Look for lines with numbers (street numbers) and common address words
        if any(word in line.lower() for word in ['street', 'st', 'road', 'rd', 'avenue', 'ave', 'nsw', 'vic', 'qld']):
            # Include this line and potentially the next few lines
            address_parts.append(line)
            if i + 1 < len(text_lines):
                address_parts.append(text_lines[i + 1])
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

@app.route('/map/<manifest_id>')
def render_map(manifest_id):
    """Render Azure Maps for a manifest"""
    try:
        # Get manifest data
        async def get_manifest_data():
            async with ParcelTrackingDB() as db:
                return await db.get_manifest_by_id(manifest_id)
        
        manifest = run_async(get_manifest_data())
        
        if not manifest or not manifest.get('optimized_route'):
            return "No route data available", 404
        
        # Generate map HTML with route geometry
        from bing_maps_routes import BingMapsRouter
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
        
        # Fetch the actual route with geometry from Azure Maps API
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
        
        route_coordinates = []
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
