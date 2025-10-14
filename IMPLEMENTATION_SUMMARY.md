# Implementação de Parâmetros para Business Objects

## Resumo
Implementação completa de suporte a parâmetros SQL no formato `:paramName` para Business Objects, incluindo validação, armazenamento e documentação.

## Arquivos Modificados

### 1. Schema SQL
**Arquivo:** `sql/005_add_params_to_business_objects.sql`
- Adiciona coluna `params` tipo JSONB à tabela `business_objects`
- Cria índice GIN para queries JSON eficientes
- Adiciona comentário documentando a estrutura dos parâmetros

### 2. Modelo SQLAlchemy
**Arquivo:** `app/models/business_object.py`
- Adiciona campo `params: Mapped[list]` com tipo JSONB

### 3. Schemas Pydantic
**Arquivo:** `app/schemas/business_object.py`
- **Nova classe `SqlParameter`**: Schema para definição de parâmetros
  - Campos: `name`, `type`, `required`, `defaultValue`
  - Validações:
    - Nome alfanumérico (sem prefixo `:`)
    - Tipos suportados: `string`, `number`, `date`
    - defaultValue validado de acordo com o tipo
- **`BusinessObjectBase`**: Adiciona campo `params: list[SqlParameter]`
- **`BusinessObjectUpdate`**: Adiciona campo `params: list[SqlParameter] | None`

### 4. Utilitários de Validação
**Arquivo:** `app/utils/parameter_validation.py` (novo)
Funções implementadas:
- `extract_sql_parameters(sql_command)`: Extrai parâmetros do SQL usando regex
- `validate_parameters(sql_command, params)`: Valida consistência entre SQL e definições
- `convert_to_dict(params)`: Converte SqlParameter para dict (storage)
- `convert_from_dict(params_data)`: Converte dict para SqlParameter (retrieval)

### 5. Endpoints
**Arquivo:** `app/api/v1/endpoints/business_objects.py`
- **POST `/business-objects`**: Valida parâmetros antes de criar
- **PATCH `/business-objects/{id}`**: Valida parâmetros se sql_command ou params forem atualizados
- Retorna erro 400 com detalhes quando validação falha

## Validações Implementadas

### 1. Validação de Nome de Parâmetro
- Deve conter apenas caracteres alfanuméricos, underscores e hífens
- Não pode começar com `:` (o prefixo é apenas no SQL)

### 2. Validação de Tipo de Parâmetro
- Tipos permitidos: `string`, `number`, `date`
- Tipo literal validado pelo Pydantic

### 3. Validação de defaultValue
- **number**: Deve ser int, float ou string convertível para número
- **date**: Deve ser string (formato ISO esperado)
- **string**: Deve ser string
- Aceita `null` para qualquer tipo

### 4. Validação de Consistência SQL/Params
- Todos os parâmetros no SQL (`:paramName`) devem ter definição em `params`
- Todas as definições em `params` devem ser usadas no SQL
- Não pode haver nomes duplicados em `params`

## Formato de Erro

Quando a validação falha, o endpoint retorna:

```json
{
  "detail": {
    "error": "Parameter validation failed",
    "details": [
      "Parameter(s) ':userId' found in SQL but not defined in params array",
      "Parameter(s) 'oldParam' defined in params but not used in SQL command"
    ]
  }
}
```

## Exemplo de Uso

### Criar Business Object com Parâmetros

```bash
POST /business-objects
Content-Type: application/json

{
  "name": "Usuários Ativos",
  "command_type": "select",
  "sqlCommand": "U0VMRUNUICogRlJPTSB1c2VycyBXSEVSRSBzdGF0dXMgPSA6c3RhdHVzIEFORCBjcmVhdGVkX2F0ID4gOnN0YXJ0RGF0ZQ==",
  "params": [
    {
      "name": "status",
      "type": "string",
      "required": true,
      "defaultValue": "active"
    },
    {
      "name": "startDate",
      "type": "date",
      "required": true,
      "defaultValue": "2024-01-01"
    }
  ],
  "tags": ["users", "active"]
}
```

**Nota:** `sqlCommand` deve estar em BASE64:
```
Base64("SELECT * FROM users WHERE status = :status AND created_at > :startDate")
```

### Resposta de Sucesso

```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "name": "Usuários Ativos",
  "command_type": "select",
  "sqlCommand": "U0VMRUNUICogRlJPTSB1c2VycyBXSEVSRSBzdGF0dXMgPSA6c3RhdHVzIEFORCBjcmVhdGVkX2F0ID4gOnN0YXJ0RGF0ZQ==",
  "params": [
    {
      "name": "status",
      "type": "string",
      "required": true,
      "defaultValue": "active"
    },
    {
      "name": "startDate",
      "type": "date",
      "required": true,
      "defaultValue": "2024-01-01"
    }
  ],
  "tags": ["users", "active"],
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

## Aplicar Migração do Banco de Dados

Para aplicar a migração SQL:

```bash
# Via Docker (recomendado)
docker exec -i admin-api-db psql -U admin -d admindb < sql/005_add_params_to_business_objects.sql

# Via psql local
psql -h localhost -U admin -d admindb -f sql/005_add_params_to_business_objects.sql
```

## Testes

Um script de testes foi criado em `test_parameter_validation.py`:

```bash
python test_parameter_validation.py
```

**Testes incluídos:**
- Extração de parâmetros de SQL simples
- Extração de SQL codificado em BASE64
- Parâmetros repetidos (set único)
- SQL sem parâmetros
- Validação de parâmetros válidos
- Detecção de parâmetros faltando definição
- Detecção de parâmetros não utilizados
- Detecção de nomes duplicados
- Validação de schema (nome, tipo, defaultValue)

## Endpoints Afetados

### GET /business-objects
- Retorna todos os Business Objects incluindo campo `params`

### GET /business-objects/{id}
- Retorna Business Object específico incluindo campo `params`

### POST /business-objects
- Cria novo Business Object
- **Valida parâmetros** antes de salvar
- Retorna 400 se validação falhar

### PATCH /business-objects/{id}
- Atualiza Business Object
- **Valida parâmetros** se `sql_command` ou `params` forem modificados
- Retorna 400 se validação falhar

### DELETE /business-objects/{id}
- Sem mudanças

### POST /business-objects/{id}/test
- Endpoint de teste continua funcionando
- **Nota:** O endpoint atual usa formato `{{parameter}}` para substituição
- Considerar migrar para `:parameter` no futuro se necessário

## Compatibilidade

### Sistema Existente
- Business Objects existentes sem `params` continuam funcionando
- Campo `params` tem valor padrão `[]` (array vazio)
- Endpoints GET retornam `params: []` para registros antigos

### Migração Gradual
1. Aplicar schema SQL (adiciona coluna com default)
2. Atualizar código (backward compatible)
3. Migrar Business Objects existentes conforme necessário

## Próximos Passos (Opcional)

1. **Unificar formato de parâmetros**: Atualmente existem dois formatos:
   - `:paramName` (novo, para definição)
   - `{{paramName}}` (usado no endpoint de teste)
   - Considerar padronizar para um único formato

2. **Validação em runtime**: Implementar validação de valores de parâmetros durante execução:
   - Valores required não podem ser null
   - Tipo number deve ser numérico
   - Tipo date deve ser data válida

3. **Documentação OpenAPI**: Adicionar exemplos de parâmetros na documentação Swagger

4. **Testes unitários**: Adicionar testes pytest formais ao projeto

## Observações Importantes

- SQL deve estar sempre em **BASE64** nos endpoints
- Parâmetros no SQL usam formato **`:paramName`** (com dois pontos)
- Parâmetros em `params` usam **`name: "paramName"`** (sem dois pontos)
- O mesmo parâmetro pode aparecer múltiplas vezes no SQL (é validado como único)
- Validações são executadas apenas em CREATE e UPDATE de Business Objects
