"""
Company Configuration
Centralized configuration for company branding and contact information
Update these values once and they will be applied throughout the application
"""

# Company Information
COMPANY_NAME = "Zava Logistics"
COMPANY_NAME_SHORT = "Zava"
COMPANY_TAGLINE = "Fast, Reliable, Trusted Delivery"
COMPANY_ABN = "12 345 678 901"

# Contact Information
COMPANY_PHONE = "1300 384 669"
COMPANY_EMAIL = "support@zava.com.au"
COMPANY_SUPPORT_EMAIL = "help@zava.com.au"
COMPANY_FRAUD_EMAIL = "security@zava.com.au"

# Address
COMPANY_ADDRESS_LINE1 = "123 Logistics Drive"
COMPANY_ADDRESS_LINE2 = "Melbourne VIC 3000"
COMPANY_ADDRESS_FULL = f"{COMPANY_ADDRESS_LINE1}, {COMPANY_ADDRESS_LINE2}"

# Web & Social
COMPANY_WEBSITE = "https://www.zava.com.au"
COMPANY_FACEBOOK = "https://facebook.com/zava"
COMPANY_TWITTER = "https://x.com/zava"
COMPANY_LINKEDIN = "https://linkedin.com/company/zava"

# Business Hours
BUSINESS_HOURS = "Monday - Friday: 8:00 AM - 6:00 PM"
BUSINESS_HOURS_WEEKEND = "Saturday: 9:00 AM - 1:00 PM"
SUPPORT_HOURS = "24/7 Customer Support Available"

# App Configuration
APP_VERSION = "1.0.0"
APP_COPYRIGHT = f"© 2025 {COMPANY_NAME}. All rights reserved."

# Service Areas (Australian States)
SERVICE_AREAS = {
    "NSW": "New South Wales",
    "VIC": "Victoria",
    "QLD": "Queensland",
    "SA": "South Australia",
    "WA": "Western Australia",
    "TAS": "Tasmania",
    "NT": "Northern Territory",
    "ACT": "Australian Capital Territory"
}

# Branding Colors (for future CSS customization)
BRAND_PRIMARY_COLOR = "#eb2525" 
BRAND_SECONDARY_COLOR = "#000000"  
BRAND_ACCENT_COLOR = "#ffffff" 
BRAND_DANGER_COLOR = "#eb2525"
BRAND_SUCCESS_COLOR = "#198754"  # Green for positive metrics, Active status, success rates
BRAND_ALERT_COLOR = "#fff3cd"  # Light yellow for alerts and warnings  

# Terms & Legal
TERMS_URL = f"{COMPANY_WEBSITE}/terms"
PRIVACY_URL = f"{COMPANY_WEBSITE}/privacy"
ABN = "12 345 678 901"  # Update with your actual ABN

def get_company_info():
    """Returns a dictionary of all company information"""
    return {
        'name': COMPANY_NAME,
        'name_short': COMPANY_NAME_SHORT,
        'tagline': COMPANY_TAGLINE,
        'phone': COMPANY_PHONE,
        'email': COMPANY_EMAIL,
        'support_email': COMPANY_SUPPORT_EMAIL,
        'fraud_email': COMPANY_FRAUD_EMAIL,
        'address': COMPANY_ADDRESS_FULL,
        'website': COMPANY_WEBSITE,
        'facebook': COMPANY_FACEBOOK,
        'twitter': COMPANY_TWITTER,
        'linkedin': COMPANY_LINKEDIN,
        'business_hours': BUSINESS_HOURS,
        'business_hours_weekend': BUSINESS_HOURS_WEEKEND,
        'support_hours': SUPPORT_HOURS,
        'version': APP_VERSION,
        'copyright': APP_COPYRIGHT,
        'terms_url': TERMS_URL,
        'privacy_url': PRIVACY_URL,
        'abn': ABN,
        'brand_primary_color': BRAND_PRIMARY_COLOR,
        'brand_secondary_color': BRAND_SECONDARY_COLOR,
        'brand_accent_color': BRAND_ACCENT_COLOR,
        'brand_danger_color': BRAND_DANGER_COLOR,
        'brand_success_color': BRAND_SUCCESS_COLOR,
        'brand_alert_color': BRAND_ALERT_COLOR
    }

def get_contact_methods():
    """Returns formatted contact methods for display"""
    return [
        {'icon': 'phone', 'label': 'Phone', 'value': COMPANY_PHONE, 'link': f'tel:{COMPANY_PHONE.replace(" ", "")}'},
        {'icon': 'envelope', 'label': 'Email', 'value': COMPANY_EMAIL, 'link': f'mailto:{COMPANY_EMAIL}'},
        {'icon': 'globe', 'label': 'Website', 'value': COMPANY_WEBSITE, 'link': COMPANY_WEBSITE},
    ]
