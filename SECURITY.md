# Security Policy

## 🔒 Overview

Zava handles sensitive customer data and Azure credentials. This document outlines our security practices and vulnerability reporting procedures.

## Supported Versions

We provide security updates for the following versions:

| Version | Supported          | Status |
| ------- | ------------------ | ------ |
| 1.2.x   | :white_check_mark: | Active development |
| 1.1.x   | :white_check_mark: | Security fixes only |
| 1.0.x   | :x:                | End of life |

## Reporting a Vulnerability

### Contact

- **Email:** <security@zavalogistics.com.au>
- **Response Time:** Within 48 hours
- **Severity Assessment:** Within 5 business days

### What to Include

1. Description of the vulnerability
2. Steps to reproduce
3. Potential impact
4. Suggested fix (if any)
5. Your contact information

### Process

1. **Report:** Send details to security email
2. **Acknowledgment:** We confirm receipt within 48 hours
3. **Investigation:** We assess severity and impact
4. **Fix:** We develop and test a patch
5. **Disclosure:** Coordinated disclosure after fix is deployed
6. **Credit:** We credit reporters in release notes (unless you prefer anonymity)

## Security Best Practices

### 🔐 Credentials Management

**❌ NEVER:**

- Commit `.env` files to git
- Hard-code API keys or connection strings
- Share Azure credentials via email or chat
- Store secrets in code comments
- Use production credentials in development

**✅ ALWAYS:**

- Use `.env.example` templates without actual values
- Use Azure Managed Identity for production deployments
- Rotate Azure keys every 90 days
- Use Azure Key Vault for sensitive configuration
- Enable MFA on all Azure accounts

### 🌐 Azure Security

**Managed Identity (Production):**

```bash
# Set in environment
USE_MANAGED_IDENTITY=true

# Never set these in production:
# COSMOS_CONNECTION_STRING=...
# COSMOS_DB_KEY=...
```

**RBAC Permissions:**

- Minimum required roles only
- Regular audit of role assignments
- Remove unused service principals

**Network Security:**

- HTTPS only (enforced in deployment script)
- Azure Private Link for Cosmos DB (optional)
- Restrict IP ranges in Azure portal

### 📦 Cosmos DB Security

**Data Protection:**

- Customer PII encrypted at rest (automatic)
- TLS 1.2+ for all connections
- Partition keys never contain PII
- Regular backup verification

**Access Control:**

- Use RBAC roles instead of keys when possible
- Rotate primary/secondary keys quarterly
- Audit database access logs monthly

**Query Safety:**

```python
# ✅ GOOD: Parameterized queries (built-in SDK protection)
async with ParcelTrackingDB() as db:
    parcel = await db.get_parcel_by_tracking_number(tracking_number)

# ❌ BAD: Raw SQL with user input (SDK prevents this anyway)
# Don't construct raw queries with user input
```

### 🤖 AI Agent Security

**Prompt Injection Protection:**

- Validate all user inputs before sending to agents
- Sanitize tracking numbers (alphanumeric only)
- Rate limit agent API calls
- Monitor for suspicious patterns

**Agent Access Control:**

- Agents use read-only Cosmos DB roles where possible
- Customer Service Agent: Read-only access to parcels
- Fraud Detection Agent: Audit logs all decisions
- Identity Verification Agent: Logs all verification attempts

**Tool Function Security:**

```python
# ✅ GOOD: Validate inputs
async def track_parcel_tool(tracking_number: str) -> str:
    # Sanitize input
    if not re.match(r'^[A-Z0-9]+$', tracking_number):
        return json.dumps({"error": "Invalid tracking number format"})

    # Proceed with database query
    async with ParcelTrackingDB() as db:
        ...
```

### 🚪 Web Application Security

**Flask Security:**

- Secret keys: 32+ random characters
- Session timeout: 30 minutes
- CSRF protection enabled
- Content Security Policy headers

**Authentication:**

- Password hashing with bcrypt
- Failed login attempt limiting
- Session invalidation on logout
- Secure cookie flags (`httponly`, `secure`)

**Input Validation:**

- Validate all form inputs server-side
- Sanitize file uploads
- Limit file upload sizes
- Validate tracking number formats

### 📸 Photo Upload Security

**File Handling:**

```python
# ✅ GOOD: Validate and limit
if photo_file and photo_file.filename:
    # Check file size (max 10MB)
    photo_bytes = photo_file.read()
    if len(photo_bytes) > 10 * 1024 * 1024:
        return error("File too large")

    # Validate image format
    try:
        from PIL import Image
        import io
        img = Image.open(io.BytesIO(photo_bytes))
        img.verify()  # Verify it's a valid image
    except:
        return error("Invalid image file")
```

**Storage:**

- Photos stored as base64 in Cosmos DB
- Maximum size: 10MB per photo
- Automatic cleanup of old photos (30 days)

## Environment Variables Security

### Required vs Optional

```bash
# ✅ Required (fail if missing)
AZURE_AI_PROJECT_ENDPOINT=https://...
COSMOS_DB_ENDPOINT=https://...

# ⚠️ Optional (graceful degradation)
AZURE_MAPS_SUBSCRIPTION_KEY=...
AZURE_SPEECH_KEY=...
```

### .env File Protection

```bash
# Verify .env is in .gitignore
git check-ignore .env  # Should return: .env

# Check for accidental commits
git log --all --full-history -- .env
```

## Deployment Security

### Pre-Deployment Checklist

- [ ] `.env` file not in deployment package
- [ ] `DEBUG_MODE` set to `false`
- [ ] Managed Identity enabled
- [ ] RBAC roles configured
- [ ] HTTPS enforced
- [ ] Application Insights enabled
- [ ] Log retention configured

### Azure App Service Security

```powershell
# Enable HTTPS only (deployment script does this)
az webapp update \
  --name <webapp-name> \
  --resource-group <rg> \
  --https-only true

# Enable diagnostic logging
az webapp log config \
  --name <webapp-name> \
  --resource-group <rg> \
  --application-logging filesystem \
  --detailed-error-messages true
```

### Monitoring & Alerts

- Set up Azure Monitor alerts for:
  - Failed authentication attempts
  - High RU consumption
  - Agent API errors
  - Unusual traffic patterns

## Incident Response

### Security Incident Levels

**🟢 Low:** Minor issue, no data exposure

- Response: 5 business days
- Example: Outdated dependency

**🟡 Medium:** Potential data exposure, no active exploitation

- Response: 2 business days
- Example: Exposed API endpoint

**🟠 High:** Active threat, limited data exposure

- Response: 24 hours
- Example: Authentication bypass

**🔴 Critical:** Active exploitation, PII exposure

- Response: Immediate
- Example: Database breach

### Response Steps

1. **Contain:** Isolate affected systems
2. **Assess:** Determine scope of breach
3. **Notify:** Inform affected parties
4. **Remediate:** Apply fixes and patches
5. **Review:** Post-incident analysis
6. **Document:** Update security procedures

## Compliance

### GDPR Compliance

- Customer data deletion on request
- Data export capabilities
- Audit trails for all PII access
- Privacy policy clearly stated

### Data Retention

- Parcel data: 90 days after delivery
- Tracking events: 12 months
- Audit logs: 24 months
- Photos: 30 days after delivery

## Security Tools

### Pre-Commit Hooks

```bash
# Install security checks
pip install pre-commit
pre-commit install

# Runs automatically on commit:
# - Checks for private keys
# - Scans for secrets
# - Validates YAML/JSON files
```

### Dependency Scanning

```bash
# Check for vulnerable dependencies
pip install safety
safety check --json

# Update dependencies
pip list --outdated
pip install --upgrade <package>
```

### Code Security Scanning

```bash
# Scan Python code for vulnerabilities
pip install bandit
bandit -r . -ll  # Only show medium/high severity
```

## Security Updates

### Notification Channels

- **GitHub Security Advisories:** Watch this repository
- **Email:** Subscribe to security mailing list
- **CHANGELOG.md:** All security fixes documented

### Update Policy

- **Critical:** Patch within 24 hours
- **High:** Patch within 1 week
- **Medium:** Patch in next minor release
- **Low:** Patch in next major release

## Questions?

For security questions or concerns:

- Review this document first
- Check AGENTS.md for agent-specific security
- Email: <security@dtlogistics.com.au>
- Do NOT create public GitHub issues for security vulnerabilities

---

**Last Updated:** January 13, 2026  
**Version:** 1.2.3  
**Security Contact:** <security@dtlogistics.com.au>
