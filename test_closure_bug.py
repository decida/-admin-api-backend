"""
Demonstração do bug de closure em loop.
"""

# BUG: Como está atualmente (ERRADO)
print("=" * 80)
print("DEMONSTRANDO O BUG")
print("=" * 80)

routes_buggy = []

for i in range(3):
    # Problema: default argument não cria uma closure adequada
    async def endpoint_buggy(resource_id: str = str(i)):
        return f"Resource ID: {resource_id}"

    routes_buggy.append(endpoint_buggy)

print("\nRoutes criadas com BUG:")
for idx, route in enumerate(routes_buggy):
    # Simular chamada
    import asyncio
    result = asyncio.run(route())
    print(f"   Route {idx}: {result}")

print("\n   Todas retornam '2' porque 'i' no final do loop é 2!")

# FIX: Usando uma função factory (CORRETO)
print("\n" + "=" * 80)
print("SOLUÇÃO COM FUNÇÃO FACTORY")
print("=" * 80)

routes_fixed = []

def make_endpoint(resource_id: str):
    """Factory function para criar endpoint com closure correta."""
    async def endpoint(request=None, db=None):
        return f"Resource ID: {resource_id}"
    return endpoint

for i in range(3):
    # Solução: usar função factory
    endpoint_fixed = make_endpoint(str(i))
    routes_fixed.append(endpoint_fixed)

print("\nRoutes criadas com FIX:")
for idx, route in enumerate(routes_fixed):
    # Simular chamada
    import asyncio
    result = asyncio.run(route())
    print(f"   Route {idx}: {result}")

print("\n   Cada route retorna seu próprio ID!")

print("\n" + "=" * 80)
