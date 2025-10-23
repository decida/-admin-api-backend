"""
Teste para verificar se as rotas dinâmicas estão realmente disponíveis.
"""

import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

print("=" * 80)
print("TESTING DYNAMIC ROUTES VIA HTTP")
print("=" * 80)

# Get all routes from the app
print("\n1. All registered routes in the app:")
print(f"   Total routes: {len(app.routes)}")

for route in app.routes:
    if hasattr(route, 'path') and hasattr(route, 'methods'):
        methods = ', '.join(route.methods) if route.methods else 'N/A'
        print(f"   {methods:20} {route.path}")

# Try to call the dynamic route
print("\n2. Testing the dynamic route:")
try:
    response = client.post(
        "/api/v1/paciente",
        json={
            "connection_id": "some-id",
            "cpf": "12345678900"
        }
    )
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.json()}")
except Exception as e:
    print(f"   ERROR: {e}")

print("\n" + "=" * 80)
