"""
Teste para verificar como o FastAPI está lendo o body da requisição.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from fastapi.testclient import TestClient
from app.main import app
from app.db.session import SessionLocal
from app.models.database import Database

client = TestClient(app)

print("=" * 80)
print("TESTING REQUEST BODY HANDLING")
print("=" * 80)

# Get a valid connection_id from database
db = SessionLocal()
try:
    connection = db.query(Database).filter(Database.status == "active").first()
    if connection:
        connection_id = str(connection.id)
        print(f"\nFound active connection: {connection.name} (id: {connection_id})")
    else:
        print("\nNo active connections found, using dummy ID")
        connection_id = "00000000-0000-0000-0000-000000000000"
finally:
    db.close()

# Test with connection_id
print("\n1. Testing with connection_id in body...")
response = client.post(
    "/api/v1/paciente",
    json={
        "connection_id": connection_id,
        "cpf": "12345678900"
    }
)
print(f"   Status: {response.status_code}")
if response.status_code == 200:
    result = response.json()
    print(f"   Success: {result.get('success')}")
    if not result.get('success'):
        print(f"   Error: {result.get('error', {}).get('message', 'Unknown')[:100]}")
elif response.status_code == 400:
    print(f"   Error 400: {response.json()}")
else:
    print(f"   Response: {response.text[:200]}")

# Test with connectionId (camelCase)
print("\n2. Testing with connectionId (camelCase) in body...")
response = client.post(
    "/api/v1/paciente",
    json={
        "connectionId": connection_id,
        "cpf": "12345678900"
    }
)
print(f"   Status: {response.status_code}")
if response.status_code == 200:
    result = response.json()
    print(f"   Success: {result.get('success')}")
    if not result.get('success'):
        print(f"   Error: {result.get('error', {}).get('message', 'Unknown')[:100]}")
elif response.status_code == 400:
    print(f"   Error 400: {response.json()}")
else:
    print(f"   Response: {response.text[:200]}")

# Test without connection_id
print("\n3. Testing WITHOUT connection_id in body...")
response = client.post(
    "/api/v1/paciente",
    json={
        "cpf": "12345678900"
    }
)
print(f"   Status: {response.status_code}")
print(f"   Response: {response.json()}")

print("\n" + "=" * 80)
