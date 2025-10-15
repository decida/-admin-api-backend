# Setup API Resources

## Passo 1: Criar a Tabela no Banco de Dados

Execute o script SQL para criar a tabela `api_resources`:

### Opção A: Com Docker (Recomendado)

```bash
docker exec -i admin-api-db psql -U admin -d admindb < sql/006_create_api_resources_table.sql
```

### Opção B: Sem Docker

```bash
psql -h localhost -U admin -d admindb -f sql/006_create_api_resources_table.sql
```

### Verificar se a Tabela Foi Criada

```sql
-- Conecte ao banco e execute:
\dt api_resources

-- Ou:
SELECT table_name FROM information_schema.tables WHERE table_name = 'api_resources';
```

## Passo 2: Reiniciar a Aplicação

### Com Docker

```bash
docker-compose restart app
```

### Sem Docker

1. Pare o servidor (Ctrl+C)
2. Reinicie:

```bash
poetry run uvicorn app.main:app --reload
```

## Passo 3: Verificar Logs

Ao iniciar, você deve ver no log:

```
INFO - Starting application...
INFO - Refreshing dynamic routes: found 0 active resources
INFO - Dynamic routes initialized successfully
```

## Passo 4: Testar os Endpoints

### Listar API Resources (deve retornar array vazio inicialmente)

```bash
curl -X GET http://localhost:8000/api/v1/api-resources
```

### Acessar Swagger

```
http://localhost:8000/api/v1/docs
```

Procure pela tag "api-resources" - você deve ver todos os endpoints CRUD.

## Passo 5: Criar seu Primeiro API Resource

1. **Primeiro, certifique-se de ter um Business Object criado:**

```bash
curl -X GET http://localhost:8000/api/v1/business-objects
```

2. **Crie um API Resource:**

```bash
curl -X POST http://localhost:8000/api/v1/api-resources \
  -H "Content-Type: application/json" \
  -d '{
    "path": "/api/v1/teste",
    "description": "Endpoint de teste",
    "isActive": true,
    "businessObjectId": "UUID_DO_SEU_BUSINESS_OBJECT"
  }'
```

3. **Verifique se o endpoint dinâmico foi criado:**

Vá para o Swagger e procure pela tag "Dynamic API Resources". Você deve ver seu novo endpoint lá!

4. **Teste o endpoint dinâmico:**

```bash
curl -X POST http://localhost:8000/api/v1/teste \
  -H "Content-Type: application/json" \
  -d '{
    "connectionId": "UUID_DA_SUA_CONEXAO",
    "param1": "valor1"
  }'
```

## Troubleshooting

### Erro: relation "api_resources" does not exist

Você precisa executar o script SQL do Passo 1.

### Erro: Dynamic routes not initialized

Verifique os logs da aplicação. Pode haver um problema de conexão com o banco.

### Endpoint dinâmico não aparece no Swagger

- Certifique-se de que `isActive = true`
- Reinicie a aplicação
- Verifique os logs para erros

### Erro: foreign key constraint "fk_api_resources_business_object"

O Business Object que você está tentando associar não existe. Verifique o UUID.

## Comandos Úteis

### Ver todas as rotas registradas (incluindo dinâmicas)

No código Python:

```python
from app.core.dynamic_routes import get_registered_routes
print(get_registered_routes())
```

### Forçar refresh das rotas dinâmicas

```python
from app.core.dynamic_routes import refresh_dynamic_routes
from app.db.session import SessionLocal

db = SessionLocal()
try:
    refresh_dynamic_routes(db)
finally:
    db.close()
```

### Ver logs em tempo real (Docker)

```bash
docker-compose logs -f app
```

## Próximos Passos

Consulte o arquivo `API_RESOURCES_README.md` para documentação completa sobre:

- Como usar os endpoints
- Exemplos práticos
- Tipos de parâmetros
- Segurança
- Troubleshooting detalhado
