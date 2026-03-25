"""
Centralized prompt loader for Azure AI Foundry agents

Loads system prompts and skills documentation from Agent-Skills folder structure.
This eliminates hardcoded prompts and centralizes agent prompt management.

Folder structure:
    Agent-Skills/
        customer-service/
            system-prompt.md
            SKILLS.md
        dispatcher/
            system-prompt.md
            SKILLS.md
        ... (other agents)

Usage:
    from agents.prompt_loader import get_agent_prompt, get_agent_skills
    
    prompt = get_agent_prompt("customer-service")
    skills = get_agent_skills("customer-service")
"""

import os
from pathlib import Path
from typing import Dict, Optional


# Cache for loaded prompts (avoids repeated file I/O)
_prompt_cache: Dict[str, str] = {}
_skills_cache: Dict[str, str] = {}


def get_agent_skills_folder() -> Path:
    """
    Get the Agent-Skills folder path
    
    Returns:
        Path object pointing to Agent-Skills folder
    """
    # Get the project root (parent of agents folder)
    current_file = Path(__file__)
    project_root = current_file.parent.parent
    agent_skills_folder = project_root / "Agent-Skills"
    
    if not agent_skills_folder.exists():
        raise FileNotFoundError(
            f"Agent-Skills folder not found at: {agent_skills_folder}\n"
            "Expected structure: Agent-Skills/<agent-name>/system-prompt.md"
        )
    
    return agent_skills_folder


def get_agent_prompt(agent_name: str, use_cache: bool = True) -> str:
    """
    Load system prompt for a specific agent
    
    Args:
        agent_name: Name of agent subfolder (e.g., "customer-service", "dispatcher")
        use_cache: Whether to use cached prompts (default: True)
    
    Returns:
        System prompt text
        
    Raises:
        FileNotFoundError: If agent folder or system-prompt.md doesn't exist
        ValueError: If prompt is empty
    """
    # Check cache first
    if use_cache and agent_name in _prompt_cache:
        return _prompt_cache[agent_name]
    
    # Load from file
    agent_skills_folder = get_agent_skills_folder()
    agent_folder = agent_skills_folder / agent_name
    prompt_file = agent_folder / "system-prompt.md"
    
    if not agent_folder.exists():
        raise FileNotFoundError(
            f"Agent folder not found: {agent_folder}\n"
            f"Available agents: {list_available_agents()}"
        )
    
    if not prompt_file.exists():
        raise FileNotFoundError(
            f"System prompt file not found: {prompt_file}\n"
            f"Expected file: {agent_name}/system-prompt.md"
        )
    
    # Read prompt
    with open(prompt_file, "r", encoding="utf-8") as f:
        prompt = f.read().strip()
    
    if not prompt:
        raise ValueError(f"System prompt is empty for agent: {agent_name}")
    
    # Cache and return
    _prompt_cache[agent_name] = prompt
    return prompt


def get_agent_skills(agent_name: str, use_cache: bool = True) -> Optional[str]:
    """
    Load skills documentation for a specific agent
    
    Args:
        agent_name: Name of agent subfolder (e.g., "customer-service", "dispatcher")
        use_cache: Whether to use cached skills (default: True)
    
    Returns:
        Skills documentation text, or None if not found
    """
    # Check cache first
    if use_cache and agent_name in _skills_cache:
        return _skills_cache[agent_name]
    
    # Load from file
    agent_skills_folder = get_agent_skills_folder()
    agent_folder = agent_skills_folder / agent_name
    skills_file = agent_folder / "SKILLS.md"
    
    if not skills_file.exists():
        # Skills file is optional
        return None
    
    # Read skills
    with open(skills_file, "r", encoding="utf-8") as f:
        skills = f.read().strip()
    
    # Cache and return
    _skills_cache[agent_name] = skills
    return skills


def list_available_agents() -> list[str]:
    """
    List all available agent configurations
    
    Returns:
        List of agent names (folder names)
    """
    try:
        agent_skills_folder = get_agent_skills_folder()
        agents = []
        
        for item in agent_skills_folder.iterdir():
            if item.is_dir() and (item / "system-prompt.md").exists():
                agents.append(item.name)
        
        return sorted(agents)
    except FileNotFoundError:
        return []


def reload_prompts():
    """
    Clear prompt cache and force reload on next access
    Useful for development when editing prompts
    """
    global _prompt_cache, _skills_cache
    _prompt_cache.clear()
    _skills_cache.clear()


def validate_all_agents() -> Dict[str, Dict[str, bool]]:
    """
    Validate all agent configurations
    
    Returns:
        Dictionary with validation results for each agent
        {
            "agent-name": {
                "system_prompt": True/False,
                "skills": True/False,
                "prompt_size": 1234
            }
        }
    """
    results = {}
    
    try:
        agent_skills_folder = get_agent_skills_folder()
        
        for agent_folder in agent_skills_folder.iterdir():
            if not agent_folder.is_dir():
                continue
            
            agent_name = agent_folder.name
            results[agent_name] = {
                "system_prompt": (agent_folder / "system-prompt.md").exists(),
                "skills": (agent_folder / "SKILLS.md").exists(),
                "prompt_size": 0
            }
            
            # Try loading prompt to validate
            if results[agent_name]["system_prompt"]:
                try:
                    prompt = get_agent_prompt(agent_name, use_cache=False)
                    results[agent_name]["prompt_size"] = len(prompt)
                except Exception as e:
                    results[agent_name]["error"] = str(e)
    
    except FileNotFoundError as e:
        results["_error"] = str(e)
    
    return results


# Pre-load common agents at module import (optional optimization)
def _preload_common_agents():
    """Pre-load prompts for commonly used agents"""
    common_agents = [
        "customer-service",
        "dispatcher",
        "fraud-detection"
    ]
    
    for agent_name in common_agents:
        try:
            get_agent_prompt(agent_name)
        except Exception:
            # Silently ignore errors during pre-load
            pass


# Uncomment to enable pre-loading:
# _preload_common_agents()


if __name__ == "__main__":
    """Test the prompt loader"""
    print("=" * 60)
    print("Agent Prompt Loader - Validation")
    print("=" * 60)
    
    # List available agents
    agents = list_available_agents()
    print(f"\n📁 Available agents: {len(agents)}")
    for agent in agents:
        print(f"   - {agent}")
    
    # Validate all agents
    print("\n🔍 Validating agent configurations...")
    validation_results = validate_all_agents()
    
    for agent_name, status in validation_results.items():
        if agent_name == "_error":
            print(f"\n❌ Error: {status}")
            continue
        
        prompt_status = "✓" if status.get("system_prompt") else "✗"
        skills_status = "✓" if status.get("skills") else "○"
        size = status.get("prompt_size", 0)
        
        print(f"\n{agent_name}:")
        print(f"   System Prompt: {prompt_status} ({size} chars)")
        print(f"   Skills Doc: {skills_status}")
        
        if "error" in status:
            print(f"   ⚠️ Error: {status['error']}")
    
    # Test loading
    print("\n\n🧪 Testing prompt loading...")
    try:
        test_agent = "customer-service"
        prompt = get_agent_prompt(test_agent)
        print(f"\n✅ Successfully loaded {test_agent} prompt")
        print(f"   Length: {len(prompt)} characters")
        print(f"   Preview: {prompt[:100]}...")
    except Exception as e:
        print(f"\n❌ Failed to load prompt: {e}")
