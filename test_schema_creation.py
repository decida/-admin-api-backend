"""
Teste para debugar a criação do schema Pydantic dinâmico.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.dynamic_routes import create_request_schema

# Testar criação de schema
params = [
    {"name": "cpf", "type": "string", "required": False, "defaultValue": None}
]

print("Creating schema with params:", params)

try:
    Schema = create_request_schema(params)
    print(f"✓ Schema created successfully: {Schema}")
    print(f"  Schema fields: {Schema.model_fields}")

    # Testar criação de instância
    instance = Schema(connectionId="test-uuid", cpf="12345678900")
    print(f"✓ Instance created: {instance}")
    print(f"  Instance dict: {instance.model_dump()}")

except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
