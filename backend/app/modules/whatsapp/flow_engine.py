"""
Conversational Flow Engine - processes incoming WhatsApp messages
against the configured flow nodes for an event.
"""
from typing import Optional, Dict
from app.database import get_db, get_redis
from bson import ObjectId


class FlowEngine:
    """Stateful conversation engine using Redis for session state."""

    @staticmethod
    async def get_session(phone: str) -> Optional[Dict]:
        redis = await get_redis()
        import json
        session = await redis.get(f"session:{phone}")
        return json.loads(session) if session else None

    @staticmethod
    async def set_session(phone: str, data: Dict, ttl: int = 3600):
        redis = await get_redis()
        import json
        await redis.set(f"session:{phone}", json.dumps(data), ex=ttl)

    @staticmethod
    async def clear_session(phone: str):
        redis = await get_redis()
        await redis.delete(f"session:{phone}")

    @staticmethod
    async def process_message(phone: str, message: str, tenant_id: str) -> str:
        db = await get_db()
        session = await FlowEngine.get_session(phone)

        # New conversation - find event from message or active registration
        if not session:
            # Try to match event from QR deep-link pattern
            registration = await db.registrations.find_one({"phone": phone, "tenant_id": tenant_id, "status": "in_progress"})
            if registration:
                session = {
                    "event_id": registration["event_id"],
                    "registration_id": str(registration["_id"]),
                    "current_node": registration["conversation_state"]["current_node"],
                    "responses": registration.get("responses", {}),
                }
            else:
                # Start new registration - find active event for this tenant
                event = await db.events.find_one({"tenant_id": tenant_id, "status": "active"})
                if not event:
                    return "No active events found. Please try again later."

                flow = await db.flows.find_one({"_id": ObjectId(event["flow_id"])}) if event.get("flow_id") else None
                if not flow or not flow.get("nodes"):
                    return "Event registration is not configured yet."

                # Create registration
                reg_doc = {
                    "tenant_id": tenant_id,
                    "event_id": str(event["_id"]),
                    "phone": phone,
                    "responses": {},
                    "conversation_state": {"current_node": flow["nodes"][0]["node_id"]},
                    "payment": {"status": "pending"},
                    "sheets_synced": False,
                    "status": "in_progress",
                }
                result = await db.registrations.insert_one(reg_doc)

                session = {
                    "event_id": str(event["_id"]),
                    "registration_id": str(result.inserted_id),
                    "current_node": flow["nodes"][0]["node_id"],
                    "responses": {},
                    "flow_id": str(flow["_id"]),
                }
                await FlowEngine.set_session(phone, session)
                return flow["nodes"][0]["content"]

        # Continue existing conversation
        event = await db.events.find_one({"_id": ObjectId(session["event_id"])})
        flow = await db.flows.find_one({"_id": ObjectId(session.get("flow_id") or event.get("flow_id"))})
        if not flow:
            return "Something went wrong. Please try again."

        nodes = {n["node_id"]: n for n in flow["nodes"]}
        current = nodes.get(session["current_node"])
        if not current:
            await FlowEngine.clear_session(phone)
            return "Conversation ended. Thank you!"

        # Store response if current node is a question
        if current["type"] == "question" and current.get("field_id"):
            session["responses"][current["field_id"]] = message
            await db.registrations.update_one(
                {"_id": ObjectId(session["registration_id"])},
                {"$set": {f"responses.{current['field_id']}": message}}
            )

        # Determine next node
        next_node_id = None
        if current["type"] == "condition":
            for cond in (current.get("conditions") or []):
                val = session["responses"].get(cond["field_id"], "")
                if FlowEngine._evaluate_condition(val, cond["operator"], cond["value"]):
                    next_node_id = cond["next"]
                    break
            if not next_node_id:
                next_node_id = current.get("next")
        else:
            next_node_id = current.get("next")

        if not next_node_id:
            # Flow complete
            await db.registrations.update_one(
                {"_id": ObjectId(session["registration_id"])},
                {"$set": {"status": "completed"}}
            )
            await FlowEngine.clear_session(phone)
            return "Registration complete! Thank you."

        next_node = nodes.get(next_node_id)
        if not next_node:
            await FlowEngine.clear_session(phone)
            return "Registration complete! Thank you."

        # Handle payment node
        if next_node["type"] == "payment":
            session["current_node"] = next_node_id
            await FlowEngine.set_session(phone, session)
            # Trigger payment link generation
            return f"{next_node['content']}\nPayment link will be sent shortly."

        session["current_node"] = next_node_id
        await FlowEngine.set_session(phone, session)
        return next_node["content"]

    @staticmethod
    def _evaluate_condition(value: str, operator: str, expected) -> bool:
        if operator == "eq":
            return value.lower() == str(expected).lower()
        elif operator == "neq":
            return value.lower() != str(expected).lower()
        elif operator == "contains":
            return str(expected).lower() in value.lower()
        return False
