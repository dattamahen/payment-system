from datetime import datetime
from bson import ObjectId
from fastapi import HTTPException
from app.database import get_db, get_tenant_db, get_redis
from app.core.security import decrypt_secret
import json
import re


def validate_field(value: str, field_type: str, options: list = None) -> bool:
    """Validates input based on field type."""
    if field_type == "email":
        return bool(re.match(r'^[\w.+-]+@[\w-]+\.[\w.]+$', value))
    if field_type == "phone":
        digits = re.sub(r'[\s\-\+\(\)]', '', value)
        return digits.isdigit() and len(digits) == 10
    if field_type == "text":
        return len(value) >= 2 and not any(c.isdigit() for c in value)
    if field_type == "number":
        return value.replace('.', '', 1).replace('-', '', 1).isdigit()
    if field_type == "select" and options:
        return value.lower() in [o.lower() for o in options]
    return True


class N8nService:
    @staticmethod
    async def get_questions(tenant_id: str, event_id: str):
        """Returns the event's form_fields as questions for n8n to ask via WhatsApp."""
        db = await get_tenant_db(tenant_id)
        event = await db.events.find_one({"_id": ObjectId(event_id)})
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        if event.get("status") not in ("active",):
            raise HTTPException(status_code=400, detail="Event is not accepting registrations")

        # Check deadline
        deadline = event.get("registration_deadline")
        if deadline and datetime.utcnow() > deadline:
            await db.events.update_one({"_id": ObjectId(event_id)}, {"$set": {"status": "stopped"}})
            raise HTTPException(status_code=400, detail="Registration deadline has passed")

        # Check max participants
        reg_count = await db.registrations.count_documents({"event_id": event_id})
        if reg_count >= event.get("max_participants", 500):
            raise HTTPException(status_code=400, detail="Event is full")

        form_fields = event.get("form_fields") or []
        return {
            "event_id": event_id,
            "event_name": event["name"],
            "pricing": event.get("pricing", {}),
            "questions": [
                {
                    "label": f["label"],
                    "type": f["type"],
                    "required": f["required"],
                    "options": f.get("options"),
                }
                for f in form_fields
            ],
        }

    @staticmethod
    async def submit_response(tenant_id: str, event_id: str, phone: str, responses: dict, payment_status: str):
        """Stores a completed registration from n8n."""
        db = await get_tenant_db(tenant_id)
        event = await db.events.find_one({"_id": ObjectId(event_id)})
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")

        # Check deadline
        deadline = event.get("registration_deadline")
        if deadline and datetime.utcnow() > deadline:
            await db.events.update_one({"_id": ObjectId(event_id)}, {"$set": {"status": "stopped"}})
            raise HTTPException(status_code=400, detail="Registration deadline has passed")

        # Check max participants
        reg_count = await db.registrations.count_documents({"event_id": event_id})
        if reg_count >= event.get("max_participants", 500):
            raise HTTPException(status_code=400, detail="Event is full")

        reg_doc = {
            "event_id": event_id,
            "phone": phone,
            "responses": responses,
            "payment": {"status": payment_status},
            "sheets_synced": False,
            "status": "completed" if payment_status == "paid" or event["pricing"]["type"] == "free" else "pending_payment",
            "created_at": datetime.utcnow(),
        }
        result = await db.registrations.insert_one(reg_doc)
        return {"registration_id": str(result.inserted_id), "status": reg_doc["status"]}

    @staticmethod
    async def sync_to_sheet(tenant_id: str, event_id: str):
        """Pushes unsynced registrations to the tenant's Google Sheet."""
        from google.oauth2.service_account import Credentials
        from googleapiclient.discovery import build

        main_db = await get_db()
        db = await get_tenant_db(tenant_id)

        tenant = await main_db.tenants.find_one({"_id": ObjectId(tenant_id)})
        event = await db.events.find_one({"_id": ObjectId(event_id)})
        if not event or not tenant:
            raise HTTPException(status_code=404, detail="Event or tenant not found")

        creds_json_enc = tenant.get("config", {}).get("google_sheets_credentials")
        sheets_config = event.get("sheets_config")
        if not creds_json_enc or not sheets_config:
            raise HTTPException(status_code=400, detail="Google Sheets not configured")

        # Get unsynced registrations
        registrations = await db.registrations.find({"event_id": event_id, "sheets_synced": False}).to_list(500)
        if not registrations:
            return {"synced": 0}

        # Build header from form_fields
        form_fields = event.get("form_fields") or []
        headers = ["Phone"] + [f["label"] for f in form_fields] + ["Status", "Registered At"]

        # Build rows
        rows = []
        for reg in registrations:
            row = [reg.get("phone", "")]
            for f in form_fields:
                row.append(reg.get("responses", {}).get(f["label"], ""))
            row.append(reg.get("status", ""))
            row.append(str(reg.get("created_at", "")))
            rows.append(row)

        # Connect to Google Sheets
        creds_json = decrypt_secret(creds_json_enc)
        creds = Credentials.from_service_account_info(
            json.loads(creds_json),
            scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
        service = build("sheets", "v4", credentials=creds)

        spreadsheet_id = sheets_config["spreadsheet_id"]
        sheet_name = sheets_config.get("sheet_name", "Registrations")

        # Check if headers exist, if not add them
        existing = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id, range=f"{sheet_name}!A1:Z1"
        ).execute()
        if not existing.get("values"):
            service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id, range=f"{sheet_name}!A1",
                valueInputOption="RAW", body={"values": [headers]}
            ).execute()

        # Append rows
        service.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id, range=f"{sheet_name}!A:Z",
            valueInputOption="RAW", body={"values": rows}
        ).execute()

        # Mark as synced
        reg_ids = [r["_id"] for r in registrations]
        await db.registrations.update_many({"_id": {"$in": reg_ids}}, {"$set": {"sheets_synced": True}})

        return {"synced": len(rows)}

    @staticmethod
    async def create_payment_link(tenant_id: str, event_id: str, registration_id: str, phone: str):
        """Creates a Razorpay payment link for n8n to send via WhatsApp."""
        import razorpay

        main_db = await get_db()
        db = await get_tenant_db(tenant_id)

        tenant = await main_db.tenants.find_one({"_id": ObjectId(tenant_id)})
        event = await db.events.find_one({"_id": ObjectId(event_id)})
        if not tenant or not event:
            raise HTTPException(status_code=404, detail="Tenant or event not found")

        if event["pricing"]["type"] == "free":
            return {"payment_required": False}

        key_id = decrypt_secret(tenant["config"]["razorpay_key_id"])
        key_secret = decrypt_secret(tenant["config"]["razorpay_key_secret"])
        client = razorpay.Client(auth=(key_id, key_secret))

        amount = event["pricing"]["amount"] * 100  # Razorpay expects paise
        payment_link_data = {
            "amount": amount,
            "currency": event["pricing"].get("currency", "INR"),
            "description": f"Registration: {event['name']}",
            "customer": {"contact": phone},
            "notify": {"sms": False, "email": False},
            "expire_by": int(__import__('time').time()) + 7200,  # 2 hours from now
            "notes": {
                "tenant_id": tenant_id,
                "event_id": event_id,
                "registration_id": registration_id,
            },
        }
        payment_link = client.payment_link.create(payment_link_data)

        # Update registration with payment info
        await db.registrations.update_one(
            {"_id": ObjectId(registration_id)},
            {"$set": {
                "payment.razorpay_link_id": payment_link["id"],
                "payment.short_url": payment_link["short_url"],
                "payment.amount": event["pricing"]["amount"],
                "payment.status": "link_sent",
            }}
        )

        return {
            "payment_required": True,
            "payment_link": payment_link["short_url"],
            "amount": event["pricing"]["amount"],
            "currency": event["pricing"].get("currency", "INR"),
        }

    @staticmethod
    async def resolve_by_whatsapp(wa_number: str):
        """Finds tenant by their WhatsApp number and returns active events."""
        db = await get_db()
        tenant = await db.tenants.find_one({"config.whatsapp_number": wa_number, "status": "active"})
        if not tenant:
            raise HTTPException(status_code=404, detail="No tenant found for this WhatsApp number")

        tenant_id = str(tenant["_id"])
        tenant_db = await get_tenant_db(tenant_id)
        events = await tenant_db.events.find({"status": "active"}).to_list(50)

        active_events = []
        for e in events:
            deadline = e.get("registration_deadline")
            if deadline and datetime.utcnow() > deadline:
                await tenant_db.events.update_one({"_id": e["_id"]}, {"$set": {"status": "stopped"}})
                continue
            active_events.append({
                "event_id": str(e["_id"]),
                "name": e["name"],
                "pricing": e.get("pricing", {}),
            })

        return {
            "tenant_id": tenant_id,
            "tenant_name": tenant["name"],
            "wa_access_token": decrypt_secret(tenant["config"]["whatsapp_api_key"]) if tenant.get("config", {}).get("whatsapp_api_key") else None,
            "events": active_events,
        }

    @staticmethod
    async def handle_conversation(phone: str, text: str, wa_number: str):
        """Stateful conversation handler. Manages sessions in Redis/memory cache."""
        redis = await get_redis()
        session_key = f"reg_session:{phone}"
        session_raw = await redis.get(session_key)
        session = json.loads(session_raw) if session_raw else None

        # If user sends a greeting while in a session, auto-reset and start fresh
        if session and text.strip().lower() in ('hi', 'hello', 'hey', 'start', 'restart'):
            await redis.delete(session_key)
            session = None

        # Resolve tenant from WhatsApp number (match by phone_number_id or display number)
        db = await get_db()
        tenant = await db.tenants.find_one({
            "$or": [
                {"config.whatsapp_number": wa_number},
                {"config.whatsapp_phone_number_id": wa_number},
            ],
            "config.whatsapp_api_key": {"$exists": True},
            "status": "active"
        })
        if not tenant:
            return {"action": "reply", "message": "Sorry, this service is not available."}

        tenant_id = str(tenant["_id"])
        tenant_db = await get_tenant_db(tenant_id)

        # No active session - start new
        if not session:
            events = await tenant_db.events.find({"status": "active"}).to_list(50)
            # Filter out expired events
            valid_events = []
            for e in events:
                deadline = e.get("registration_deadline")
                if deadline and datetime.utcnow() > deadline:
                    await tenant_db.events.update_one({"_id": e["_id"]}, {"$set": {"status": "stopped"}})
                    continue
                reg_count = await tenant_db.registrations.count_documents({"event_id": str(e["_id"])})
                if reg_count < e.get("max_participants", 500):
                    valid_events.append(e)

            if not valid_events:
                return {"action": "reply", "message": "Sorry, no events are currently accepting registrations."}

            # If single event, start directly
            if len(valid_events) == 1:
                event = valid_events[0]
                event_id = str(event["_id"])
                form_fields = event.get("form_fields") or []
                if not form_fields:
                    return {"action": "reply", "message": "This event has no registration form configured."}

                session = {
                    "tenant_id": tenant_id,
                    "event_id": event_id,
                    "event_name": event["name"],
                    "questions": form_fields,
                    "current": 0,
                    "responses": {},
                    "pricing": event.get("pricing", {}),
                }
                await redis.set(session_key, json.dumps(session), ex=3600)

                # Build welcome message with venue details
                venue = event.get("venue") or {}
                msg = f"\U0001f3c6 *{event['name']}*\n\n"
                if venue.get("name"):
                    msg += f"\U0001f4cd *Venue:* {venue['name']}\n"
                if venue.get("address"):
                    msg += f"{venue['address']}"
                    if venue.get("city"):
                        msg += f", {venue['city']}"
                    msg += "\n"
                if venue.get("map_url"):
                    msg += f"\U0001f5fa *Map:* {venue['map_url']}\n"
                if event.get("event_date"):
                    msg += f"\U0001f4c5 *Date:* {event['event_date']}\n"
                pricing = event.get("pricing", {})
                if pricing.get("type") == "paid":
                    msg += f"\U0001f4b0 *Fee:* \u20b9{pricing.get('amount', 0)}\n"
                else:
                    msg += f"\U0001f4b0 *Fee:* Free\n"
                msg += f"\n---\n\nPlease answer the following to register:\n\n"
                q = form_fields[0]
                msg += f"*Q1:* {q['label']}"
                if q.get("options"):
                    msg += " (Options: " + ", ".join(q["options"]) + ")"
                return {"action": "reply", "message": msg}

            # Multiple events - ask user to choose
            event_list = ", ".join([f"{i+1}. {e['name']}" for i, e in enumerate(valid_events)])
            session = {
                "tenant_id": tenant_id,
                "state": "choosing_event",
                "events": [{"id": str(e["_id"]), "name": e["name"], "form_fields": e.get("form_fields", []), "pricing": e.get("pricing", {})} for e in valid_events],
            }
            await redis.set(session_key, json.dumps(session), ex=3600)
            return {"action": "reply", "message": f"Hi! Which event? {event_list}. Reply with the number."}

        # Choosing event
        if session.get("state") == "choosing_event":
            try:
                choice = int(text.strip()) - 1
                chosen = session["events"][choice]
            except (ValueError, IndexError):
                return {"action": "reply", "message": "Please reply with a valid number."}

            form_fields = chosen["form_fields"]
            if not form_fields:
                await redis.delete(session_key)
                return {"action": "reply", "message": "This event has no registration form configured."}

            session = {
                "tenant_id": session["tenant_id"],
                "event_id": chosen["id"],
                "event_name": chosen["name"],
                "questions": form_fields,
                "current": 0,
                "responses": {},
                "pricing": chosen["pricing"],
            }
            await redis.set(session_key, json.dumps(session), ex=3600)

            q = form_fields[0]
            msg = f"Registering for {chosen['name']}. Please answer: {q['label']}"
            if q.get("options"):
                msg += " (Options: " + ", ".join(q["options"]) + ")"
            return {"action": "reply", "message": msg}

        # Answering questions
        questions = session["questions"]
        current_idx = session["current"]
        current_q = questions[current_idx]

        # Validate answer
        if not validate_field(text.strip(), current_q.get("type", "text"), current_q.get("options")):
            if current_q.get("type") == "select" and current_q.get("options"):
                msg = f"Invalid option. Please choose from: {', '.join(current_q['options'])}"
            elif current_q.get("type") == "email":
                msg = f"Invalid email format. Please enter a valid email (e.g. name@example.com)"
            elif current_q.get("type") == "phone":
                msg = f"Invalid phone number. Please enter a valid 10-digit phone number"
            elif current_q.get("type") == "number":
                msg = f"Please enter a valid number"
            else:
                msg = f"Invalid input. Name must be at least 2 characters with no numbers. Try again: {current_q['label']}"
            return {"action": "reply", "message": msg}

        # Store answer
        session["responses"][current_q["label"]] = text.strip()
        session["current"] += 1

        # More questions?
        if session["current"] < len(questions):
            next_q = questions[session["current"]]
            await redis.set(session_key, json.dumps(session), ex=3600)
            msg = f"{next_q['label']}"
            if next_q.get("options"):
                msg += " (Options: " + ", ".join(next_q["options"]) + ")"
            return {"action": "reply", "message": msg}

        # All answered - submit
        tenant_id = session["tenant_id"]
        event_id = session["event_id"]
        pricing = session.get("pricing", {})
        is_free = pricing.get("type") != "paid"

        # Submit responses
        result = await N8nService.submit_response(
            tenant_id, event_id, phone, session["responses"],
            "paid" if is_free else "pending"
        )

        await redis.delete(session_key)

        if is_free:
            # Sync to sheet
            try:
                await N8nService.sync_to_sheet(tenant_id, event_id)
            except Exception:
                pass
            return {"action": "reply", "message": "Registration successful! Thank you."}

        # Paid event - create payment link
        try:
            payment = await N8nService.create_payment_link(
                tenant_id, event_id, result["registration_id"], phone
            )
            return {
                "action": "reply",
                "message": f"Almost done! Please pay Rs.{payment['amount']} via UPI to complete registration: {payment['payment_link']} (Link expires in 1 hour)"
            }
        except Exception as e:
            return {"action": "reply", "message": f"Registration saved but payment link failed. Please contact support."}
