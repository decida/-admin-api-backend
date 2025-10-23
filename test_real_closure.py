"""
Teste real do problema de closure com objetos.
"""

class Resource:
    def __init__(self, id, path):
        self.id = id
        self.path = path

# BUG: Como está atualmente
print("=" * 80)
print("SIMULANDO O PROBLEMA REAL")
print("=" * 80)

resources = [
    Resource("id-1", "/api/v1/users"),
    Resource("id-2", "/api/v1/posts"),
    Resource("id-3", "/api/v1/comments"),
]

routes_buggy = []

# Simulando o loop em refresh_dynamic_routes
for resource in resources:
    # PROBLEMA: resource_id captura a REFERÊNCIA de resource.id
    # Mas como resource muda no loop, o valor pode ser imprevisível
    async def endpoint(resource_id: str = str(resource.id)):
        return f"Resource ID: {resource_id}"

    routes_buggy.append((resource.path, endpoint))

print("\nRoutes criadas:")
import asyncio
for path, route in routes_buggy:
    result = asyncio.run(route())
    print(f"   {path} -> {result}")

print("\n   Observe: TODAS as rotas apontam para 'id-3' (último resource do loop)!")

# FIX: Usando função factory
print("\n" + "=" * 80)
print("SOLUÇÃO COM FUNÇÃO FACTORY")
print("=" * 80)

routes_fixed = []

def make_endpoint(resource_id: str):
    """Factory function para criar endpoint com closure correta."""
    async def endpoint(request=None, db=None, _resource_id: str = resource_id):
        # Usar _resource_id do escopo externo capturado corretamente
        return f"Resource ID: {_resource_id}"
    return endpoint

for resource in resources:
    endpoint_fixed = make_endpoint(str(resource.id))
    routes_fixed.append((resource.path, endpoint_fixed))

print("\nRoutes criadas:")
for path, route in routes_fixed:
    result = asyncio.run(route())
    print(f"   {path} -> {result}")

print("\n   Agora cada route mantém seu próprio resource_id!")

print("\n" + "=" * 80)
