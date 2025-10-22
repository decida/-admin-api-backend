# 🚀 Quickstart - Admin API SDK

## Instalação Rápida

### 1. Copiar SDK para seu projeto

```bash
# Copie a pasta sdk/python para seu projeto
cp -r sdk/python seu_projeto/admin_api_sdk
```

### 2. Usar no seu código

```python
from admin_api_sdk import AdminAPIClient

client = AdminAPIClient("http://localhost:8000")
```

---

## Exemplos Práticos

### 1️⃣ Listar Recursos Disponíveis

```python
from admin_api_sdk import AdminAPIClient

client = AdminAPIClient("http://localhost:8000")

# Listar todos os recursos
resources = client.list_resources()

for resource in resources:
    print(f"{resource.path} - {resource.description}")
```

---

### 2️⃣ Executar um Recurso

```python
# Executar recurso de consulta de paciente
result = client.execute(
    path="/api/v1/consultar-paciente",
    connection_id="uuid-da-conexao",
    parameters={
        "cpf": "12345678900"
    }
)

if result.success:
    print("Paciente encontrado:")
    for row in result.rows:
        print(f"  Nome: {row['nome']}")
        print(f"  Email: {row['email']}")
else:
    print(f"Erro: {result.error}")
```

---

### 3️⃣ Criar Wrapper no Seu Backend (Flask)

```python
from flask import Flask, request, jsonify
from admin_api_sdk import AdminAPIClient, ExecutionError

app = Flask(__name__)
admin_api = AdminAPIClient("http://localhost:8000")

@app.route("/paciente/<cpf>")
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

    except ExecutionError as e:
        return jsonify({
            "error": e.message
        }), 500
```

---

### 4️⃣ Criar Wrapper no Seu Backend (FastAPI)

```python
from fastapi import FastAPI, HTTPException, Header
from admin_api_sdk import AdminAPIClient, ExecutionError

app = FastAPI()
admin_api = AdminAPIClient("http://localhost:8000")

@app.get("/paciente/{cpf}")
async def get_paciente(cpf: str, x_connection_id: str = Header(...)):
    try:
        result = admin_api.execute(
            path="/api/v1/consultar-paciente",
            connection_id=x_connection_id,
            parameters={"cpf": cpf}
        )

        if not result.success:
            raise HTTPException(500, result.error)

        return {"data": result.rows}

    except ExecutionError as e:
        raise HTTPException(500, e.message)
```

---

### 5️⃣ Tratar Erros Adequadamente

```python
from admin_api_sdk import (
    AdminAPIClient,
    ConnectionError,
    ResourceNotFoundError,
    ExecutionError
)

client = AdminAPIClient("http://localhost:8000")

try:
    result = client.execute(
        path="/api/v1/consultar-paciente",
        connection_id="conn-uuid",
        parameters={"cpf": "12345678900"}
    )

    if result.success:
        print(f"Dados: {result.rows}")

except ConnectionError:
    print("❌ Não foi possível conectar ao Admin API Backend")

except ResourceNotFoundError:
    print("❌ Recurso não encontrado")

except ExecutionError as e:
    print(f"❌ Erro na execução: {e.message}")
    if e.step:
        print(f"   Falhou no step {e.step}: {e.business_object_name}")
```

---

### 6️⃣ Buscar Recursos

```python
# Buscar por path
resource = client.get_resource_by_path("/api/v1/consultar-paciente")

if resource:
    print(f"Recurso: {resource.id}")
    print(f"Ativo: {resource.is_active}")
    print(f"Business Object: {resource.business_object_name}")

# Buscar por texto
results = client.search_resources("paciente")
print(f"Encontrados {len(results)} recursos")
```

---

### 7️⃣ Gerenciar Recursos Programaticamente

```python
# Criar novo recurso
resource = client.create_resource(
    path="/api/v1/novo-endpoint",
    business_object_id="uuid-do-bo",
    description="Meu novo endpoint",
    is_active=True
)

print(f"Criado: {resource.id}")

# Atualizar recurso
updated = client.update_resource(
    resource_id=resource.id,
    description="Nova descrição",
    is_active=False
)

# Ativar/Desativar
toggled = client.toggle_resource(resource.id)
print(f"Agora está: {'ativo' if toggled.is_active else 'inativo'}")

# Deletar
client.delete_resource(resource.id)
print("Recurso deletado")
```

---

### 8️⃣ Trabalhar com Cadeias de Execução

```python
# Executar recurso com cadeia
result = client.execute(
    path="/api/v1/recurso-com-cadeia",
    connection_id="conn-uuid",
    parameters={"clienteId": 123}
)

# Verificar se é resultado de cadeia
if hasattr(result, 'steps'):
    print(f"✓ Executou {result.steps} steps")
    print(f"Resultado final: {result.result}")
    print(f"Todos os resultados: {result.all_results}")
```

---

### 9️⃣ Verificar Saúde da API

```python
if client.health_check():
    print("✓ Admin API está funcionando")
else:
    print("✗ Admin API não está respondendo")
```

---

### 🔟 Filtrar Recursos Ativos/Inativos

```python
# Apenas recursos ativos
active = client.get_active_resources()
print(f"Recursos ativos: {len(active)}")

# Apenas recursos inativos
inactive = client.get_inactive_resources()
print(f"Recursos inativos: {len(inactive)}")
```

---

## Padrões de Uso Recomendados

### ✅ Singleton Client

```python
# Crie uma instância única do client
# config.py
from admin_api_sdk import AdminAPIClient

ADMIN_API_CLIENT = AdminAPIClient("http://localhost:8000")

# Use em qualquer lugar
# views.py
from config import ADMIN_API_CLIENT

result = ADMIN_API_CLIENT.execute(...)
```

### ✅ Wrapper Service

```python
# Crie um serviço wrapper para encapsular chamadas
class PacienteService:
    def __init__(self, admin_client):
        self.admin_client = admin_client

    def consultar_por_cpf(self, cpf: str, connection_id: str):
        return self.admin_client.execute(
            path="/api/v1/consultar-paciente",
            connection_id=connection_id,
            parameters={"cpf": cpf}
        )

    def listar_agendamentos(self, paciente_id: int, connection_id: str):
        return self.admin_client.execute(
            path="/api/v1/listar-agendamentos",
            connection_id=connection_id,
            parameters={"pacienteId": paciente_id}
        )

# Uso
service = PacienteService(ADMIN_API_CLIENT)
paciente = service.consultar_por_cpf("12345678900", "conn-uuid")
```

### ✅ Cache de Recursos

```python
# Cache recursos para evitar chamadas repetidas
class ResourceCache:
    def __init__(self, client):
        self.client = client
        self._cache = {}

    def get_resource(self, path: str):
        if path not in self._cache:
            self._cache[path] = self.client.get_resource_by_path(path)
        return self._cache[path]

    def clear(self):
        self._cache = {}
```

---

## Troubleshooting

### Erro de Conexão

```python
# Verifique se o backend está rodando
if not client.health_check():
    print("Backend não está rodando em http://localhost:8000")
```

### Recurso Não Encontrado

```python
# Liste recursos disponíveis
resources = client.list_resources()
print("Recursos disponíveis:")
for r in resources:
    print(f"  {r.path}")
```

### Erro de Execução

```python
# Verifique os parâmetros esperados
resource = client.get_resource_by_path("/api/v1/seu-endpoint")
print("Parâmetros esperados:")
for param in resource.business_object_params:
    print(f"  {param.name} ({param.type}) - Required: {param.required}")
```

---

## Próximos Passos

1. ✅ Instalar SDK no seu projeto
2. ✅ Testar conexão com `health_check()`
3. ✅ Listar recursos disponíveis
4. ✅ Executar seu primeiro recurso
5. ✅ Criar wrappers no seu backend
6. ✅ Implementar tratamento de erros
7. ✅ Criar testes

**Veja `examples.py` para mais exemplos completos!**
