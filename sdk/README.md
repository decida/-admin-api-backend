# Admin API Backend SDK

SDK para facilitar a integração com Admin API Backend em aplicações Python.

## Estrutura

```
sdk/
└── python/
    ├── __init__.py       # Exports principais
    ├── client.py         # Cliente principal (Facade)
    ├── models.py         # Modelos de dados
    ├── exceptions.py     # Exceções customizadas
    └── examples.py       # Exemplos de uso
```

## Instalação

### Opção 1: Copiar diretamente para seu projeto

```bash
cp -r sdk/python seu_projeto/admin_api_sdk
```

### Opção 2: Usar como submódulo

```bash
# No seu projeto
git submodule add <repo_url> libs/admin-api-sdk
```

## Uso Básico

```python
from admin_api_sdk import AdminAPIClient

# Inicializar cliente
client = AdminAPIClient("http://localhost:8000")

# Verificar saúde da API
if client.health_check():
    print("API está funcionando")

# Listar recursos
resources = client.list_resources()

# Executar recurso
result = client.execute(
    path="/api/v1/consultar-paciente",
    connection_id="connection-uuid",
    parameters={"cpf": "12345678900"}
)

if result.success:
    print(f"Dados: {result.rows}")
```

## Funcionalidades

### Gerenciamento de Recursos

- `list_resources()` - Listar todos os recursos
- `get_resource_by_id(id)` - Buscar por ID
- `get_resource_by_path(path)` - Buscar por path
- `create_resource()` - Criar novo recurso
- `update_resource()` - Atualizar recurso
- `delete_resource()` - Deletar recurso
- `toggle_resource()` - Ativar/desativar recurso

### Execução de Recursos

- `execute(path, connection_id, parameters)` - Executar por path
- `execute_by_id(resource_id, connection_id, parameters)` - Executar por ID

### Métodos de Conveniência

- `health_check()` - Verificar saúde da API
- `get_active_resources()` - Recursos ativos
- `get_inactive_resources()` - Recursos inativos
- `search_resources(query)` - Buscar recursos

## Tratamento de Erros

```python
from admin_api_sdk import (
    AdminAPIClient,
    ConnectionError,
    ResourceNotFoundError,
    ExecutionError
)

client = AdminAPIClient("http://localhost:8000")

try:
    result = client.execute(...)
except ConnectionError:
    print("Falha na conexão com API")
except ResourceNotFoundError:
    print("Recurso não encontrado")
except ExecutionError as e:
    print(f"Erro na execução: {e.message}")
    if e.step:
        print(f"Falhou no step {e.step}")
```

## Integração em Outro Backend

### Exemplo com Flask

```python
from flask import Flask, request, jsonify
from admin_api_sdk import AdminAPIClient

app = Flask(__name__)
admin_api = AdminAPIClient("http://localhost:8000")

@app.route("/api/paciente/<cpf>")
def get_paciente(cpf):
    try:
        result = admin_api.execute(
            path="/api/v1/consultar-paciente",
            connection_id=request.headers.get("X-Connection-ID"),
            parameters={"cpf": cpf}
        )

        return jsonify({
            "success": result.success,
            "data": result.rows
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
```

### Exemplo com FastAPI

```python
from fastapi import FastAPI, HTTPException
from admin_api_sdk import AdminAPIClient, ExecutionError

app = FastAPI()
admin_api = AdminAPIClient("http://localhost:8000")

@app.post("/paciente/consultar")
async def consultar_paciente(cpf: str, connection_id: str):
    try:
        result = admin_api.execute(
            path="/api/v1/consultar-paciente",
            connection_id=connection_id,
            parameters={"cpf": cpf}
        )

        if not result.success:
            raise HTTPException(500, result.error)

        return {"data": result.rows}

    except ExecutionError as e:
        raise HTTPException(500, e.message)
```

### Exemplo com Django

```python
from django.http import JsonResponse
from admin_api_sdk import AdminAPIClient

admin_api = AdminAPIClient("http://localhost:8000")

def consultar_paciente(request):
    cpf = request.GET.get('cpf')
    connection_id = request.headers.get('X-Connection-ID')

    try:
        result = admin_api.execute(
            path="/api/v1/consultar-paciente",
            connection_id=connection_id,
            parameters={"cpf": cpf}
        )

        return JsonResponse({
            "success": result.success,
            "data": result.rows
        })
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
```

## Recursos Avançados

### Criar Recurso com Cadeia de Execução

```python
execution_chain = [
    {
        "businessObjectId": "uuid-1",
        "businessObjectName": "Query Cliente",
        "businessObjectType": "select",
        "businessObjectParams": [
            {"name": "id", "type": "number", "required": True}
        ],
        "order": 1,
        "parameterMappings": []
    },
    {
        "businessObjectId": "uuid-2",
        "businessObjectName": "Insert Log",
        "businessObjectType": "insert",
        "businessObjectParams": [
            {"name": "clienteId", "type": "number", "required": True}
        ],
        "order": 2,
        "parameterMappings": [
            {
                "parameterName": "clienteId",
                "sourceType": "variable",
                "staticValue": "",
                "variableSource": {
                    "stepIndex": 0,
                    "fieldName": "id"
                }
            }
        ]
    }
]

resource = client.create_resource(
    path="/api/v1/cliente-com-log",
    business_object_id="uuid-1",
    execution_chain=execution_chain
)
```

## Dependências

- Python 3.11+
- Sem dependências externas (usa apenas stdlib)

## Design Pattern

O SDK implementa o padrão **Facade**, fornecendo uma interface simples e unificada para interagir com a Admin API Backend. Isso esconde a complexidade das chamadas HTTP, parsing de responses, e tratamento de erros.

## Thread Safety

O cliente não mantém estado mutável, portanto é thread-safe. Você pode compartilhar uma única instância entre threads.

```python
# Seguro para uso em múltiplas threads
client = AdminAPIClient("http://localhost:8000")

# Use em diferentes threads/workers
result1 = client.execute(...)  # Thread 1
result2 = client.execute(...)  # Thread 2
```

## Performance

- Usa `urllib` da stdlib (sem dependências)
- Timeout configurável (padrão: 30s)
- Conexões não são mantidas abertas (stateless)

Para alto desempenho, considere:
- Connection pooling no lado da aplicação
- Cache de recursos frequentemente acessados
- Execução assíncrona (contribuições bem-vindas!)

## Exemplos Completos

Veja `examples.py` para exemplos completos de:
- Gerenciamento de recursos
- Execução de recursos
- Tratamento de erros
- Integração em backends (Flask, FastAPI, Django)
- Recursos com cadeias de execução
