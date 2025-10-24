# 🚀 Simple Dynamic Routes - Guia de Uso

Sistema **minimalista** de rotas dinâmicas para FastAPI. Basta copiar 2 arquivos e adicionar 3 linhas no `main.py`!

## 📦 O Que É?

Cria endpoints FastAPI automaticamente baseados nos API Resources configurados na Admin API.

- ✅ **Simples**: 2 arquivos, 3 linhas de código
- ✅ **Zero configuração**: Não precisa criar resources extras
- ✅ **Plug & Play**: Copiar e usar

## 🔧 Instalação (2 minutos)

### 1. Copiar Arquivos

Copie estes 2 arquivos para o seu projeto:

```bash
# No projeto de destino, criar pasta sdk/
mkdir -p seu-projeto/sdk

# Copiar arquivos
cp admin_api_lite.py seu-projeto/sdk/
cp simple_dynamic_routes.py seu-projeto/sdk/
```

### 2. Integrar no main.py

Adicione no seu `main.py`:

```python
# ========== IMPORTS ==========
import sys
sys.path.append("./sdk")  # Ajuste o path se necessário

from admin_api_lite import AdminAPILite
from simple_dynamic_routes import setup_dynamic_routes, dynamic_router


# ========== LIFESPAN ==========
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup - configurar rotas dinâmicas
    admin_client = AdminAPILite(base_url="http://localhost:8000")  # URL da Admin API
    setup_dynamic_routes(admin_client)

    yield

    # Shutdown
    pass


# ========== APP ==========
app = FastAPI(
    title="My App",
    lifespan=lifespan  # ← Adicionar lifespan
)

# Incluir router de rotas dinâmicas
app.include_router(dynamic_router)  # ← Adicionar esta linha

# Seus outros routers...
```

### 3. Pronto!

```bash
uvicorn app.main:app --reload
```

Acesse `/docs` e veja as rotas dinâmicas criadas automaticamente!

## 📝 Como Funciona

### No Startup

1. `setup_dynamic_routes()` chama `admin_client.list_api_resources()`
2. Para cada resource ativo, cria uma rota no FastAPI
3. Rotas ficam disponíveis automaticamente

### Quando Request Chega

1. Extrai `connectionId` e parâmetros do body
2. Busca metadata do resource via Admin API
3. Busca database connection via Admin API
4. Decodifica SQL do business object
5. Substitui parâmetros (`:param` format)
6. Executa SQL no banco de dados alvo
7. Retorna resultado

## 🔄 Atualizar Rotas

Se criar novos API Resources na Admin API:

### Opção 1: Reiniciar app

```bash
# Ctrl+C e rodar novamente
uvicorn app.main:app --reload
```

### Opção 2: Endpoint de refresh (recomendado)

Adicione no `main.py`:

```python
from simple_dynamic_routes import refresh_routes

@app.post("/admin/refresh-routes")
async def refresh():
    refresh_routes()
    return {"status": "Routes refreshed"}
```

Depois, quando criar novos resources:

```bash
curl -X POST http://localhost:8000/admin/refresh-routes
```

## 🧪 Testar

### 1. Criar API Resource na Admin API

Via UI ou SQL:

```sql
-- Criar Business Object
INSERT INTO business_objects (id, name, sql_command, command_type, params)
VALUES (
    gen_random_uuid(),
    'test-query',
    encode('SELECT NOW() as time, ''Hello!'' as message;', 'base64'),
    'select',
    '[]'::jsonb
) RETURNING id;

-- Criar API Resource (substitua <BO_ID>)
INSERT INTO api_resources (
    id, path, method, business_object_id,
    business_object_name, business_object_params, is_active
)
VALUES (
    gen_random_uuid(),
    '/api/v1/test',
    'POST',
    '<BO_ID>',
    'test-query',
    '[]'::jsonb,
    true
);
```

### 2. Refresh Rotas

```bash
# Se adicionou endpoint de refresh
curl -X POST http://localhost:8000/admin/refresh-routes

# Ou reinicie o app
```

### 3. Testar Endpoint

```bash
curl -X POST http://localhost:8000/api/v1/test \
  -H "Content-Type: application/json" \
  -d '{
    "connectionId": "SEU_CONNECTION_ID"
  }'
```

**Resposta:**
```json
{
  "success": true,
  "rows": [
    {
      "time": "2025-01-...",
      "message": "Hello!"
    }
  ],
  "rowCount": 1
}
```

## ⚙️ Configuração Avançada

### Headers de Autenticação

Se a Admin API requer autenticação:

```python
admin_client = AdminAPILite(
    base_url="http://localhost:8000",
    headers={"Authorization": "Bearer YOUR_TOKEN"}
)
```

### Variáveis de Ambiente

```python
import os

ADMIN_API_URL = os.getenv("ADMIN_API_URL", "http://localhost:8000")

admin_client = AdminAPILite(base_url=ADMIN_API_URL)
```

### Logging

```python
import logging

logging.basicConfig(level=logging.INFO)
```

Você verá logs como:
```
INFO - Fetching API resources from Admin API...
INFO - Found 5 active API resources
INFO - ✓ Registered: POST /api/v1/consultar-paciente
INFO - ✓ Registered: POST /api/v1/atualizar-status
INFO - Dynamic routes setup complete: 5 routes registered
```

## 🐛 Troubleshooting

### Erro: "Admin client not configured"

**Causa**: `setup_dynamic_routes()` não foi chamado.

**Solução**: Verifique que o `lifespan` está configurado corretamente.

### Erro: "connectionId is required"

**Causa**: Request não tem `connectionId` no body.

**Solução**: Todos os requests devem incluir `connectionId`:

```json
{
  "connectionId": "uuid-da-conexao",
  "param1": "value1"
}
```

### Rotas não aparecem no /docs

**Causa**: `dynamic_router` não foi incluído no app.

**Solução**: Adicione `app.include_router(dynamic_router)`

### Admin API não acessível

**Causa**: URL incorreta ou Admin API offline.

**Solução**:

```bash
# Testar conectividade
curl http://localhost:8000/health
```

## 📊 Limitações

Esta versão simplificada:

- ❌ **Não suporta execution chains** (apenas single business object)
- ❌ **Não suporta parameter mapping complexo**
- ⚠️ **Busca metadados em cada request** (pode ter overhead)

Se precisar dessas features, use a versão completa em `dynamic_routes_portable/`.

## 📁 Estrutura de Arquivos

```
seu-projeto/
├── sdk/
│   ├── admin_api_lite.py          ← Cliente HTTP para Admin API
│   └── simple_dynamic_routes.py   ← Sistema de rotas dinâmicas
└── app/
    └── main.py                     ← Seu FastAPI app (modificar aqui)
```

## ✨ Pronto!

Agora você pode criar endpoints apenas configurando na Admin API, sem escrever código! 🎉

### Para adicionar novo endpoint:

1. Criar Business Object na Admin API (SQL)
2. Criar API Resource apontando para o BO
3. Refresh rotas (`POST /admin/refresh-routes` ou restart)
4. Usar o endpoint automaticamente criado!

---

**Dúvidas?** Verifique os logs da aplicação com `logging.INFO`
