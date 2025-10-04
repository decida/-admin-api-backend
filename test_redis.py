#!/usr/bin/env python
"""
Script para testar conexão Redis
"""
import asyncio
import sys
from app.core.config import settings
from app.core.cache import get_redis, set_cache, get_cache

async def test_redis():
    print("=== Teste de Conexão Redis ===\n")

    print(f"Configurações:")
    print(f"  REDIS_HOST: {settings.REDIS_HOST}")
    print(f"  REDIS_PORT: {settings.REDIS_PORT}")
    print(f"  REDIS_DB: {settings.REDIS_DB}")
    print(f"  REDIS_PASSWORD: {'***' if settings.REDIS_PASSWORD else '(none)'}")
    print(f"  CACHE_TTL: {settings.CACHE_TTL}s\n")

    try:
        # Test connection
        print("1. Testando conexão...")
        client = await get_redis()
        pong = await client.ping()
        print(f"   ✓ Redis PING: {pong}\n")

        # Test set
        print("2. Testando SET...")
        test_key = "test:connection"
        test_value = {"message": "Hello from test", "timestamp": "2024-01-01"}
        success = await set_cache(test_key, test_value, ttl=60)
        print(f"   ✓ SET success: {success}\n")

        # Test get
        print("3. Testando GET...")
        retrieved = await get_cache(test_key)
        print(f"   ✓ GET result: {retrieved}\n")

        # Verify
        if retrieved == test_value:
            print("✅ Redis está funcionando corretamente!")

            # Show keys
            print("\n4. Keys no Redis:")
            keys = await client.keys("*")
            for key in keys[:10]:  # Mostrar primeiras 10 keys
                print(f"   - {key}")
            if len(keys) > 10:
                print(f"   ... e mais {len(keys) - 10} keys")

            return True
        else:
            print("❌ Erro: Valor recuperado não corresponde ao valor salvo")
            return False

    except Exception as e:
        print(f"❌ Erro ao conectar no Redis: {e}")
        print(f"\nPossíveis soluções:")
        print(f"1. Verifique se o Redis está rodando:")
        print(f"   - Windows: Verifique serviço Redis")
        print(f"   - Docker: docker ps | grep redis")
        print(f"2. Verifique as credenciais no arquivo .env")
        print(f"3. Teste conexão manual: redis-cli -h {settings.REDIS_HOST} -p {settings.REDIS_PORT}")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_redis())
    sys.exit(0 if result else 1)
