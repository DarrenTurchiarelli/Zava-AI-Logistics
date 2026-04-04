#!/usr/bin/env python3
"""Pre-deployment validation script for Zava Logistics.

Checks all prerequisites before running deploy_to_azure.ps1
"""

import subprocess
import sys
from pathlib import Path

# Colors for terminal output
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    RESET = '\033[0m'

def print_header(text):
    """Print section header"""
    print(f"\n{Colors.YELLOW}{text}{Colors.RESET}")

def print_success(text):
    """Print success message"""
    print(f"  {Colors.GREEN}√ {text}{Colors.RESET}")

def print_failure(text):
    """Print failure message"""
    print(f"  {Colors.RED}× {text}{Colors.RESET}")

def check_azure_cli():
    """Check Azure CLI installation and authentication"""
    print_header("Checking Azure CLI...")
    
    try:
        # Check if Azure CLI is installed
        subprocess.run(['az', 'version'], capture_output=True, check=True)
        
        # Check if authenticated
        result = subprocess.run(
            ['az', 'account', 'show'],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            import json
            account = json.loads(result.stdout)
            print_success(f"Azure CLI authenticated as {account['user']['name']}")
            return True
        else:
            print_failure("Not logged in. Run: az login")
            return False
            
    except (subprocess.CalledProcessError, FileNotFoundError):
        print_failure("Azure CLI not installed")
        return False

def check_python_version():
    """Check Python version >= 3.11"""
    print_header("Checking Python version...")
    
    version = sys.version_info
    if version >= (3, 11):
        print_success(f"Python {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print_failure(f"Python 3.11+ required (found {version.major}.{version.minor})")
        return False

def check_python_packages():
    """Check required Python packages"""
    print_header("Checking Python packages...")
    
    required = [
        'flask', 'azure-cosmos', 'azure-identity', 'openai', 
        'pydantic', 'pydantic_settings', 'python-dotenv'
    ]
    
    try:
        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'list'],
            capture_output=True,
            text=True,
            check=True
        )
        
        installed = result.stdout.lower()
        missing = [pkg for pkg in required if pkg.lower() not in installed]
        
        if not missing:
            print_success(f"All {len(required)} required packages installed")
            return True
        else:
            print_failure(f"Missing packages: {', '.join(missing)}")
            print(f"    Run: pip install -r requirements.txt")
            return False
            
    except subprocess.CalledProcessError:
        print_failure("Could not check installed packages")
        return False

def check_project_structure():
    """Check critical project files exist"""
    print_header("Checking project structure...")
    
    critical_files = [
        'infra/main.bicep',
        'scripts/create_foundry_agents_openai.py',
        'scripts/register_agent_tools_openai.py',
        'src/infrastructure/agents/skills/customer-service/system-prompt.md',
        'src/infrastructure/agents/core/prompt_loader.py',
        'src/interfaces/web/app.py',
        'app.py',
        'requirements.txt',
        '.env.example'
    ]
    
    missing = []
    for file_path in critical_files:
        if not Path(file_path).exists():
            missing.append(file_path)
    
    if not missing:
        print_success(f"All {len(critical_files)} critical files present")
        return True
    else:
        print_failure(f"Missing files:")
        for file in missing:
            print(f"    - {file}")
        return False

def check_agent_skills():
    """Validate agent skills load correctly"""
    print_header("Validating agent skills...")
    
    try:
        result = subprocess.run(
            [sys.executable, 'scripts/validate_agent_skills.py'],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0 and 'SUCCESS' in result.stdout:
            print_success("All 9 agents validated")
            return True
        else:
            print_failure("Agent validation failed")
            print(f"    Output: {result.stdout[:200]}")
            return False
            
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        print_failure(f"Agent validation error: {e}")
        return False

def check_bicep_template():
    """Validate Bicep template syntax"""
    print_header("Validating Bicep template...")
    
    try:
        result = subprocess.run(
            ['bicep', 'build', 'infra/main.bicep'],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        # Check for errors (warnings are okay)
        if result.returncode == 0:
            print_success("Bicep template valid")
            return True
        else:
            # Check if only warnings (not errors)
            if 'Error' not in result.stderr and 'error' not in result.stderr:
                print_success("Bicep template valid (warnings only)")
                return True
            else:
                print_failure("Bicep template has errors")
                print(f"    {result.stderr[:200]}")
                return False
                
    except FileNotFoundError:
        print_failure("Bicep CLI not installed")
        return False
    except subprocess.TimeoutExpired:
        print_failure("Bicep validation timed out")
        return False

def check_flask_imports():
    """Test Flask application imports"""
    print_header("Testing Flask application...")
    
    try:
        result = subprocess.run(
            [sys.executable, '-c', 'from src.interfaces.web.app import create_app'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            print_success("Flask app imports successfully")
            return True
        else:
            print_failure("Flask app import error")
            print(f"    {result.stderr[:200]}")
            return False
            
    except subprocess.TimeoutExpired:
        print_failure("Flask import timed out")
        return False

def main():
    """Run all pre-deployment checks"""
    print(f"\n{Colors.CYAN}{'='*60}")
    print(f"  Zava Logistics - Pre-Deployment Check")
    print(f"{'='*60}{Colors.RESET}\n")
    
    checks = [
        check_azure_cli,
        check_python_version,
        check_python_packages,
        check_project_structure,
        check_agent_skills,
        check_bicep_template,
        check_flask_imports
    ]
    
    results = [check() for check in checks]
    passed = sum(results)
    total = len(results)
    
    # Print summary
    print(f"\n{Colors.CYAN}{'='*60}{Colors.RESET}")
    if all(results):
        print(f"{Colors.GREEN}  √√√  READY FOR DEPLOYMENT  √√√{Colors.RESET}")
        print(f"{Colors.CYAN}{'='*60}{Colors.RESET}\n")
        print(f"{Colors.CYAN}Run: .\\deploy_to_azure.ps1{Colors.RESET}\n")
        return 0
    else:
        print(f"{Colors.RED}  ×××  {total - passed} ISSUES FOUND  ×××{Colors.RESET}")
        print(f"{Colors.CYAN}{'='*60}{Colors.RESET}\n")
        print(f"{Colors.YELLOW}Fix the issues above before deploying.{Colors.RESET}\n")
        return 1

if __name__ == '__main__':
    sys.exit(main())
