# API Resources - Sistema de Endpoints Dinâmicos

## Visão Geral

O sistema de API Resources permite criar endpoints dinâmicos de API que executam Business Objects (objetos de negócio) configurados previamente. Um API Resource é essencialmente um endpoint REST que, quando chamado, executa uma query SQL parametrizada e retorna o resultado.

## Setup

### 1. Criar a Tabela no Banco de Dados

```bash
# Com Docker (recomendado)
docker exec -i admin-api-db psql -U admin -d admindb < sql/006_create_api_resources_table.sql

# Sem Docker
psql -h localhost -U admin -d admindb -f sql/006_create_api_resources_table.sql
```

### 2. Reiniciar a Aplicação

```bash
# Com Docker
docker-compose restart app

# Sem Docker
# Ctrl+C e depois
poetry run uvicorn app.main:app --reload
```

## Estrutura de Dados

### API Resource

```json
{
  "id": "uuid-123",
  "path": "/api/v1/consultar-paciente",
  "method": "POST",
  "description": "Consulta paciente por ID",
  "isActive": true,
  "businessObjectId": "uuid-do-business-object",
  "businessObjectName": "Consultar Paciente",
  "businessObjectParams": [
    {
      "name": "id",
      "type": "string",
      "required": false,
      "defaultValue": null
    }
  ],
  "createdAt": "2025-01-15T10:30:00Z",
  "updatedAt": "2025-01-15T10:30:00Z"
}
```

## Endpoints da API

### 1. Listar Todos os API Resources

```http
GET /api/v1/api-resources
```

**Response:**
```json
[
  {
    "id": "uuid-123",
    "path": "/api/v1/consultar-paciente",
    "method": "POST",
    "description": "Consulta paciente por ID",
    "isActive": true,
    "businessObjectId": "uuid-do-bo",
    "businessObjectName": "Consultar Paciente",
    "businessObjectParams": [...],
    "createdAt": "2025-01-15T10:30:00Z",
    "updatedAt": "2025-01-15T10:30:00Z"
  }
]
```

### 2. Buscar API Resource por ID

```http
GET /api/v1/api-resources/{id}
```

**Response:** Mesmo formato do item acima.

### 3. Criar Novo API Resource

```http
POST /api/v1/api-resources
Content-Type: application/json

{
  "path": "/api/v1/consultar-paciente",
  "description": "Consulta paciente por ID",
  "isActive": true,
  "businessObjectId": "uuid-do-business-object"
}
```

**Validações:**
- `path` deve ser único
- `path` deve começar com `/`
- `businessObjectId` deve existir na tabela de Business Objects
- Copia automaticamente `name` e `params` do Business Object

**Response:** Objeto criado (mesmo formato GET)

### 4. Atualizar API Resource

```http
PATCH /api/v1/api-resources/{id}
Content-Type: application/json

{
  "path": "/api/v1/novo-path",
  "description": "Nova descrição",
  "isActive": false,
  "businessObjectId": "outro-uuid"
}
```

Todos os campos são opcionais. Se `businessObjectId` for atualizado, o sistema atualiza automaticamente o snapshot dos metadados.

**Response:** Objeto atualizado

### 5. Deletar API Resource

```http
DELETE /api/v1/api-resources/{id}
```

**Response:** `204 No Content`

### 6. Alternar Status (Ativar/Desativar)

```http
PATCH /api/v1/api-resources/{id}/toggle
```

**Response:** Objeto atualizado com `isActive` invertido

## Endpoints Dinâmicos

Quando um API Resource está ativo (`isActive = true`), o sistema cria automaticamente um endpoint no path especificado.

### Exemplo

Se você criar um API Resource:

```json
{
  "path": "/api/v1/consultar-paciente",
  "method": "POST",
  "businessObjectId": "uuid-do-bo",
  "businessObjectParams": [
    {"name": "id", "type": "string", "required": false}
  ]
}
```

O sistema automaticamente cria:

```http
POST /api/v1/consultar-paciente
Content-Type: application/json

{
  "connectionId": "uuid-da-conexao",
  "id": "123"
}
```

**Response:**
```json
{
  "success": true,
  "rows": [
    {
      "id": "123",
      "nome": "João Silva",
      "idade": 35
    }
  ],
  "rowCount": 1
}
```

### Formato da Requisição

```json
{
  "connectionId": "uuid-da-conexao-do-banco",  // OBRIGATÓRIO
  "param1": "valor1",
  "param2": "valor2"
  // ... outros parâmetros definidos no Business Object
}
```

### Formato da Response

```json
{
  "success": true,
  "rows": [...],      // Array de objetos (SELECT) ou vazio (INSERT/UPDATE/DELETE)
  "rowCount": 10      // Número de linhas retornadas ou afetadas
}
```

Ou em caso de erro:

```json
{
  "success": false,
  "error": "Mensagem de erro"
}
```

## Como Funciona

1. **Criação do API Resource**: Quando você cria um API Resource, o sistema:
   - Valida o path e business object
   - Copia os metadados do Business Object (nome e parâmetros) como snapshot
   - Registra a nova rota dinamicamente na aplicação

2. **Execução do Endpoint Dinâmico**: Quando o endpoint é chamado:
   - Valida que o recurso está ativo
   - Busca o Business Object associado
   - Decodifica o SQL do Business Object (Base64)
   - Substitui os parâmetros `:param_name` com os valores do body
   - Executa o SQL na conexão especificada (`connectionId`)
   - Retorna os resultados

3. **Atualização/Deleção**: Quando você atualiza ou deleta um API Resource:
   - O sistema automaticamente atualiza as rotas dinâmicas
   - Se desativado (`isActive = false`), o endpoint retorna 404
   - Se deletado, a rota é removida completamente

## Tipos de Parâmetros

O sistema suporta 3 tipos de parâmetros:

- **string**: Valores de texto (envoltos em aspas simples no SQL)
- **number**: Valores numéricos (sem aspas no SQL)
- **date**: Valores de data (envoltos em aspas simples no SQL)

Exemplo de Business Object com parâmetros:

```sql
-- SQL do Business Object (em Base64)
SELECT * FROM pacientes
WHERE id = :id
  AND idade > :idade_minima
  AND data_nascimento = :data_nasc
```

Parâmetros definidos:
```json
[
  {"name": "id", "type": "string", "required": true},
  {"name": "idade_minima", "type": "number", "required": false, "defaultValue": 18},
  {"name": "data_nasc", "type": "date", "required": false}
]
```

Chamada do endpoint:
```json
{
  "connectionId": "uuid-123",
  "id": "PAC-001",
  "idade_minima": 25,
  "data_nasc": "1990-01-15"
}
```

SQL executado:
```sql
SELECT * FROM pacientes
WHERE id = 'PAC-001'
  AND idade > 25
  AND data_nascimento = '1990-01-15'
```

## Segurança

- **Validação de Parâmetros**: Todos os parâmetros são escapados para prevenir SQL Injection
- **Conexões Isoladas**: Cada execução usa a conexão especificada no `connectionId`
- **Validação de Status**: Apenas recursos ativos podem ser executados
- **Foreign Key**: Não é possível deletar um Business Object se houver API Resources associados

## Logs

O sistema registra logs detalhados:

- Inicialização de rotas dinâmicas no startup
- Registro de cada rota dinâmica
- Erros de execução SQL
- Falhas de validação

Exemplo de logs:
```
2025-01-15 10:30:00 - app.main - INFO - Starting application...
2025-01-15 10:30:00 - app.core.dynamic_routes - INFO - Refreshing dynamic routes: found 3 active resources
2025-01-15 10:30:00 - app.core.dynamic_routes - INFO - Registered dynamic route: POST /api/v1/consultar-paciente
2025-01-15 10:30:00 - app.main - INFO - Dynamic routes initialized successfully
```

## Troubleshooting

### Erro: "API resource not found"
- Verifique se o recurso existe: `GET /api/v1/api-resources/{id}`
- Verifique se está ativo (`isActive = true`)

### Erro: "connection_id is required"
- Sempre inclua `connectionId` no body da requisição ao chamar endpoints dinâmicos

### Erro: "Business object with id X not found"
- O Business Object foi deletado ou o ID está incorreto
- Verifique: `GET /api/v1/business-objects/{id}`

### Endpoint dinâmico não aparece
- Reinicie a aplicação para recarregar as rotas
- Verifique se `isActive = true`
- Verifique os logs para erros de registro

### SQL não executa corretamente
- Verifique se os parâmetros no SQL usam formato `:param_name`
- Verifique se os tipos dos parâmetros estão corretos
- Use o endpoint de teste do Business Object primeiro: `POST /api/v1/business-objects/{id}/test`

## Exemplos Completos

### Criar um Recurso de Consulta de Usuários

1. **Criar o Business Object:**
```http
POST /api/v1/business-objects
Content-Type: application/json

{
  "name": "Listar Usuários por Status",
  "commandType": "select",
  "sqlCommand": "U0VMRUNUICogRlJPTSB1c3VhcmlvcyBXSEVSRSBzdGF0dXMgPSA6c3RhdHVz",
  "params": [
    {
      "name": "status",
      "type": "string",
      "required": true
    }
  ]
}
```

2. **Criar o API Resource:**
```http
POST /api/v1/api-resources
Content-Type: application/json

{
  "path": "/api/v1/usuarios/por-status",
  "description": "Lista usuários filtrados por status",
  "isActive": true,
  "businessObjectId": "uuid-retornado-acima"
}
```

3. **Usar o Endpoint Dinâmico:**
```http
POST /api/v1/usuarios/por-status
Content-Type: application/json

{
  "connectionId": "uuid-da-conexao",
  "status": "ativo"
}
```

## Swagger/OpenAPI

Todos os endpoints (CRUD e dinâmicos) aparecem automaticamente na documentação Swagger:

- Acesse: `http://localhost:8000/api/v1/docs`
- Os endpoints dinâmicos aparecem na tag "Dynamic API Resources"
- Os endpoints CRUD aparecem na tag "api-resources"
