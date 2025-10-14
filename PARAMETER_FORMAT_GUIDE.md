# Guia de Uso de Parâmetros em Business Objects

## Visão Geral

O sistema suporta dois formatos de parâmetros em comandos SQL:

1. **Formato novo (recomendado)**: `:paramName` - Com definição de tipos e valores padrão
2. **Formato legado**: `{{paramName}}` - Para compatibilidade com objetos antigos

## Formato Recomendado: `:paramName`

### Características

- Suporte a tipos de dados: `string`, `number`, `date`
- Valores padrão configuráveis
- Validação de consistência entre SQL e definições
- Substituição automática com tipagem correta (números sem aspas, strings com aspas)

### Exemplo de Business Object

```json
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
  "tags": ["pacientes", "busca"]
}
```

**SQL decodificado:**
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

### Requisição de Teste

```json
POST /api/v1/business-objects/{id}/test

{
  "connection_id": "ccc59f20-a9a8-4101-be19-9ff19e27a985",
  "parameters": {
    "cpf": "12345678900"
  }
}
```

**SQL executado:**
```sql
SELECT
  pac.pac_reg as codigo,
  pac.pac_nome as nome,
  pac.pac_numcpf as cpf,
  pac.pac_dreg as data_cadastro
FROM
   pac WITH(NOLOCK)
WHERE
   pac.pac_numcpf = '12345678900'  -- String com aspas
ORDER BY
   pac.pac_dreg ASC
```

## Tipos de Parâmetros e Substituição

### 1. String (`"type": "string"`)

**Definição:**
```json
{
  "name": "status",
  "type": "string",
  "required": false,
  "defaultValue": "active"
}
```

**SQL:** `WHERE status = :status`

**Parâmetro enviado:** `{"status": "active"}`

**SQL final:** `WHERE status = 'active'`

**Observações:**
- Valores são sempre colocados entre aspas simples
- Aspas simples no valor são escapadas (`'` → `''`)

### 2. Number (`"type": "number"`)

**Definição:**
```json
{
  "name": "age",
  "type": "number",
  "required": false,
  "defaultValue": 18
}
```

**SQL:** `WHERE age > :age`

**Parâmetro enviado:** `{"age": "25"}`

**SQL final:** `WHERE age > 25`

**Observações:**
- Números NÃO têm aspas
- Valores são validados como numéricos
- Se não for um número válido, é substituído por `NULL`

### 3. Date (`"type": "date"`)

**Definição:**
```json
{
  "name": "startDate",
  "type": "date",
  "required": true,
  "defaultValue": "2024-01-01"
}
```

**SQL:** `WHERE created_at > :startDate`

**Parâmetro enviado:** `{"startDate": "2024-06-15"}`

**SQL final:** `WHERE created_at > '2024-06-15'`

**Observações:**
- Datas são tratadas como strings (com aspas)
- Formato esperado: ISO 8601 (YYYY-MM-DD)

## Valores Padrão (defaultValue)

Quando um parâmetro não é fornecido na requisição, o sistema usa o `defaultValue`:

**Exemplo:**

```json
{
  "name": "status",
  "type": "string",
  "required": false,
  "defaultValue": "active"
}
```

**Requisição sem parâmetro:**
```json
{
  "connection_id": "...",
  "parameters": {}
}
```

**Resultado:** `WHERE status = 'active'` (usa o defaultValue)

Se não houver `defaultValue` ou ele for `null`:
- **Resultado:** `WHERE status = NULL`

## Validações no Cadastro/Atualização

Ao criar ou atualizar um Business Object, o sistema valida:

1. **Parâmetros no SQL devem ter definição**
   ```
   SQL: WHERE id = :userId AND status = :status
   Params: [{"name": "userId", ...}]
   ❌ Erro: "Parameter ':status' found in SQL but not defined in params array"
   ```

2. **Parâmetros definidos devem ser usados no SQL**
   ```
   SQL: WHERE id = :userId
   Params: [{"name": "userId", ...}, {"name": "oldParam", ...}]
   ❌ Erro: "Parameter 'oldParam' defined in params but not used in SQL command"
   ```

3. **Nomes de parâmetros devem ser únicos**
   ```
   Params: [
     {"name": "userId", ...},
     {"name": "userId", ...}
   ]
   ❌ Erro: "Duplicate parameter definitions found: userId"
   ```

4. **defaultValue deve ser compatível com o tipo**
   ```json
   {
     "name": "age",
     "type": "number",
     "defaultValue": "not a number"
   }
   ❌ Erro de validação
   ```

## Comparação: Novo vs Legado

| Característica | `:paramName` (novo) | `{{paramName}}` (legado) |
|---|---|---|
| Tipagem | ✅ Sim (string, number, date) | ❌ Tudo é string |
| Valores padrão | ✅ Sim | ❌ Não (sempre NULL) |
| Validação | ✅ Sim (consistência SQL/params) | ❌ Não |
| Substituição | ✅ Inteligente (com/sem aspas) | ⚠️ Sempre com aspas |
| Recomendado | ✅ Sim | ⚠️ Apenas compatibilidade |

## Exemplos Completos

### Exemplo 1: Busca com Múltiplos Parâmetros

**SQL:**
```sql
SELECT * FROM users
WHERE status = :status
  AND age > :minAge
  AND created_at > :startDate
ORDER BY created_at DESC
```

**Definição de Params:**
```json
{
  "params": [
    {
      "name": "status",
      "type": "string",
      "required": false,
      "defaultValue": "active"
    },
    {
      "name": "minAge",
      "type": "number",
      "required": false,
      "defaultValue": 18
    },
    {
      "name": "startDate",
      "type": "date",
      "required": true,
      "defaultValue": null
    }
  ]
}
```

**Requisição de Teste:**
```json
{
  "connection_id": "...",
  "parameters": {
    "status": "active",
    "minAge": "21",
    "startDate": "2024-01-01"
  }
}
```

**SQL Executado:**
```sql
SELECT * FROM users
WHERE status = 'active'
  AND age > 21
  AND created_at > '2024-01-01'
ORDER BY created_at DESC
```

### Exemplo 2: Parâmetro Repetido no SQL

**SQL:**
```sql
SELECT * FROM users
WHERE first_name = :name OR last_name = :name
```

**Definição:**
```json
{
  "params": [
    {
      "name": "name",
      "type": "string",
      "required": true,
      "defaultValue": null
    }
  ]
}
```

**Requisição:**
```json
{
  "connection_id": "...",
  "parameters": {
    "name": "João"
  }
}
```

**SQL Executado:**
```sql
SELECT * FROM users
WHERE first_name = 'João' OR last_name = 'João'
```

## Migração de Objetos Legados

Para migrar Business Objects do formato `{{param}}` para `:param`:

1. Identifique os parâmetros no SQL atual
2. Crie as definições de `params` com tipos apropriados
3. Substitua `{{paramName}}` por `:paramName` no SQL
4. Atualize o Business Object via API

**Antes:**
```sql
SELECT * FROM users WHERE id = {{userId}}
```

**Depois:**
```sql
SELECT * FROM users WHERE id = :userId
```

Com definição:
```json
{
  "params": [
    {
      "name": "userId",
      "type": "number",
      "required": true,
      "defaultValue": null
    }
  ]
}
```

## Troubleshooting

### Erro: "A value is required for bind parameter"

**Causa:** O SQL está usando placeholders `?` ou parâmetros não estão sendo substituídos corretamente.

**Solução:** Certifique-se de que:
1. O SQL usa o formato `:paramName` (não `?` ou `{{paramName}}`)
2. Todos os parâmetros estão definidos em `params`
3. O Business Object foi salvo com a definição de `params`

### Erro: "Parameter validation failed"

**Causa:** Inconsistência entre SQL e definições de parâmetros.

**Solução:** Verifique que:
1. Todos os `:paramName` no SQL têm definição em `params`
2. Todos os parâmetros em `params` são usados no SQL
3. Não há nomes duplicados em `params`

### Parâmetro não está sendo substituído

**Solução:**
1. Verifique o formato: deve ser `:paramName` (com dois pontos)
2. Certifique-se que o nome no `params` é exatamente igual ao nome no SQL
3. Verifique que o parâmetro está sendo enviado na requisição de teste

## Referências

- Documentação completa: `IMPLEMENTATION_SUMMARY.md`
- Exemplos de API: `examples_api_curl.sh`
- Código de validação: `app/utils/parameter_validation.py`
- Endpoint de teste: `app/api/v1/endpoints/business_objects.py:test_business_object`
