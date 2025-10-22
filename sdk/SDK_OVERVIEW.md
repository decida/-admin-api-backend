# 📦 Admin API SDK - Overview

## Visão Geral

SDK Python para facilitar a integração com Admin API Backend. Implementa o **padrão Facade** para simplificar o acesso aos recursos de API, abstraindo a complexidade das chamadas HTTP e parsing de responses.

---

## 🎯 Objetivo

Permitir que desenvolvedores integrem facilmente os recursos da Admin API em outros backends (Flask, FastAPI, Django, etc.) sem precisar lidar diretamente com requisições HTTP, parsing JSON, tratamento de erros, etc.

---

## 📁 Estrutura

```
sdk/
├── README.md              # Documentação principal
├── QUICKSTART.md          # Guia rápido de uso
├── SDK_OVERVIEW.md        # Este arquivo
└── python/
    ├── __init__.py        # Exports principais
    ├── client.py          # Cliente principal (Facade)
    ├── models.py          # Modelos de dados
    ├── exceptions.py      # Exceções customizadas
    ├── examples.py        # Exemplos de uso
    ├── test_client.py     # Testes
    └── setup.py           # Setup para instalação
```

---

## 🏗️ Arquitetura

### Design Pattern: **Facade**

O SDK implementa o padrão Facade fornecendo uma interface simplificada sobre a API REST complexa.

```
┌─────────────────────────────────────────────────┐
│          Seu Backend (Flask/FastAPI)            │
│                                                 │
│  ┌───────────────────────────────────────────┐ │
│  │        AdminAPIClient (Facade)            │ │
│  │                                           │ │
│  │  • list_resources()                       │ │
│  │  • execute()                              │ │
│  │  • create_resource()                      │ │
│  │  • ...                                    │ │
│  └───────────────┬───────────────────────────┘ │
│                  │                             │
└──────────────────┼─────────────────────────────┘
                   │ HTTP
                   ▼
       ┌───────────────────────┐
       │  Admin API Backend    │
       │  (FastAPI)            │
       └───────────────────────┘
```

### Componentes

#### 1. **Client (client.py)**

Classe principal `AdminAPIClient` que fornece todos os métodos de interação:

- **Gerenciamento de Recursos**: CRUD completo
- **Execução de Recursos**: Execução síncrona
- **Métodos de Conveniência**: Filtros, busca, health check
- **Tratamento de Erros**: Exceções tipadas

#### 2. **Models (models.py)**

Dataclasses Python para representar dados da API:

- `APIResource` - Definição de recurso
- `ExecutionResult` - Resultado de execução simples
- `ChainExecutionResult` - Resultado de cadeia
- `ExecutionChainStep` - Step da cadeia
- `ParameterMapping` - Mapeamento de parâmetros
- E outros...

#### 3. **Exceptions (exceptions.py)**

Hierarquia de exceções customizadas:

```
AdminAPIError (base)
├── ConnectionError
├── AuthenticationError
├── ResourceNotFoundError
├── ValidationError
└── ExecutionError
```

---

## 🎨 Benefícios do Design

### ✅ Simplicidade

**Sem SDK:**
```python
import urllib.request
import json

url = "http://localhost:8000/api/v1/api-resources"
headers = {"Content-Type": "application/json"}
req = urllib.request.Request(url, headers=headers)
response = urllib.request.urlopen(req)
data = json.loads(response.read())
# ... processar data ...
```

**Com SDK:**
```python
from admin_api_sdk import AdminAPIClient

client = AdminAPIClient("http://localhost:8000")
resources = client.list_resources()
```

### ✅ Type Safety

Todos os modelos são tipados com dataclasses:

```python
resource: APIResource = client.get_resource_by_id("uuid")
# IDE autocomplete funciona!
print(resource.path)
print(resource.is_active)
```

### ✅ Tratamento de Erros Robusto

```python
try:
    result = client.execute(...)
except ResourceNotFoundError:
    # Recurso não existe
except ExecutionError as e:
    # Erro na execução
    print(f"Falhou no step {e.step}")
except ConnectionError:
    # Backend offline
```

### ✅ Sem Dependências Externas

- Usa apenas Python stdlib
- `urllib` para HTTP
- `json` para parsing
- `dataclasses` para modelos

---

## 🚀 Casos de Uso

### Caso 1: Backend Intermediário

Seu backend serve como intermediário entre frontend e Admin API:

```
Frontend (React/Vue)
    ↓ HTTP
Seu Backend (Flask)
    ↓ SDK
Admin API Backend
    ↓ SQL
Database
```

**Vantagem**: Adicione lógica de negócio, validações, autenticação antes de executar recursos.

### Caso 2: Microserviços

Múltiplos microserviços usam Admin API como fonte de dados:

```
Microservice 1 (Pedidos)  ─┐
Microservice 2 (Clientes) ─┤ SDK → Admin API Backend
Microservice 3 (Estoque)  ─┘
```

**Vantagem**: Centralize lógica de acesso a dados sem duplicação.

### Caso 3: Scripts de Automação

Scripts Python para tarefas administrativas:

```python
# backup_script.py
client = AdminAPIClient("http://localhost:8000")

# Desativar todos os recursos
for resource in client.get_active_resources():
    client.toggle_resource(resource.id)
    print(f"Desativado: {resource.path}")
```

### Caso 4: Dashboard Customizado

Crie dashboards administrativos:

```python
# dashboard.py
client = AdminAPIClient("http://localhost:8000")

# Estatísticas
total = len(client.list_resources())
active = len(client.get_active_resources())
inactive = len(client.get_inactive_resources())

print(f"Total: {total} | Ativos: {active} | Inativos: {inactive}")
```

---

## 🔌 Integração

### Flask

```python
from flask import Flask
from admin_api_sdk import AdminAPIClient

app = Flask(__name__)
admin_api = AdminAPIClient("http://localhost:8000")

@app.route("/resources")
def list_resources():
    resources = admin_api.list_resources()
    return {"resources": [r.__dict__ for r in resources]}
```

### FastAPI

```python
from fastapi import FastAPI
from admin_api_sdk import AdminAPIClient

app = FastAPI()
admin_api = AdminAPIClient("http://localhost:8000")

@app.get("/resources")
async def list_resources():
    resources = admin_api.list_resources()
    return {"resources": resources}
```

### Django

```python
from django.http import JsonResponse
from admin_api_sdk import AdminAPIClient

admin_api = AdminAPIClient("http://localhost:8000")

def list_resources(request):
    resources = admin_api.list_resources()
    return JsonResponse({"resources": [r.__dict__ for r in resources]})
```

---

## 📊 Performance

### Características

- **Stateless**: Não mantém conexões abertas
- **Thread-safe**: Sem estado mutável compartilhado
- **Timeout configurável**: Evita travamentos

### Otimizações Possíveis

1. **Connection Pooling**: Implementar pool de conexões HTTP
2. **Cache**: Cachear recursos frequentemente acessados
3. **Async**: Versão assíncrona com `aiohttp`
4. **Retry Logic**: Retry automático em falhas temporárias

---

## 🧪 Testes

Execute os testes:

```bash
# Com pytest
pytest sdk/python/test_client.py

# Sem pytest
python sdk/python/test_client.py
```

Testes incluem:
- Inicialização do client
- Parsing de modelos
- Health check (requer backend rodando)
- Operações CRUD (requer backend rodando)

---

## 📚 Documentação

- **README.md**: Documentação completa
- **QUICKSTART.md**: Guia rápido com exemplos práticos
- **examples.py**: Exemplos de código funcionais
- **SDK_OVERVIEW.md**: Este documento (visão arquitetural)

---

## 🔮 Roadmap Futuro

### Versão 1.1
- [ ] Cliente assíncrono (`AsyncAdminAPIClient`)
- [ ] Connection pooling
- [ ] Retry automático
- [ ] Rate limiting

### Versão 1.2
- [ ] Cache inteligente de recursos
- [ ] Batch operations
- [ ] Streaming de resultados grandes

### Versão 2.0
- [ ] SDK em outras linguagens (JavaScript, Go, Java)
- [ ] WebSocket para execuções em tempo real
- [ ] Métricas e observabilidade integradas

---

## 🤝 Contribuindo

### Estrutura de Código

- **PEP 8**: Código segue PEP 8
- **Type Hints**: Todas as funções são tipadas
- **Docstrings**: Todas as classes/métodos documentados
- **No Dependencies**: Mantém zero dependências externas

### Adicionando Features

1. Adicione método em `client.py`
2. Adicione testes em `test_client.py`
3. Adicione exemplo em `examples.py`
4. Atualize documentação

---

## 📄 Licença

MIT License - Use livremente em projetos comerciais e open source.

---

## 🎉 Conclusão

O Admin API SDK fornece uma interface **simples**, **tipo-safe** e **sem dependências** para integrar recursos API em qualquer backend Python. O padrão Facade esconde a complexidade e torna a integração trivial.

**Comece agora**: `QUICKSTART.md`
