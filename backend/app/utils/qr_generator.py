import qrcode
import io
import base64
from urllib.parse import quote


def generate_whatsapp_qr(phone: str, message: str, event_id: str) -> str:
    """Generate a QR code that opens WhatsApp with a pre-filled message."""
    wa_url = f"https://wa.me/{phone}?text={quote(message)}"
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(wa_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    b64 = base64.b64encode(buffer.getvalue()).decode()
    return f"data:image/png;base64,{b64}"
