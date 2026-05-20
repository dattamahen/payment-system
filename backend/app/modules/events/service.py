from datetime import datetime
from bson import ObjectId
from fastapi import HTTPException
from app.database import get_tenant_db
from app.modules.events.schemas import EventCreate, EventUpdate
from app.utils.qr_generator import generate_whatsapp_qr


class EventService:
    @staticmethod
    async def create(tenant_id: str, body: EventCreate):
        db = await get_tenant_db(tenant_id)
        doc = {
            "tenant_id": tenant_id,
            "name": body.name,
            "slug": body.slug,
            "description": body.description,
            "event_date": body.event_date,
            "registration_deadline": body.registration_deadline,
            "max_participants": body.max_participants,
            "pricing": body.pricing.model_dump(),
            "venue": body.venue.model_dump() if body.venue else None,
            "form_fields": [f.model_dump() for f in body.form_fields] if body.form_fields else None,
            "form_id": body.form_id,
            "flow_id": body.flow_id,
            "sheets_config": body.sheets_config.model_dump() if body.sheets_config else None,
            "qr_code_url": None,
            "status": "draft",
            "created_at": datetime.utcnow(),
        }
        result = await db.events.insert_one(doc)
        # Save questions separately for n8n integration
        if body.form_fields:
            await db.questions.update_one(
                {"event_id": str(result.inserted_id)},
                {"$set": {
                    "event_id": str(result.inserted_id),
                    "event_name": body.name,
                    "fields": [f.model_dump() for f in body.form_fields],
                    "updated_at": datetime.utcnow(),
                }},
                upsert=True
            )
        return {"id": str(result.inserted_id), "tenant_id": tenant_id, "name": body.name, "slug": body.slug, "status": "draft", "pricing": body.pricing, "venue": body.venue, "form_fields": body.form_fields, "created_at": doc["created_at"]}

    @staticmethod
    async def list_by_tenant(tenant_id: str):
        db = await get_tenant_db(tenant_id)
        events = await db.events.find().to_list(100)
        result = []
        for e in events:
            event_id = str(e["_id"])
            reg_count = await db.registrations.count_documents({"event_id": event_id})
            result.append({"id": event_id, "tenant_id": tenant_id, "name": e["name"], "slug": e["slug"], "status": e["status"], "pricing": e["pricing"], "venue": e.get("venue"), "form_fields": e.get("form_fields"), "registrations_count": reg_count, "qr_code_url": e.get("qr_code_url"), "created_at": e.get("created_at")})
        return result

    @staticmethod
    async def get(event_id: str, tenant_id: str):
        db = await get_tenant_db(tenant_id)
        event = await db.events.find_one({"_id": ObjectId(event_id)})
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        reg_count = await db.registrations.count_documents({"event_id": event_id})
        return {"id": str(event["_id"]), "tenant_id": tenant_id, "name": event["name"], "slug": event["slug"], "status": event["status"], "pricing": event["pricing"], "venue": event.get("venue"), "form_fields": event.get("form_fields"), "registrations_count": reg_count, "qr_code_url": event.get("qr_code_url"), "created_at": event.get("created_at")}

    @staticmethod
    async def update(event_id: str, tenant_id: str, body: EventUpdate):
        db = await get_tenant_db(tenant_id)
        update_data = body.model_dump(exclude_none=True)
        if "pricing" in update_data:
            update_data["pricing"] = update_data["pricing"] if isinstance(update_data["pricing"], dict) else update_data["pricing"].model_dump()
        await db.events.update_one({"_id": ObjectId(event_id)}, {"$set": update_data})
        return await EventService.get(event_id, tenant_id)

    @staticmethod
    async def generate_qr(event_id: str, tenant_id: str):
        db = await get_tenant_db(tenant_id)
        from app.database import get_db
        main_db = await get_db()
        tenant = await main_db.tenants.find_one({"_id": ObjectId(tenant_id)})
        event = await db.events.find_one({"_id": ObjectId(event_id)})
        if not event or not tenant:
            raise HTTPException(status_code=404, detail="Event or tenant not found")

        whatsapp_number = tenant.get("config", {}).get("whatsapp_number", "")
        message = f"Hi! I want to register for {event['name']}"
        qr_url = generate_whatsapp_qr(whatsapp_number, message, event_id)

        await db.events.update_one({"_id": ObjectId(event_id)}, {"$set": {"qr_code_url": qr_url}})
        return {"qr_code_url": qr_url}

    @staticmethod
    async def change_status(event_id: str, tenant_id: str, status: str):
        if status not in ("active", "paused", "stopped"):
            raise HTTPException(status_code=400, detail="Invalid status. Use: active, paused, stopped")
        db = await get_tenant_db(tenant_id)
        await db.events.update_one({"_id": ObjectId(event_id)}, {"$set": {"status": status}})
        return await EventService.get(event_id, tenant_id)

    @staticmethod
    async def get_registrations(event_id: str, tenant_id: str):
        db = await get_tenant_db(tenant_id)
        registrations = await db.registrations.find({"event_id": event_id}).sort("created_at", -1).to_list(500)
        return [{"id": str(r["_id"]), "phone": r.get("phone"), "responses": r.get("responses", {}), "payment": r.get("payment", {}), "status": r.get("status"), "created_at": r.get("created_at")} for r in registrations]

    @staticmethod
    async def generate_pdf(event_id: str, tenant_id: str):
        from io import BytesIO
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.units import mm
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet
        from fastapi.responses import StreamingResponse

        db = await get_tenant_db(tenant_id)
        event = await db.events.find_one({"_id": ObjectId(event_id)})
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")

        registrations = await db.registrations.find({"event_id": event_id}).sort("created_at", -1).to_list(500)
        form_fields = event.get("form_fields") or []

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=15*mm, rightMargin=15*mm, topMargin=20*mm, bottomMargin=20*mm)
        styles = getSampleStyleSheet()
        elements = []

        # Title
        elements.append(Paragraph(f"<b>{event['name']}</b> - Registrations", styles['Title']))
        elements.append(Spacer(1, 10))
        elements.append(Paragraph(f"Total: {len(registrations)} | Status: {event['status']}", styles['Normal']))
        elements.append(Spacer(1, 15))

        # Table header
        headers = ['#'] + [f['label'] for f in form_fields] + ['Status']
        data = [headers]

        # Table rows
        for i, r in enumerate(registrations):
            row = [str(i + 1)]
            for f in form_fields:
                row.append(r.get('responses', {}).get(f['label'], '-'))
            row.append(r.get('status', '-'))
            data.append(row)

        # Build table
        from reportlab.platypus import TableStyle
        from reportlab.lib.units import mm

        # Wrap long text in cells
        wrapped_data = []
        for row in data:
            wrapped_row = []
            for cell in row:
                wrapped_row.append(Paragraph(str(cell), styles['Normal']))
            wrapped_data.append(wrapped_row)

        # Calculate column widths based on A4
        page_width = A4[0] - 30*mm  # minus margins
        col_count = len(headers)
        col_widths = [page_width / col_count] * col_count

        table = Table(wrapped_data, colWidths=col_widths, repeatRows=1)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a56db')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('FONTSIZE', (0, 1), (-1, -1), 7),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
            ('PADDING', (0, 0), (-1, -1), 4),
            ('WORDWRAP', (0, 0), (-1, -1), True),
        ]))
        elements.append(table)

        doc.build(elements)
        buffer.seek(0)

        filename = f"{event['slug']}_registrations.pdf"
        return StreamingResponse(
            buffer,
            media_type='application/pdf',
            headers={'Content-Disposition': f'attachment; filename="{filename}"'}
        )
