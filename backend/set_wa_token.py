"""
Run this to set your WhatsApp access token for a tenant.
Usage: py set_wa_token.py
"""
import sys
sys.path.insert(0, '.')

from pymongo import MongoClient
from app.core.security import encrypt_secret

client = MongoClient("mongodb://localhost:27017")
db = client["eventpay"]

# Show tenants
tenants = list(db.tenants.find({"status": "active"}))
print("\nActive tenants:")
for i, t in enumerate(tenants):
    print(f"  {i+1}. {t['name']} (phone_number_id: {t.get('config',{}).get('whatsapp_phone_number_id', 'NOT SET')})")

choice = int(input("\nSelect tenant number: ")) - 1
tenant = tenants[choice]

token = input("Paste your WhatsApp access token from Meta Developer Portal: ").strip()
if not token:
    print("No token provided. Exiting.")
    sys.exit(1)

# Encrypt and store
encrypted_token = encrypt_secret(token)
db.tenants.update_one(
    {"_id": tenant["_id"]},
    {"$set": {"config.whatsapp_api_key": encrypted_token}}
)

print(f"\n✅ WhatsApp API key saved for tenant '{tenant['name']}'")
print("Now send a WhatsApp message - you should get a reply!")
