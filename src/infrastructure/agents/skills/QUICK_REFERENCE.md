# Quick Reference: Using the Prompt Loader

## Import the Module

```python
from src.infrastructure.agents.core.prompt_loader import get_agent_prompt, get_agent_skills
```

## Load a System Prompt

```python
# Load the customer service agent prompt
prompt = get_agent_prompt("customer-service")

# Load with cache disabled (force fresh read)
prompt = get_agent_prompt("customer-service", use_cache=False)
```

## Load Skills Documentation

```python
# Load skills documentation (optional)
skills = get_agent_skills("dispatcher")

# Returns None if SKILLS.md doesn't exist
if skills:
    print(skills)
```

## List Available Agents

```python
from src.infrastructure.agents.core.prompt_loader import list_available_agents

agents = list_available_agents()
print(agents)
# Output: ['customer-service', 'delivery-coordination', 'dispatcher', ...]
```

## Validate All Agents

```python
from src.infrastructure.agents.core.prompt_loader import validate_all_agents

results = validate_all_agents()
for agent_name, status in results.items():
    print(f"{agent_name}: {status}")
```

## Reload Prompts (Clear Cache)

```python
from src.infrastructure.agents.core.prompt_loader import reload_prompts

# Clear cache - useful during development
reload_prompts()
```

## Example: Using in an Agent Function

```python
async def my_agent(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """Custom agent function"""
    
    # Load base prompt from file
    base_prompt = get_agent_prompt("my-agent")
    
    # Enhance with request-specific context
    message = f"""{base_prompt}

## Current Request

**Customer Details:**
- Name: {request_data.get('customer_name')}
- Issue: {request_data.get('issue')}

Provide assistance based on the above information.
"""
    
    # Call Azure AI agent
    return await call_azure_agent(MY_AGENT_ID, message, request_data)
```

## Folder Structure

```
Agent-Skills/
  {agent-name}/
    system-prompt.md   # Required: Base system prompt
    SKILLS.md          # Optional: Capabilities documentation
```

## Error Handling

```python
try:
    prompt = get_agent_prompt("nonexistent-agent")
except FileNotFoundError as e:
    print(f"Agent not found: {e}")
    # Handle gracefully
```

## Best Practices

1. **Load once**: Prompts are cached, so load them at function start
2. **Keep prompts clean**: Separate base behavior (in file) from request context (in code)
3. **Validate changes**: Run `python agents/prompt_loader.py` after editing prompts
4. **Version control**: Commit prompt changes separately from code changes
5. **Document changes**: Update SKILLS.md when prompt behavior changes

## Testing

```bash
# Validate all agent prompts
python src/infrastructure/agents/core/prompt_loader.py

# Test importing in your code
python -c "from src.infrastructure.agents.core.base import customer_service_agent; print('✓ OK')"

# Test a specific agent
python -c "from src.infrastructure.agents.core.prompt_loader import get_agent_prompt; print(get_agent_prompt('dispatcher')[:100])"
```

## Common Patterns

### Pattern 1: Conversational Agent with Context
```python
base_prompt = get_agent_prompt("customer-service")
message = f"""{base_prompt}

## Current Conversation

**Customer Question:** {question}
**Previous Context:** {context}

Respond naturally and helpfully.
"""
```

### Pattern 2: Structured Analysis Agent
```python
base_prompt = get_agent_prompt("fraud-detection")
message = f"""{base_prompt}

## Analysis Task

**Message Content:** {message_content}
**Sender Info:** {sender_info}

Provide risk assessment with score, indicators, and recommendations.
"""
```

### Pattern 3: Batch Processing Agent
```python
base_prompt = get_agent_prompt("dispatcher")
parcels_json = json.dumps(parcels, indent=2)

message = f"""{base_prompt}

## Route Assignment Task

**Parcels to Assign:**
{parcels_json}

Provide optimized driver assignments.
"""
```

## Troubleshooting

### Issue: FileNotFoundError
**Solution:** Check that the agent folder exists in `Agent-Skills/` and has `system-prompt.md`

### Issue: Empty prompt
**Solution:** Ensure `system-prompt.md` has content (not empty file)

### Issue: Changes not reflecting
**Solution:** Call `reload_prompts()` or restart your application

### Issue: Import errors
**Solution:** Ensure you're in the project root directory and Python path is set correctly

## CLI Commands

```bash
# Validate all prompts
python src/infrastructure/agents/core/prompt_loader.py

# Test specific agent
python -c "from src.infrastructure.agents.core.prompt_loader import get_agent_prompt; print(get_agent_prompt('customer-service'))"

# List all agents
python -c "from src.infrastructure.agents.core.prompt_loader import list_available_agents; print(list_available_agents())"

# Validate and get details
python -c "from src.infrastructure.agents.core.prompt_loader import validate_all_agents; import json; print(json.dumps(validate_all_agents(), indent=2))"
```
