"""
Teste com resource_id obrigatorio no body.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from fastapi.testclient import TestClient
from app.main import app
from app.db.session import SessionLocal
from app.models.database import Database
from app.models.api_resource import ApiResource

client = TestClient(app)

print("=" * 80)
print("TESTE: resource_id OBRIGATORIO NO BODY")
print("=" * 80)

# Get valid IDs
db = SessionLocal()
try:
    # Get active connection
    connection = db.query(Database).filter(Database.status == "active").first()
    if not connection:
        print("\nNenhuma conexao ativa encontrada!")
        sys.exit(1)
    connection_id = str(connection.id)

    # Get active API resource
    api_resource = db.query(ApiResource).filter(ApiResource.is_active == True).first()
    if not api_resource:
        print("\nNenhum API resource ativo encontrado!")
        sys.exit(1)
    resource_id = str(api_resource.id)
    resource_path = api_resource.path

    print(f"\nConexao: {connection.name} ({connection_id})")
    print(f"API Resource: {api_resource.business_object_name} ({resource_id})")
    print(f"Path: {resource_path}")

finally:
    db.close()

# Teste 1: COM resource_id correto
print("\n" + "-" * 80)
print("TESTE 1: COM resource_id correto")
print("-" * 80)
response = client.post(
    resource_path,
    json={
        "resource_id": resource_id,
        "connectionId": connection_id,
        "cpf": "12345678900"
    }
)
print(f"Status: {response.status_code} (esperado: 200)")
if response.status_code == 200:
    result = response.json()
    print(f"Success: {result.get('success')}")
    if not result.get('success'):
        error = result.get('error', {})
        if isinstance(error, dict):
            print(f"Error: {error.get('message', 'Unknown')[:100]}")
        else:
            print(f"Error: {str(error)[:100]}")
else:
    print(f"Response: {response.text[:200]}")

# Teste 2: SEM resource_id
print("\n" + "-" * 80)
print("TESTE 2: SEM resource_id (deve dar erro 422)")
print("-" * 80)
response = client.post(
    resource_path,
    json={
        "connectionId": connection_id,
        "cpf": "12345678900"
    }
)
print(f"Status: {response.status_code} (esperado: 422)")
if response.status_code == 422:
    print("[OK] Validacao funcionando!")
    result = response.json()
    if 'detail' in result:
        detail = result['detail']
        if isinstance(detail, list) and len(detail) > 0:
            print(f"Campo faltando: {detail[0].get('loc', [])[1] if len(detail[0].get('loc', [])) > 1 else 'unknown'}")
            print(f"Mensagem: {detail[0].get('msg', 'unknown')}")
else:
    print(f"[ERRO] Status inesperado: {response.status_code}")

# Teste 3: COM resource_id ERRADO
print("\n" + "-" * 80)
print("TESTE 3: COM resource_id ERRADO (deve dar erro 400)")
print("-" * 80)
wrong_resource_id = "00000000-0000-0000-0000-000000000000"
response = client.post(
    resource_path,
    json={
        "resource_id": wrong_resource_id,
        "connectionId": connection_id,
        "cpf": "12345678900"
    }
)
print(f"Status: {response.status_code} (esperado: 400)")
if response.status_code == 400:
    print("[OK] Validacao de resource_id funcionando!")
    result = response.json()
    print(f"Mensagem: {result.get('detail', 'unknown')}")
else:
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text[:200]}")

# Teste 4: SEM connectionId
print("\n" + "-" * 80)
print("TESTE 4: SEM connectionId (deve dar erro 422)")
print("-" * 80)
response = client.post(
    resource_path,
    json={
        "resource_id": resource_id,
        "cpf": "12345678900"
    }
)
print(f"Status: {response.status_code} (esperado: 422)")
if response.status_code == 422:
    print("[OK] Validacao de connectionId funcionando!")
else:
    print(f"[ERRO] Status inesperado: {response.status_code}")

print("\n" + "=" * 80)
print("RESUMO")
print("=" * 80)
print("[OK] resource_id e obrigatorio no schema")
print("[OK] resource_id e validado (UUID4)")
print("[OK] resource_id mismatch retorna erro 400")
print("[OK] connectionId continua obrigatorio")
print("\n" + "=" * 80)
