# Contributing to Zava

Thank you for your interest in contributing to Zava! This document provides guidelines and instructions for contributing to the project.

## 📋 Table of Contents

- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Code Standards](#code-standards)
- [Agent Development](#agent-development)
- [Testing Guidelines](#testing-guidelines)
- [Pull Request Process](#pull-request-process)
- [Security](#security)

## 🚀 Getting Started

### Prerequisites

- Python 3.11 or later
- Git
- Azure subscription (for testing agents)
- Visual Studio Code (recommended) or another code editor

### First-Time Setup

1. **Fork the repository** (if external contributor)

   ```bash
   # Fork via GitHub UI, then clone your fork
   git clone https://github.com/YOUR_USERNAME/dt_item_scanner.git
   cd dt_item_scanner
   ```

2. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt  # Development tools
   ```

3. **Configure environment**

   ```bash
   cp .env.example .env
   # Edit .env with your Azure credentials
   ```

4. **Initialize database**

   ```bash
   python parcel_tracking_db.py
   ```

5. **Generate demo data**

   ```bash
   python utils/generators/generate_demo_manifests.py --all
   ```

6. **Install pre-commit hooks**

   ```bash
   pip install pre-commit
   pre-commit install
   ```

7. **Verify setup**

   ```bash
   python -c "from agents.base import customer_service_agent; print('✓ Setup complete!')"
   ```

## 💻 Development Setup

### Running Locally

**Web Application:**

```bash
$env:FLASK_ENV='development'; py app.py
```

**CLI Interface:**

```bash
python main.py
```

**With Debug Mode:**

```bash
$env:DEBUG_MODE='true'; py app.py
```

### Project Structure

Familiarize yourself with the codebase structure:

- `agents/` - AI agent implementations
- `workflows/` - Multi-agent workflows
- `services/` - External service integrations (Maps, Speech, Vision)
- `templates/` - HTML templates
- `static/` - CSS, JavaScript, images
- `utils/` - Shared utilities and helpers

**Key Files:**

- `agents/base.py` - Core agent functions
- `agent_tools.py` - Cosmos DB tools for agents
- `parcel_tracking_db.py` - Database operations
- `app.py` - Flask web application
- `register_agent_tools.py` - Agent tool registration

See [AGENTS.md](AGENTS.md) for detailed architecture documentation.

## 📝 Code Standards

### Python Style Guide

We follow [PEP 8](https://pep8.org/) with some modifications:

```python
# ✅ GOOD: Type hints, docstrings, async/await
async def track_parcel(tracking_number: str) -> Dict[str, Any]:
    """
    Track a parcel by its tracking number.

    Args:
        tracking_number: The parcel tracking number

    Returns:
        Dictionary with parcel status and tracking history
    """
    async with ParcelTrackingDB() as db:
        return await db.get_parcel_by_tracking_number(tracking_number)
```

**Key Conventions:**

- Line length: 120 characters (not 80)
- Indentation: 4 spaces (Python), 2 spaces (HTML/JS/CSS)
- Quotes: Use double quotes for strings
- Type hints: Required for function parameters and returns
- Async/await: Use for all database and agent operations

### Naming Conventions

| Type | Convention | Example |
|------|-----------|---------|
| Files | snake_case | `parcel_tracking_db.py` |
| Classes | PascalCase | `ParcelTrackingDB` |
| Functions | snake_case | `get_parcel_by_tracking_number()` |
| Constants | UPPER_SNAKE_CASE | `CUSTOMER_SERVICE_AGENT_ID` |
| Variables | snake_case | `tracking_number` |
| Private | _prefix | `_internal_helper()` |

### Code Formatting

**Before committing, format your code:**

```bash
# Format Python code
black --line-length=120 .

# Sort imports
isort --profile black --line-length=120 .

# Lint code
flake8 . --max-line-length=120
```

Or rely on pre-commit hooks to do this automatically!

### Import Organization

```python
# Standard library imports
import os
import json
from typing import Dict, Any, Optional

# Third-party imports
from flask import Flask, request, jsonify
from azure.cosmos import CosmosClient

# Local imports
from agents.base import customer_service_agent
from parcel_tracking_db import ParcelTrackingDB
```

## 🤖 Agent Development

### Adding a New Agent

1. **Create agent function in `agents/base.py`:**

```python
async def new_agent_name(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Brief description of agent purpose.

    Args:
        request_data: Description of expected input

    Returns:
        Dictionary with success, response, and metadata
    """
    message = f"""
    Your structured prompt here...

    Context: {json.dumps(request_data, indent=2)}
    """

    return await call_azure_agent(NEW_AGENT_ID, message, request_data)
```

2. **Add environment variable:**

```bash
# In .env
NEW_AGENT_ID=asst_xxxxxxxxxxxxx
```

3. **Update `agents/base.py` imports:**

```python
NEW_AGENT_ID = os.getenv("NEW_AGENT_ID")
```

4. **Add agent to AGENTS.md documentation**

5. **Test the agent:**

```bash
python -c "
from agents.base import new_agent_name
import asyncio

result = asyncio.run(new_agent_name({'test': 'data'}))
print(result)
"
```

### Adding Agent Tools

1. **Define tool function in `agent_tools.py`:**

```python
async def new_tool_function(param: str) -> str:
    """
    Tool description for the agent.

    Args:
        param: Parameter description

    Returns:
        JSON string with tool result
    """
    try:
        async with ParcelTrackingDB() as db:
            result = await db.some_operation(param)

        return json.dumps({
            "success": True,
            "data": result
        })
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        })
```

2. **Add to AGENT_TOOLS list:**

```python
AGENT_TOOLS = [
    # ... existing tools ...
    {
        "type": "function",
        "function": {
            "name": "new_tool_function",
            "description": "Description for the AI agent",
            "parameters": {
                "type": "object",
                "properties": {
                    "param": {
                        "type": "string",
                        "description": "Parameter description"
                    }
                },
                "required": ["param"]
            }
        }
    }
]
```

3. **Register with agent:**

```bash
python register_agent_tools.py
```

### Agent Prompt Best Practices

**✅ GOOD:**

- Clear, specific instructions
- Structured format with sections
- Context provided as JSON
- Examples of expected output
- Natural language, conversational tone

**❌ AVOID:**

- Vague instructions
- Overly long prompts (>1000 words)
- Ambiguous formatting requirements
- Technical jargon without context

## 🧪 Testing Guidelines

### Manual Testing

```bash
# Test database connection
python parcel_tracking_db.py

# Test agent imports
python -c "from agents.base import customer_service_agent; print('✓')"

# Test agent tools
python register_agent_tools.py

# Test specific agent
python Scripts/check_demo_parcel.py
```

### Writing Tests (when implementing test suite)

```python
# tests/test_agents.py
import pytest
from agents.base import customer_service_agent

@pytest.mark.asyncio
async def test_customer_service_agent():
    result = await customer_service_agent({
        'details': 'Test query',
        'public_mode': True
    })

    assert result['success'] is True
    assert 'response' in result
```

### Before Committing

Pre-commit hooks will automatically run:

- ✅ Code formatting (Black)
- ✅ Import sorting (isort)
- ✅ Linting (flake8)
- ✅ Secret detection
- ✅ YAML/JSON validation
- ✅ Trailing whitespace removal

**Manual checks:**

```bash
# Run all pre-commit hooks manually
pre-commit run --all-files

# Test imports
python -c "from agents.base import *"
python -c "from parcel_tracking_db import *"

# Verify no secrets
git log --all --full-history -- .env
```

## 🔄 Pull Request Process

### Branch Naming

```bash
# Feature branches
git checkout -b feature/add-delivery-prediction-agent

# Bug fix branches
git checkout -b fix/photo-display-issue

# Documentation branches
git checkout -b docs/update-agent-guide
```

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```bash
# Format: <type>(<scope>): <description>

feat(agents): add delivery prediction agent
fix(customer-service): include lodgement photos in response
docs(agents): update AGENTS.md with new tool
refactor(database): optimize parcel query performance
test(agents): add unit tests for fraud detection
chore(deps): update azure-cosmos to 4.6.0
```

**Types:**

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `refactor`: Code refactoring
- `test`: Adding tests
- `chore`: Maintenance tasks
- `perf`: Performance improvements
- `ci`: CI/CD changes

### Pull Request Template

When creating a PR, include:

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Tested locally
- [ ] Pre-commit hooks pass
- [ ] Agent still responds correctly
- [ ] Database operations work

## Checklist
- [ ] Code follows style guidelines
- [ ] AGENTS.md updated (if applicable)
- [ ] CHANGELOG.md updated
- [ ] No secrets committed
- [ ] register_agent_tools.py run (if agent tools changed)

## Screenshots (if UI changes)
[Add screenshots]
```

### Review Process

1. **Automated Checks:** CI/CD pipeline runs tests
2. **Code Review:** Maintainer reviews code
3. **Feedback:** Address review comments
4. **Approval:** Once approved, PR can be merged
5. **Merge:** Squash and merge to keep history clean

## 🔐 Security

### Critical Rules

**❌ NEVER commit:**

- `.env` files
- Azure connection strings
- API keys or secrets
- Agent IDs (except as examples)
- Customer PII

**✅ ALWAYS:**

- Use environment variables for secrets
- Use managed identity for Azure deployments
- Run pre-commit hooks
- Check `.gitignore` includes sensitive files
- Review [SECURITY.md](SECURITY.md) before contributing

### Reporting Security Issues

**DO NOT create public GitHub issues for security vulnerabilities!**

Email: <security@dtlogistics.com.au>

See [SECURITY.md](SECURITY.md) for full policy.

## 📚 Additional Resources

- [AGENTS.md](AGENTS.md) - Agent architecture and development
- [SECURITY.md](SECURITY.md) - Security policies
- [CHANGELOG.md](CHANGELOG.md) - Version history
- [readme.md](readme.md) - User documentation

## 💬 Questions?

- **Documentation:** Check AGENTS.md first
- **Setup Issues:** Review this guide
- **Agent Development:** See AGENTS.md agent sections
- **Security:** Email <security@dtlogistics.com.au>
- **Other Questions:** Create a GitHub issue

## 🙏 Thank You

Your contributions help make Zava better for everyone. We appreciate your time and effort!

---

**Last Updated:** January 13, 2026  
**Maintained By:** Darren Turchiarelli (Microsoft)
