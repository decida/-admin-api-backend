# Sistema de Cache - Admin API Backend

## Visão Geral

O sistema de cache utiliza **Redis** para armazenar em memória os resultados das consultas de banco de dados, reduzindo a carga no PostgreSQL e melhorando significativamente a performance da API.

## Configuração

### Variáveis de Ambiente

```bash
REDIS_HOST=localhost      # Host do Redis
REDIS_PORT=6379          # Porta do Redis
REDIS_DB=0               # Database do Redis (0-15)
REDIS_PASSWORD=          # Senha (opcional)
CACHE_TTL=300            # Time-to-live em segundos (padrão: 5 minutos)
```

### Docker

O Redis está configurado no `docker-compose.yml`:

```bash
# Iniciar Redis com Docker
docker-compose up -d redis

# Verificar status
docker exec admin-api-redis redis-cli ping
# Deve retornar: PONG
```

## Como Funciona

### Endpoints com Cache

1. **GET /databases/** - Lista de conexões
   - Cache key: `databases:list:{skip}:{limit}`
   - TTL: 5 minutos (configurável)
   - Header: `X-Cache-Status: HIT` ou `MISS`

2. **GET /databases/{id_or_slug}** - Conexão específica
   - Cache key: `databases:item:{id_or_slug}`
   - TTL: 5 minutos (configurável)
   - Header: `X-Cache-Status: HIT` ou `MISS`

### Header X-Cache-Status

Todos os endpoints GET retornam um header customizado indicando se a resposta veio do cache:

- **`X-Cache-Status: HIT`** ✅ - Resposta veio do cache Redis (rápido!)
- **`X-Cache-Status: MISS`** 📊 - Resposta veio do banco de dados PostgreSQL

### Logs

O sistema de cache usa logging do Python com os seguintes níveis:

- **INFO**: Conexão Redis, invalidações de cache
- **DEBUG**: Cache HIT/MISS/SET individual
- **WARNING**: Erros não-críticos (cache continua funcionando)
- **ERROR**: Erros críticos de conexão

Para ver logs de debug (HIT/MISS detalhado), configure:
```python
# Em app/main.py
logging.basicConfig(level=logging.DEBUG)
```

### Invalidação de Cache

O cache é **automaticamente invalidado** quando há mudanças nos dados:

- **POST /databases/** (criar) → Invalida todo cache de databases
- **PATCH /databases/{id_or_slug}** (atualizar) → Invalida todo cache de databases
- **DELETE /databases/{id_or_slug}** (deletar) → Invalida todo cache de databases

### Fluxo de Funcionamento

```
1. Request chega no endpoint
2. API verifica se existe no cache (Redis)
   ├─ Se existe → Retorna do cache (rápido!)
   └─ Se não existe:
      ├─ Consulta o PostgreSQL
      ├─ Armazena no cache com TTL
      └─ Retorna o resultado
```

## Benefícios

✅ **Performance**: Reduz tempo de resposta de consultas frequentes
✅ **Escalabilidade**: Diminui carga no banco de dados
✅ **Consistência**: Invalidação automática garante dados atualizados
✅ **Tolerância a falhas**: Se Redis falhar, API continua funcionando (consulta direto no DB)

## Testando o Cache

### Verificar header X-Cache-Status

```bash
# Primeira requisição (MISS - consulta o banco)
curl -I http://localhost:8000/api/v1/databases/
# Response headers:
# X-Cache-Status: MISS

# Segunda requisição (HIT - usa o cache)
curl -I http://localhost:8000/api/v1/databases/
# Response headers:
# X-Cache-Status: HIT

# Com curl verbose
curl -v http://localhost:8000/api/v1/databases/my-database-slug
# Procure por: < X-Cache-Status: HIT ou MISS
```

### Testar invalidação

```bash
# 1. GET - primeira vez (MISS)
curl -I http://localhost:8000/api/v1/databases/

# 2. GET - segunda vez (HIT)
curl -I http://localhost:8000/api/v1/databases/

# 3. Criar/atualizar/deletar algo
curl -X POST http://localhost:8000/api/v1/databases/ -d '{...}'

# 4. GET - novamente (MISS - cache foi invalidado)
curl -I http://localhost:8000/api/v1/databases/
```

## Monitoramento

### Verificar cache no Redis

```bash
# Listar todas as keys de databases
docker exec admin-api-redis redis-cli KEYS "databases:*"

# Ver conteúdo de uma key específica
docker exec admin-api-redis redis-cli GET "databases:item:my-database-slug"

# Ver TTL de uma key
docker exec admin-api-redis redis-cli TTL "databases:item:my-database-slug"

# Limpar todo o cache manualmente
docker exec admin-api-redis redis-cli FLUSHDB
```

### Estatísticas do Redis

```bash
# Ver estatísticas gerais
docker exec admin-api-redis redis-cli INFO stats

# Monitorar comandos em tempo real
docker exec admin-api-redis redis-cli MONITOR
```

## Ajuste de Performance

### Aumentar TTL (cache mais longo)

```bash
# Em .env
CACHE_TTL=600  # 10 minutos
```

### Desabilitar cache (desenvolvimento)

```bash
# Parar o Redis
docker-compose stop redis

# A API continuará funcionando, mas sem cache
```

## Implementação Técnica

### Arquivos Principais

- **`app/core/cache.py`** - Cliente Redis e funções de cache
- **`app/core/config.py`** - Configurações Redis
- **`app/api/v1/endpoints/databases.py`** - Implementação do cache nos endpoints

### Funções Disponíveis

```python
from app.core.cache import (
    get_cache,                    # Buscar do cache
    set_cache,                    # Salvar no cache
    delete_cache,                 # Deletar key específica
    delete_pattern,               # Deletar por padrão
    invalidate_database_cache,    # Invalida todo cache de databases
)
```

## Troubleshooting

### Redis não conecta

```bash
# Verificar se Redis está rodando
docker ps | grep redis

# Ver logs do Redis
docker logs admin-api-redis

# Reiniciar Redis
docker-compose restart redis
```

### Cache não invalida

```bash
# Limpar cache manualmente
docker exec admin-api-redis redis-cli FLUSHDB

# Verificar implementação nos endpoints
# Todos endpoints de mutação (POST/PATCH/DELETE) devem chamar:
await invalidate_database_cache()
```

### Performance ainda lenta

```bash
# Verificar latência do Redis
docker exec admin-api-redis redis-cli --latency

# Ajustar TTL para maior
CACHE_TTL=900  # 15 minutos

# Considerar aumentar recursos do Redis no docker-compose.yml
```
