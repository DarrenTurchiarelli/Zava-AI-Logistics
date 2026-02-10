# Changelog

All notable changes to Zava will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- AGENTS.md documentation for AI coding agents
- SECURITY.md with comprehensive security policies
- CHANGELOG.md (this file)
- .editorconfig for consistent code formatting
- .pre-commit-config.yaml for automated security checks
- CONTRIBUTING.md for contributor guidelines

### Changed

- Deployment script now automatically updates agent instructions via register_agent_tools.py

## [1.3.0] - 2026-02-10

### Added

- **Mobile-First Responsive UI**: Complete mobile optimization across all pages
  - Mobile bottom navigation bar with role-based links (logged-in vs public)
  - Card-based table views on mobile (tables convert to swipeable cards)
  - Touch-friendly 44px minimum targets, iOS safe area support
  - Dual-view manifests: desktop table + mobile card views
  - Collapsible side panels on chatbot page for full-width chat
  - Landscape mobile optimizations
  - iOS viewport height fix, double-tap zoom prevention
  - Skeleton loading animations, swipe hints for scrollable tables
- **Address Notes Lifecycle System**: Intelligent note categorization and expiry
  - Auto-categorisation of notes: Safety, Carded, Access, Property, General
  - TTL-based expiry: Carded 30d, General 90d, Safety/Access/Property 180d
  - Lazy pruning on read: expired notes filtered and removed automatically
  - Driver dismiss: drivers can remove inaccurate notes via AJAX dismiss button
  - Category badges with color coding in notes modal and delivery completion modal
  - Expiry date display on each note
  - `Scripts/cleanup_expired_notes.py`: Bulk cleanup utility (dry-run + apply modes)
  - `POST /api/address-notes/dismiss` API endpoint

### Changed

- `static/css/style.css`: Complete mobile-first CSS rewrite with breakpoints for phones, small phones, tablets, and landscape
- `static/js/app.js`: Added mobile detection, bottom nav highlighting, iOS viewport fix, double-tap prevention
- `templates/base.html`: Mobile meta tags, mobile bottom navigation bar, theme-color
- `templates/driver_manifest.html`: Mobile card view for deliveries, category badges on notes, dismiss button
- `templates/admin_manifests.html`: Dual view with desktop table + mobile cards, state filter for both views
- `templates/manifest_details.html`: Mobile card view for delivery items, responsive footer
- `templates/customer_service_chatbot.html`: Collapsible side panels, mobile chat optimizations
- `templates/dashboard.html`: 2-column stat cards on mobile, mobile-card table
- `templates/ai_insights.html`: Responsive metric cards, compact system health bar
- `templates/agent_dashboard.html`: 2-column agent cards, mobile-card performance table
- `templates/all_parcels.html`: Mobile register button, table-mobile-cards with data-labels
- `templates/index.html`: 2-column demo credentials and tech showcase cards
- `templates/register_parcel.html`: Side-by-side weight/value fields on mobile
- `templates/track_parcel.html`: 3-column weight/dimensions/value on all screen sizes
- `parcel_tracking_db.py`: Note categorization system (`NOTE_CATEGORIES`, `_categorise_note()`), expiry filtering in `get_address_notes()`, new `dismiss_address_note()` method
- `app.py`: Added `POST /api/address-notes/dismiss` endpoint

## [1.2.3] - 2026-01-13

### Fixed

- **Customer Service Agent:** Lodgement photos now display correctly when tracking parcels
  - Added `lodgement_photos` field to `track_parcel_tool` response in agent_tools.py
  - Updated agent instructions to acknowledge auto-displayed photos
  - Agents no longer tell customers to check "internal systems" when photos exist
- **Agent Instructions:** Added guidance for handling automatically-displayed photos

### Technical Details

- Modified: `agent_tools.py` line 66-75 to include lodgement photo metadata
- Modified: `agents/base.py` line 685-695 to add photo acknowledgment instructions
- Ref: GitHub issue tracking lodgement photo display

## [1.2.0] - 2025-12-18

### Added

- **8 Active AI Agents:** All Azure AI Foundry agents deployed and operational
  - Customer Service Agent (47 decisions)
  - Fraud Detection Agent (32 decisions)
  - Identity Verification Agent (18 decisions)
  - Dispatcher Agent (56 decisions)
  - Parcel Intake Agent (89 decisions)
  - Sorting Facility Agent (41 decisions)
  - Delivery Coordination Agent (38 decisions)
  - Optimization Agent (23 decisions)
- **Agent Performance Dashboard:** Real-time monitoring with 344+ total decisions tracked
  - Individual agent metrics and confidence scores
  - Average response times per agent
  - Success rate monitoring and trend analysis
- **Optimization Agent:** Network-wide cost reduction and predictive analytics
- **Sorting Facility Agent:** Real-time capacity monitoring and routing decisions
- **Delivery Coordination Agent:** Customer notifications and route sequencing

### Changed

- Enhanced fraud detection statistics with decision counts and confidence metrics
- Updated UI theme to modern blue design with colorblind-accessible colors
- Improved agent telemetry and performance tracking

### Technical Details

- Agent performance tracking in `app.py`
- Dashboard UI in `templates/agent_dashboard.html`
- Agent implementations in `agents/base.py` and `agents/fraud.py`

## [1.1.0] - 2025-12-10

### Added

- **Multi-Agent Workflows:** Automated fraud detection to customer service escalation
  - Fraud Detection Agent analyzes suspicious activity
  - Customer Service Agent generates personalized warnings
  - Identity Verification Agent for very high-risk cases (≥85%)
  - Automatic parcel holds for critical fraud (≥90%)
- **Fraud Detection Features:**
  - Multi-category threat analysis (phishing, impersonation, payment fraud)
  - Risk score calculation with confidence metrics
  - Educational content generation
  - Email/SMS analysis with OCR support
- **Agent Communication:** workflows/fraud_to_customer_service.py
  - Complete audit trail and workflow logging
  - Multi-channel notifications (email, SMS, phone)

### Changed

- Enhanced fraud detection with severity levels
- Improved customer notification system
- Better agent-to-agent communication patterns

### Technical Details

- New workflow system in `workflows/` directory
- Enhanced fraud agent in `agents/fraud.py`
- Multi-channel notification support

## [1.0.0] - 2025-11-15

### Added

- **Initial Release:** Core parcel tracking system
- **Web Application:** Flask-based web interface
  - Parcel registration and tracking
  - Driver manifest generation
  - Admin dashboard
  - Public tracking page
- **Database:** Azure Cosmos DB integration
  - Parcels container
  - Tracking events container
  - Approvals container
- **Azure AI Foundry Integration:**
  - Customer Service Agent with real-time tracking
  - Parcel Intake Agent for validation
  - Basic agent framework
- **Azure Maps Integration:**
  - Route optimization for drivers
  - Up to 20 parcels per manifest
  - Real-time traffic analysis
- **Driver Features:**
  - Mobile-friendly manifest view
  - Proof of delivery with photo capture
  - Route sequence optimization
- **Admin Features:**
  - User management system
  - Manifest generation and assignment
  - Parcel status monitoring
- **Authentication:**
  - User login system
  - Role-based access control
  - Default admin account

### Technical Details

- Python 3.11+ requirement
- Flask 3.0+ web framework
- Azure Cosmos DB for data storage
- Azure AI Foundry for intelligent agents
- Azure Maps for route optimization

## Version History Summary

- **v1.2.3** (2026-01-13): Photo display fixes
- **v1.2.0** (2025-12-18): 8 active agents + performance dashboard
- **v1.1.0** (2025-12-10): Multi-agent workflows + fraud detection
- **v1.0.0** (2025-11-15): Initial release with core tracking

---

## Release Types

### Major (x.0.0)

Breaking changes, major new features, architectural changes

### Minor (1.x.0)

New features, non-breaking changes, new agent capabilities

### Patch (1.2.x)

Bug fixes, security patches, documentation updates

---

## Future Roadmap

### Planned for v1.3.0

- [ ] Enhanced delivery predictions with ML
- [ ] Real-time customer notifications
- [ ] Driver mobile app
- [ ] Advanced analytics dashboard
- [ ] API for third-party integrations

### Under Consideration

- [ ] Multi-language support
- [ ] IoT sensor integration
- [ ] Blockchain-based tracking
- [ ] Carbon footprint tracking
- [ ] Predictive maintenance for vehicles

---

**Note:** This changelog follows [Keep a Changelog](https://keepachangelog.com/) format.  
For security vulnerabilities, see [SECURITY.md](SECURITY.md).  
For contribution guidelines, see [CONTRIBUTING.md](CONTRIBUTING.md).
