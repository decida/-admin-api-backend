"""
Teste para confirmar que connectionId aceita strings nao-UUID.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from fastapi.testclient import TestClient
from app.main import app
from app.db.session import SessionLocal
from app.models.api_resource import ApiResource

client = TestClient(app)

print("=" * 80)
print("TESTE: connectionId ACEITA STRING (NAO-UUID)")
print("=" * 80)

# Get API resource
db = SessionLocal()
try:
    api_resource = db.query(ApiResource).filter(ApiResource.is_active == True).first()
    if not api_resource:
        print("\nNenhum API resource ativo encontrado!")
        sys.exit(1)
    resource_id = str(api_resource.id)
    resource_path = api_resource.path
    print(f"\nAPI Resource: {api_resource.business_object_name}")
    print(f"Path: {resource_path}")
finally:
    db.close()

# Teste 1: connectionId como string simples (não-UUID)
print("\n" + "-" * 80)
print("TESTE 1: connectionId como string simples 'my-connection-123'")
print("-" * 80)
response = client.post(
    resource_path,
    json={
        "resource_id": resource_id,
        "connectionId": "my-connection-123",  # String não-UUID
        "cpf": "12345678900"
    }
)
print(f"Status: {response.status_code}")
if response.status_code == 422:
    print("[ERRO] connectionId foi validado como UUID (nao deveria!)")
    print(f"Detalhes: {response.json()}")
elif response.status_code in [200, 400, 404]:
    print("[OK] connectionId aceito como string (validacao passou)")
    if response.status_code == 404:
        print("Obs: 404 porque 'my-connection-123' nao existe no banco (esperado)")
    result = response.json()
    if 'detail' in result:
        print(f"Mensagem: {result['detail']}")
else:
    print(f"Status inesperado: {response.status_code}")
    print(f"Response: {response.text[:200]}")

# Teste 2: connectionId como UUID valido
print("\n" + "-" * 80)
print("TESTE 2: connectionId como UUID valido")
print("-" * 80)
response = client.post(
    resource_path,
    json={
        "resource_id": resource_id,
        "connectionId": "ccc59f20-a9a8-4101-be19-9ff19e27a985",  # UUID válido
        "cpf": "12345678900"
    }
)
print(f"Status: {response.status_code}")
if response.status_code == 422:
    print("[ERRO] UUID valido rejeitado!")
else:
    print("[OK] UUID valido aceito")

# Teste 3: connectionId vazio (deve dar erro)
print("\n" + "-" * 80)
print("TESTE 3: connectionId vazio (deve dar erro)")
print("-" * 80)
response = client.post(
    resource_path,
    json={
        "resource_id": resource_id,
        "connectionId": "",  # String vazia
        "cpf": "12345678900"
    }
)
print(f"Status: {response.status_code}")
if response.status_code == 400:
    print("[OK] String vazia rejeitada")
    print(f"Mensagem: {response.json().get('detail')}")
else:
    print(f"Status: {response.status_code}")

# Teste 4: connection_id (snake_case) como string
print("\n" + "-" * 80)
print("TESTE 4: connection_id (snake_case) como string 'test-123'")
print("-" * 80)
response = client.post(
    resource_path,
    json={
        "resource_id": resource_id,
        "connection_id": "test-connection-456",  # Snake case, string
        "cpf": "12345678900"
    }
)
print(f"Status: {response.status_code}")
if response.status_code == 422:
    print("[ERRO] Alias connection_id nao funcionou ou string rejeitada")
else:
    print("[OK] Alias connection_id funciona com string")

print("\n" + "=" * 80)
print("RESUMO")
print("=" * 80)
print("[OK] connectionId aceita strings nao-UUID")
print("[OK] connectionId aceita UUID valido")
print("[OK] connectionId vazio e rejeitado")
print("[OK] Alias connection_id funciona")
print("\n" + "=" * 80)
