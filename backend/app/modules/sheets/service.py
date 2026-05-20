from bson import ObjectId
from fastapi import HTTPException
from app.database import get_db, get_tenant_db
from app.core.security import decrypt_secret
import json


class SheetsService:
    @staticmethod
    async def sync_registrations(tenant_id: str, event_id: str):
        from google.oauth2.service_account import Credentials
        from googleapiclient.discovery import build

        main_db = await get_db()
        db = await get_tenant_db(tenant_id)
        tenant = await main_db.tenants.find_one({"_id": ObjectId(tenant_id)})
        event = await db.events.find_one({"_id": ObjectId(event_id)})

        if not event or not event.get("sheets_config"):
            raise HTTPException(status_code=400, detail="Sheets not configured for this event")

        creds_json = decrypt_secret(tenant["config"]["google_sheets_credentials"])
        creds = Credentials.from_service_account_info(json.loads(creds_json), scopes=["https://www.googleapis.com/auth/spreadsheets"])
        service = build("sheets", "v4", credentials=creds)

        sheets_config = event["sheets_config"]
        registrations = await db.registrations.find({"event_id": event_id, "status": "completed", "sheets_synced": False}).to_list(500)

        if not registrations:
            return {"synced": 0}

        column_mapping = sheets_config["column_mapping"]
        rows = []
        for reg in registrations:
            row = []
            for field_id, col in sorted(column_mapping.items(), key=lambda x: x[1]):
                row.append(reg.get("responses", {}).get(field_id, ""))
            rows.append(row)

        body = {"values": rows}
        service.spreadsheets().values().append(
            spreadsheetId=sheets_config["spreadsheet_id"],
            range=f"{sheets_config['sheet_name']}!A:Z",
            valueInputOption="RAW",
            body=body
        ).execute()

        # Mark as synced
        reg_ids = [r["_id"] for r in registrations]
        await db.registrations.update_many({"_id": {"$in": reg_ids}}, {"$set": {"sheets_synced": True}})

        return {"synced": len(rows)}

    @staticmethod
    async def get_mapping(tenant_id: str, event_id: str):
        db = await get_tenant_db(tenant_id)
        event = await db.events.find_one({"_id": ObjectId(event_id)})
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        return event.get("sheets_config", {})

    @staticmethod
    async def update_mapping(tenant_id: str, event_id: str, mapping: dict):
        db = await get_tenant_db(tenant_id)
        await db.events.update_one(
            {"_id": ObjectId(event_id)},
            {"$set": {"sheets_config.column_mapping": mapping}}
        )
        return {"message": "Mapping updated"}
