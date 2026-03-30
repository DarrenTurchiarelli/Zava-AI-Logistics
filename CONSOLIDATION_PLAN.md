# Customer Service Chatbot Consolidation Plan

## Summary
`customer_service_chatbot.py` (215 lines) can be replaced with a simple helper function (20-30 lines) in `app.py`.

## What Gets Removed
- ❌ The entire `CustomerServiceChatbot` class
- ❌ Conversation history that's never used
- ❌ Redundant parcel pre-fetching (agent has track_parcel tool)
- ❌ Per-request company info injection

## What Gets Kept (Moved to Helper Function)
- ✅ Public vs Internal mode flag
- ✅ Thread ID passing
- ✅ Context building

## New Helper Function (add to app.py)

```python
async def call_customer_service_agent(
    query: str,
    tracking_number: str = None,
    thread_id: str = None,
    is_public: bool = False,
    customer_name: str = "Customer"
) -> Dict[str, Any]:
    """
    Simple wrapper to call customer service agent
    
    Args:
        query: User's question
        tracking_number: Optional tracking number for context
        thread_id: Optional conversation thread ID
        is_public: True for public chat widget, False for internal CS
        customer_name: Customer name for personalization
    
    Returns:
        Agent response
    """
    # Build context
    context = {
        "customer_name": customer_name,
        "issue_type": "inquiry",
        "details": query,
        "public_mode": is_public
    }
    
    if tracking_number:
        context["tracking_number"] = tracking_number
    
    # Call agent (agent handles tracking number extraction and data fetching via tools)
    return await customer_service_agent(context, thread_id=thread_id)
```

## Changes to app.py Routes

### Before (Current):
```python
@app.route("/api/chatbot/query", methods=["POST"])
def chatbot_query():
    from customer_service_chatbot import CustomerServiceChatbot
    
    async def process():
        async with ParcelTrackingDB() as db:
            chatbot = CustomerServiceChatbot(db)
            context = {"tracking_number": tracking_number}
            response = await chatbot.process_query(query, context, thread_id)
            return response
```

### After (Simplified):
```python
@app.route("/api/chatbot/query", methods=["POST"])
def chatbot_query():
    async def process():
        return await call_customer_service_agent(
            query=query,
            tracking_number=tracking_number,
            thread_id=thread_id,
            is_public=False
        )
```

## Benefits
1. **215 lines removed** from customer_service_chatbot.py
2. **Simpler code** - one helper function vs entire class
3. **No redundant database calls** - agent uses its tools
4. **Same functionality** - public/internal modes still work
5. **Thread persistence** - still passed to agent

## Migration Steps
1. Add helper function to app.py
2. Update all 5 routes to use helper
3. Delete customer_service_chatbot.py
4. Test all routes work correctly

## Files Affected
- `app.py` - Add helper, update 5 routes
- `customer_service_chatbot.py` - DELETE

## Estimated Impact
- **Lines removed**: 215
- **Lines added**: 30
- **Net reduction**: ~185 lines
- **Maintainability**: Significantly improved
