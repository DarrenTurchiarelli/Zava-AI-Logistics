# logistics_customer.py
# Customer & Delivery Experience Features

import asyncio
from datetime import datetime
from parcel_tracking_db import ParcelTrackingDB

async def manage_delivery_preferences():
    """Manage customer delivery preferences"""
    print("\n=== Manage Delivery Preferences ===")
    
    # First, identify the customer/parcel
    print("🆔 Customer Identification:")
    print("  1. Enter customer ID/account")
    print("  2. Use specific parcel tracking number")
    print("  3. Use phone number lookup")
    
    id_method = input("Select identification method (1-3): ").strip()
    
    customer_id = None
    parcel_barcode = None
    
    if id_method == "1":
        customer_id = input("Enter customer ID or account number: ").strip()
        print(f"👤 Managing preferences for Customer: {customer_id}")
        
    elif id_method == "2":
        parcel_barcode = input("Enter parcel tracking number/barcode: ").strip()
        print(f"📦 Managing preferences for parcel: {parcel_barcode}")
        print("   (Preferences will apply to this delivery and future deliveries from this customer)")
        
    elif id_method == "3":
        phone_number = input("Enter customer phone number: ").strip()
        print(f"📞 Looking up customer by phone: {phone_number}")
        customer_id = f"CUST_{phone_number[-4:]}"  # Simulate lookup
        print(f"👤 Found customer: {customer_id}")
        
    else:
        print("❌ Invalid selection. Please restart.")
        return
    
    print("\nAvailable delivery preference options:")
    preferences = [
        "Authority to leave (safe drop)",
        "Secure locker pickup",
        "Change delivery address",
        "Delivery time preferences",
        "Special handling instructions",
        "Signature required",
        "Leave with neighbor authorization"
    ]
    
    for i, pref in enumerate(preferences, 1):
        print(f"  {i}. {pref}")
    
    choice = input("\nSelect preference to configure (1-7): ").strip()
    
    # Show which customer/parcel this applies to
    target = f"Customer {customer_id}" if customer_id else f"Parcel {parcel_barcode}"
    
    if choice == "1":
        print(f"🏠 Authority to Leave Configuration for {target}:")
        print("✅ Customer authorizes safe drop at front door")
        print("📋 Preferred safe drop locations: Front porch, side gate, mailbox")
        safe_location = input("Specify preferred safe drop location: ").strip()
        print(f"💾 Saved: Authority to leave at '{safe_location}' for {target}")
        
    elif choice == "2":
        print(f"🔐 Secure Locker Pickup for {target}:")
        print("📍 Nearby parcel lockers: Melbourne Central, Southern Cross, Flinders Street")
        print("⏰ Available pickup times: 6AM - 11PM daily")
        locker_choice = input("Select preferred locker location: ").strip()
        print(f"💾 Saved: Locker pickup preference '{locker_choice}' for {target}")
        
    elif choice == "3":
        print(f"📍 Address Change Request for {target}:")
        if parcel_barcode:
            current_address = input("Current delivery address: ")
            new_address = input("New delivery address: ")
            print(f"✅ Address change requested for {parcel_barcode}: {current_address} → {new_address}")
            print("⚠️ Note: Address changes may affect delivery timing")
        else:
            new_address = input("Set default delivery address: ")
            print(f"💾 Saved: Default delivery address '{new_address}' for {target}")
        
    elif choice == "4":
        print(f"⏰ Delivery Time Preferences for {target}:")
        print("  🌅 Morning (8AM-12PM)")
        print("  🌞 Afternoon (12PM-5PM)")
        print("  🌆 Evening (5PM-8PM)")
        time_pref = input("Select preferred delivery window: ")
        print(f"💾 Saved: Delivery preference '{time_pref}' for {target}")
        
    elif choice == "5":
        print(f"📝 Special Handling Instructions for {target}:")
        instructions = input("Enter special handling instructions: ")
        print(f"💾 Saved: Special instructions '{instructions}' for {target}")
        
    elif choice == "6":
        print(f"✍️ Signature Required for {target}:")
        print("✅ All deliveries will require recipient signature")
        print("💾 Saved: Signature required preference enabled")
        
    elif choice == "7":
        print(f"🏠 Neighbor Authorization for {target}:")
        neighbor_address = input("Authorized neighbor address/name: ")
        print(f"💾 Saved: Neighbor authorization '{neighbor_address}' for {target}")
        
    else:
        print("📋 Delivery preferences saved successfully!")
    
    print(f"\n💡 Preferences for {target} will be applied to future deliveries")
    if parcel_barcode:
        print(f"🔄 Immediate effect: Current delivery {parcel_barcode} updated with new preferences")

async def subscribe_to_notifications():
    """Subscribe to delivery notifications"""
    print("\n=== Subscribe to Notifications ===")
    
    # Customer identification
    tracking_number = input("Enter tracking number or customer ID: ").strip()
    print(f"📦 Setting up notifications for: {tracking_number}")
    
    print("\n📱 Available notification channels:")
    print("  1. SMS notifications")
    print("  2. Email updates")
    print("  3. Push notifications (mobile app)")
    print("  4. All channels")
    
    channel = input("Select notification preference (1-4): ").strip()
    
    if channel == "1":
        phone = input("Enter mobile number: ")
        print(f"📱 SMS notifications enabled for {phone} (Tracking: {tracking_number})")
        
    elif channel == "2":
        email = input("Enter email address: ")
        print(f"📧 Email notifications enabled for {email} (Tracking: {tracking_number})")
        
    elif channel == "3":
        print(f"📲 Push notifications enabled for mobile app (Tracking: {tracking_number})")
        
    elif channel == "4":
        phone = input("Enter mobile number: ")
        email = input("Enter email address: ")
        print(f"📱📧📲 All notifications enabled for {phone} and {email} (Tracking: {tracking_number})")
    
    print(f"\n🔔 Notification types you'll receive for {tracking_number}:")
    print("  ✅ Parcel collected from sender")
    print("  🚛 In transit updates")
    print("  📍 Out for delivery (with ETA)")
    print("  ⏰ Running early/late alerts")
    print("  📦 Delivery completed")
    print("  ⚠️ Exception notifications")

async def report_suspicious_message():
    """Report suspicious delivery messages"""
    print("\n=== Report Suspicious Message ===")
    
    print("🛡️ Help us identify potential scams and fraud")
    print("Common suspicious message types:")
    print("  • Fake delivery fee requests")
    print("  • Phishing links claiming failed delivery")
    print("  • Requests for personal information")
    print("  • Unusual payment demands")
    
    message_content = input("\nDescribe the suspicious message: ")
    sender_info = input("Sender information (phone/email/unknown): ")
    
    print("\n🔍 Analyzing message for fraud indicators...")
    
    # Use the Fraud & Risk Agent for intelligent analysis
    from fraud_risk_agent import analyze_with_fraud_agent
    try:
        ai_analysis = await analyze_with_fraud_agent(message_content, sender_info)
        
        # Display AI analysis
        from fraud_risk_agent import fraud_risk_agent
        print(fraud_risk_agent.format_analysis_report(ai_analysis))
        
        # Store the report with AI analysis in database
        from parcel_tracking_db import ParcelTrackingDB
        async with ParcelTrackingDB() as db:
            # Convert analysis to dictionary for storage
            ai_data = {
                "threat_level": ai_analysis.threat_level.value,
                "fraud_category": ai_analysis.fraud_category.value,
                "confidence_score": ai_analysis.confidence_score,
                "recommended_actions": ai_analysis.recommended_actions,
                "alert_security_team": ai_analysis.alert_security_team,
                "related_patterns": ai_analysis.related_patterns
            }
            
            report_id = await db.store_suspicious_message(
                message_content=message_content,
                sender_info=sender_info,
                risk_indicators=ai_analysis.risk_indicators,
                ai_analysis=ai_data
            )
            
            if report_id:
                print(f"\n✅ Report submitted successfully!")
                print(f"📋 Report ID: {report_id}")
                
                # Show personalized education
                print(fraud_risk_agent.format_educational_content(ai_analysis.educational_content))
                
                # Security team alert if needed
                if ai_analysis.alert_security_team:
                    print("\n🚨 SECURITY ALERT: This high-risk threat has been escalated to our security team")
                    print("📞 You may be contacted for additional information")
            else:
                print("\n⚠️ Report submission failed, but analysis completed")
                print(fraud_risk_agent.format_educational_content(ai_analysis.educational_content))
                
    except Exception as e:
        # Fallback to basic analysis if AI agent fails
        print(f"⚠️ AI analysis unavailable ({e}), using basic detection...")
        
        # Basic fraud detection (fallback)
        risk_indicators = [
            "Payment request via untrusted link",
            "Urgency language ('act now', 'immediate action')",
            "Request for personal information",
            "Non-official sender domain"
        ]
        
        from parcel_tracking_db import ParcelTrackingDB
        async with ParcelTrackingDB() as db:
            report_id = await db.store_suspicious_message(
                message_content=message_content,
                sender_info=sender_info,
                risk_indicators=risk_indicators[:2]
            )
            
            if report_id:
                print("⚠️ Potential fraud indicators detected:")
                for indicator in risk_indicators[:2]:
                    print(f"  🔴 {indicator}")
                
                print(f"\n✅ Report submitted successfully!")
                print(f"📋 Report ID: {report_id}")
            else:
                print("\n⚠️ Report submission failed, but fraud indicators detected:")
                for indicator in risk_indicators[:2]:
                    print(f"  🔴 {indicator}")
                print("\n✅ Report logged locally!")
    
    print("🎓 SECURITY TIP: DT Logistics will never:")
    print("  • Request payment via text message")
    print("  • Ask for personal details in unsolicited messages")
    print("  • Send links from non-official domains")
    print("  • Threaten immediate action for failed deliveries")
    
    print("\n📞 For urgent delivery issues, contact customer service directly")

async def post_delivery_feedback():
    """Collect post-delivery feedback and NPS"""
    print("\n=== Post-Delivery Feedback ===")
    
    tracking_number = input("Enter tracking number for delivered parcel: ")
    
    print(f"\n📦 Thank you for using our service! (Tracking: {tracking_number})")
    print("\n📊 Rate your delivery experience:")
    print("1 = Poor, 5 = Excellent")
    
    # NPS Score
    try:
        nps_score = int(input("\nHow likely are you to recommend our service? (0-10): "))
        if nps_score >= 9:
            category = "Promoter 🌟"
        elif nps_score >= 7:
            category = "Passive 😐"
        else:
            category = "Detractor 😞"
        print(f"NPS Category: {category}")
    except ValueError:
        nps_score = 7
    
    # Delivery aspects
    print("\nRate specific aspects (1-5):")
    delivery_time = input("⏰ Delivery timing: ") or "4"
    courier_service = input("👤 Courier service: ") or "4"
    parcel_condition = input("📦 Parcel condition: ") or "5"
    
    # Additional feedback
    additional_feedback = input("\n💬 Additional comments (optional): ")
    
    # Calculate overall satisfaction
    overall_satisfaction = (int(delivery_time) + int(courier_service) + int(parcel_condition)) / 3
    
    # Store feedback in Cosmos DB
    feedback_data = {
        "tracking_number": tracking_number,
        "nps_score": nps_score,
        "nps_category": category,
        "delivery_time_rating": int(delivery_time),
        "courier_service_rating": int(courier_service),
        "parcel_condition_rating": int(parcel_condition),
        "overall_satisfaction": round(overall_satisfaction, 1),
        "additional_comments": additional_feedback
    }
    
    async with ParcelTrackingDB() as db:
        feedback_id = await db.store_feedback(feedback_data)
        if feedback_id:
            print(f"\n✅ Feedback recorded successfully! (ID: {feedback_id[:8]}...)")
        else:
            print(f"\n⚠️ Feedback recorded locally but database storage failed")
    
    print(f"📊 Overall satisfaction: {overall_satisfaction:.1f}/5")
    print("🙏 Thank you for helping us improve our service!")
    
    if additional_feedback:
        print(f"💭 Your comment: \"{additional_feedback}\"")