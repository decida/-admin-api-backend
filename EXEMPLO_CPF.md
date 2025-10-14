# Exemplo: Business Object de Busca por CPF

## Problema Resolvido

Erro anterior:
```
sqlalchemy.exc.InvalidRequestError: A value is required for bind parameter 'cpf'
```

**Causa:** O SQL tinha o placeholder `?` e não estava substituindo o parâmetro `:cpf` corretamente.

**Solução:** Usar o formato `:cpf` no SQL e definir o parâmetro no array `params`.

## Configuração do Business Object

### SQL Original (BASE64)

```sql
SELECT
  pac.pac_reg as codigo,
  pac.pac_nome as nome,
  pac.pac_numcpf as cpf,
  pac.pac_dreg as data_cadastro
FROM
   pac WITH(NOLOCK)
WHERE
   pac.pac_numcpf = :cpf
ORDER BY
   pac.pac_dreg ASC
```

**Converter para BASE64:**

```bash
# Linux/Mac
echo -n "SELECT
  pac.pac_reg as codigo,
  pac.pac_nome as nome,
  pac.pac_numcpf as cpf,
  pac.pac_dreg as data_cadastro
FROM
   pac WITH(NOLOCK)
WHERE
   pac.pac_numcpf = :cpf
ORDER BY
   pac.pac_dreg ASC" | base64

# PowerShell (Windows)
$sql = @"
SELECT
  pac.pac_reg as codigo,
  pac.pac_nome as nome,
  pac.pac_numcpf as cpf,
  pac.pac_dreg as data_cadastro
FROM
   pac WITH(NOLOCK)
WHERE
   pac.pac_numcpf = :cpf
ORDER BY
   pac.pac_dreg ASC
"@
[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($sql))
```

**Resultado BASE64:**
```
U0VMRUNUCiAgcGFjLnBhY19yZWcgYXMgY29kaWdvLAogIHBhYy5wYWNfbm9tZSBhcyBub21lLAogIHBhYy5wYWNfbnVtY3BmIGFzIGNwZiwKICBwYWMucGFjX2RyZWcgYXMgZGF0YV9jYWRhc3RybwpGUk9NCiAgIHBhYyBXSVRIKE5PTE9DSykKV0hFUkUKICAgcGFjLnBhY19udW1jcGYgPSA6Y3BmCk9SREVSIEJZCiAgIHBhYy5wYWNfZHJlZyBBU0M=
```

## Criar/Atualizar Business Object

### Request

```http
POST /api/v1/business-objects
Content-Type: application/json

{
  "name": "Buscar Paciente por CPF",
  "command_type": "select",
  "sqlCommand": "U0VMRUNUCiAgcGFjLnBhY19yZWcgYXMgY29kaWdvLAogIHBhYy5wYWNfbm9tZSBhcyBub21lLAogIHBhYy5wYWNfbnVtY3BmIGFzIGNwZiwKICBwYWMucGFjX2RyZWcgYXMgZGF0YV9jYWRhc3RybwpGUk9NCiAgIHBhYyBXSVRIKE5PTE9DSykKV0hFUkUKICAgcGFjLnBhY19udW1jcGYgPSA6Y3BmCk9SREVSIEJZCiAgIHBhYy5wYWNfZHJlZyBBU0M=",
  "params": [
    {
      "name": "cpf",
      "type": "string",
      "required": true,
      "defaultValue": null
    }
  ],
  "tags": ["pacientes", "busca", "cpf"]
}
```

### cURL

```bash
curl -X POST "http://localhost:8000/api/v1/business-objects" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Buscar Paciente por CPF",
    "command_type": "select",
    "sqlCommand": "U0VMRUNUCiAgcGFjLnBhY19yZWcgYXMgY29kaWdvLAogIHBhYy5wYWNfbm9tZSBhcyBub21lLAogIHBhYy5wYWNfbnVtY3BmIGFzIGNwZiwKICBwYWMucGFjX2RyZWcgYXMgZGF0YV9jYWRhc3RybwpGUk9NCiAgIHBhYyBXSVRIKE5PTE9DSykKV0hFUkUKICAgcGFjLnBhY19udW1jcGYgPSA6Y3BmCk9SREVSIEJZCiAgIHBhYy5wYWNfZHJlZyBBU0M=",
    "params": [
      {
        "name": "cpf",
        "type": "string",
        "required": true,
        "defaultValue": null
      }
    ],
    "tags": ["pacientes", "busca", "cpf"]
  }'
```

### Response (Sucesso)

```json
{
  "id": "abc12345-6789-4def-ghij-klmnopqrstuv",
  "name": "Buscar Paciente por CPF",
  "command_type": "select",
  "sqlCommand": "U0VMRUNUCiAgcGFjLnBhY19yZWcgYXMgY29kaWdvLAogIHBhYy5wYWNfbm9tZSBhcyBub21lLAogIHBhYy5wYWNfbnVtY3BmIGFzIGNwZiwKICBwYWMucGFjX2RyZWcgYXMgZGF0YV9jYWRhc3RybwpGUk9NCiAgIHBhYyBXSVRIKE5PTE9DSykKV0hFUkUKICAgcGFjLnBhY19udW1jcGYgPSA6Y3BmCk9SREVSIEJZCiAgIHBhYy5wYWNfZHJlZyBBU0M=",
  "params": [
    {
      "name": "cpf",
      "type": "string",
      "required": true,
      "defaultValue": null
    }
  ],
  "tags": ["pacientes", "busca", "cpf"],
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

## Testar Execução

### Request

```http
POST /api/v1/business-objects/{id}/test
Content-Type: application/json

{
  "connection_id": "ccc59f20-a9a8-4101-be19-9ff19e27a985",
  "parameters": {
    "cpf": "12345678900"
  }
}
```

### cURL

```bash
# Substitua {id} pelo ID retornado na criação
curl -X POST "http://localhost:8000/api/v1/business-objects/{id}/test" \
  -H "Content-Type: application/json" \
  -d '{
    "connection_id": "ccc59f20-a9a8-4101-be19-9ff19e27a985",
    "parameters": {
      "cpf": "12345678900"
    }
  }'
```

### SQL que será executado

```sql
SELECT
  pac.pac_reg as codigo,
  pac.pac_nome as nome,
  pac.pac_numcpf as cpf,
  pac.pac_dreg as data_cadastro
FROM
   pac WITH(NOLOCK)
WHERE
   pac.pac_numcpf = '12345678900'
ORDER BY
   pac.pac_dreg ASC
```

**Observe que:**
- `:cpf` foi substituído por `'12345678900'`
- O valor está entre aspas simples porque o tipo é `string`
- Não há mais erro "A value is required for bind parameter"

### Response (Sucesso)

```json
{
  "success": true,
  "rows": [
    {
      "codigo": 123,
      "nome": "João da Silva",
      "cpf": "12345678900",
      "data_cadastro": "2023-01-15T10:00:00"
    }
  ],
  "rowCount": 1
}
```

### Response (Sem resultados)

```json
{
  "success": true,
  "rows": [],
  "rowCount": 0
}
```

### Response (Erro)

```json
{
  "success": false,
  "error": "SQL syntax error: Invalid column name 'pac_numcpf'"
}
```

## Frontend - Como Enviar

### JavaScript/TypeScript

```typescript
// Definir o Business Object
const businessObject = {
  name: "Buscar Paciente por CPF",
  command_type: "select",
  sqlCommand: btoa(`SELECT
  pac.pac_reg as codigo,
  pac.pac_nome as nome,
  pac.pac_numcpf as cpf,
  pac.pac_dreg as data_cadastro
FROM
   pac WITH(NOLOCK)
WHERE
   pac.pac_numcpf = :cpf
ORDER BY
   pac.pac_dreg ASC`),
  params: [
    {
      name: "cpf",
      type: "string",
      required: true,
      defaultValue: null
    }
  ],
  tags: ["pacientes", "busca", "cpf"]
};

// Criar Business Object
const response = await fetch('/api/v1/business-objects', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(businessObject)
});

const created = await response.json();
console.log('Business Object criado:', created.id);

// Testar execução
const testResponse = await fetch(`/api/v1/business-objects/${created.id}/test`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    connection_id: "ccc59f20-a9a8-4101-be19-9ff19e27a985",
    parameters: {
      cpf: "12345678900"
    }
  })
});

const result = await testResponse.json();
if (result.success) {
  console.log('Pacientes encontrados:', result.rows);
  console.log('Total:', result.rowCount);
} else {
  console.error('Erro na execução:', result.error);
}
```

## Outros Exemplos com CPF

### Exemplo com múltiplos critérios

**SQL:**
```sql
SELECT * FROM pac
WHERE pac_numcpf = :cpf
  AND pac_status = :status
  AND pac_dreg > :dataInicio
```

**Params:**
```json
{
  "params": [
    {
      "name": "cpf",
      "type": "string",
      "required": true,
      "defaultValue": null
    },
    {
      "name": "status",
      "type": "string",
      "required": false,
      "defaultValue": "active"
    },
    {
      "name": "dataInicio",
      "type": "date",
      "required": false,
      "defaultValue": "2024-01-01"
    }
  ]
}
```

**Teste:**
```json
{
  "connection_id": "...",
  "parameters": {
    "cpf": "12345678900"
    // status e dataInicio usarão valores padrão
  }
}
```

### Exemplo com CPF parcial (LIKE)

**SQL:**
```sql
SELECT * FROM pac
WHERE pac_numcpf LIKE :cpfParcial
```

**Params:**
```json
{
  "params": [
    {
      "name": "cpfParcial",
      "type": "string",
      "required": true,
      "defaultValue": null
    }
  ]
}
```

**Teste:**
```json
{
  "connection_id": "...",
  "parameters": {
    "cpfParcial": "123%"
  }
}
```

**SQL executado:**
```sql
SELECT * FROM pac
WHERE pac_numcpf LIKE '123%'
```

## Checklist para Resolver o Erro

- [ ] SQL usa `:cpf` (não `?` ou `{{cpf}}`)
- [ ] Business Object tem definição de `params` com `name: "cpf"`
- [ ] SQL está codificado em BASE64
- [ ] Tipo do parâmetro está correto (`string` para CPF)
- [ ] Requisição de teste envia `{"cpf": "valor"}`
- [ ] Database migration foi aplicada (`sql/005_add_params_to_business_objects.sql`)
- [ ] Backend foi reiniciado após as mudanças

## Aplicar a Migração (Se ainda não fez)

```bash
# Via Docker
docker exec -i admin-api-db psql -U admin -d admindb < sql/005_add_params_to_business_objects.sql

# Via psql local
psql -h localhost -U admin -d admindb -f sql/005_add_params_to_business_objects.sql
```

## Testando Localmente

Para testar se está funcionando:

```bash
# 1. Aplicar migração
docker exec -i admin-api-db psql -U admin -d admindb < sql/005_add_params_to_business_objects.sql

# 2. Reiniciar backend
docker-compose restart api
# ou
docker-compose up --build

# 3. Criar Business Object com curl
curl -X POST "http://localhost:8000/api/v1/business-objects" \
  -H "Content-Type: application/json" \
  -d @- << 'EOF'
{
  "name": "Buscar Paciente por CPF",
  "command_type": "select",
  "sqlCommand": "U0VMRUNUCiAgcGFjLnBhY19yZWcgYXMgY29kaWdvLAogIHBhYy5wYWNfbm9tZSBhcyBub21lLAogIHBhYy5wYWNfbnVtY3BmIGFzIGNwZiwKICBwYWMucGFjX2RyZWcgYXMgZGF0YV9jYWRhc3RybwpGUk9NCiAgIHBhYyBXSVRIKE5PTE9DSykKV0hFUkUKICAgcGFjLnBhY19udW1jcGYgPSA6Y3BmCk9SREVSIEJZCiAgIHBhYy5wYWNfZHJlZyBBU0M=",
  "params": [
    {
      "name": "cpf",
      "type": "string",
      "required": true,
      "defaultValue": null
    }
  ],
  "tags": ["pacientes", "busca", "cpf"]
}
EOF

# 4. Testar execução (substitua {id} pelo retornado)
curl -X POST "http://localhost:8000/api/v1/business-objects/{id}/test" \
  -H "Content-Type: application/json" \
  -d '{
    "connection_id": "ccc59f20-a9a8-4101-be19-9ff19e27a985",
    "parameters": {
      "cpf": "12345678900"
    }
  }'
```

## Suporte

Se continuar com problemas:

1. Verifique os logs do backend para mensagens de erro detalhadas
2. Confirme que a coluna `params` foi adicionada à tabela `business_objects`:
   ```sql
   \d business_objects
   ```
3. Valide que o Business Object foi salvo com os params:
   ```sql
   SELECT id, name, params FROM business_objects WHERE name = 'Buscar Paciente por CPF';
   ```
4. Verifique se o SQL decodificado está correto:
   ```bash
   echo "U0VMRUNUCiAgcGFjLnBhY19yZWcgYXMgY29kaWdvLAogIHBhYy5wYWNfbm9tZSBhcyBub21lLAogIHBhYy5wYWNfbnVtY3BmIGFzIGNwZiwKICBwYWMucGFjX2RyZWcgYXMgZGF0YV9jYWRhc3RybwpGUk9NCiAgIHBhYyBXSVRIKE5PTE9DSykKV0hFUkUKICAgcGFjLnBhY19udW1jcGYgPSA6Y3BmCk9SREVSIEJZCiAgIHBhYy5wYWNfZHJlZyBBU0M=" | base64 -d
   ```
