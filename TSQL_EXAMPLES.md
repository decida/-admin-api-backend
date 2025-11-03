# T-SQL Execution Examples

Este documento fornece exemplos de como usar T-SQL (SQL Server) com a engine de execução de chains no Admin API Backend.

## Overview

O `chain_executor.py` foi melhorado para suportar:
- **T-SQL Blocks** com múltiplas statements (DECLARE, BEGIN/COMMIT, múltiplos SELECTs)
- **Raw connection** ao SQL Server para melhor compatibilidade com T-SQL
- **Multiple result sets** - retorna o último SELECT do bloco
- **Transações explícitas** - BEGIN TRANSACTION, COMMIT, ROLLBACK

## Exemplo 1: Incrementar Contador (Seu caso de uso)

### SQL T-SQL (Conforme você forneceu):
```sql
DECLARE @SEQ INT;
DECLARE @SERIE INT = 118;

BEGIN TRANSACTION;

UPDATE CNT WITH (ROWLOCK, UPDLOCK)
SET CNT_NUM = CNT_NUM + 1
WHERE CNT_TIPO = 'OSM' AND CNT_SERIE = @SERIE;

SELECT @SEQ = CNT_NUM
FROM CNT WITH (ROWLOCK, UPDLOCK)
WHERE CNT_TIPO = 'OSM' AND CNT_SERIE = @SERIE;

COMMIT TRANSACTION;

SELECT @SEQ AS cnt_num;
```

### Como usar no Business Object:

1. **Crie um Business Object** com:
   - **Nome**: "Incrementar contador OSM"
   - **Tipo de Comando**: `select` (porque o resultado final é um SELECT)
   - **SQL**: (codifique em Base64)

2. **Base64 encode** do SQL:
   ```bash
   # No terminal/PowerShell:
   # Windows: echo -n "DECLARE @SEQ INT;..." | certutil -encodehex -
   # Linux: echo -n "DECLARE @SEQ INT;..." | base64
   ```

3. **Configure na Chain** com parâmetros:
   ```json
   {
     "order": 1,
     "business_object_id": "seu-id",
     "business_object_name": "Incrementar contador OSM",
     "business_object_params": [
       {
         "name": "SERIE",
         "type": "int"
       }
     ],
     "parameter_mappings": [
       {
         "parameter_name": "SERIE",
         "source_type": "static",
         "static_value": 118
       }
     ]
   }
   ```

### O que acontece:

1. ✅ Detecta que é T-SQL block (começa com DECLARE)
2. ✅ Usa raw connection ao SQL Server
3. ✅ Executa TODO o bloco (transação, updates, selects)
4. ✅ Coleta todos os result sets
5. ✅ **Retorna o último SELECT** como resultado: `[{"cnt_num": 125}]`

## Exemplo 2: Validação com Múltiplos SELECTs

```sql
DECLARE @ID INT = :ID;
DECLARE @STATUS VARCHAR(50);
DECLARE @COUNT INT;

BEGIN TRANSACTION;

-- Primeiro SELECT: verificar se existe
SELECT @COUNT = COUNT(*)
FROM USUARIOS
WHERE ID = @ID;

-- Segundo SELECT: pegar dados
SELECT @STATUS = STATUS
FROM USUARIOS
WHERE ID = @ID;

-- Último SELECT: retornar resultado
SELECT
  @ID AS id,
  @STATUS AS status,
  @COUNT AS existe
AS resultado;

COMMIT TRANSACTION;
```

**Resultado retornado**: O último SELECT
```json
[
  {
    "id": 123,
    "status": "ATIVO",
    "existe": 1
  }
]
```

## Exemplo 3: Parâmetros Dinâmicos

```sql
DECLARE @TABELA VARCHAR(100) = ':TABELA';
DECLARE @CAMPO VARCHAR(100) = ':CAMPO';
DECLARE @VALOR VARCHAR(100) = ':VALOR';

BEGIN TRANSACTION;

-- INSERT dinâmico
DECLARE @SQL NVARCHAR(MAX) = 'INSERT INTO ' + @TABELA + ' (' + @CAMPO + ') VALUES (''' + @VALOR + ''')';
EXEC sp_executesql @SQL;

-- SELECT para confirmar
SELECT TOP 1 * FROM TABELA ORDER BY CREATED_AT DESC;

COMMIT TRANSACTION;
```

**Na Chain**:
```json
{
  "order": 1,
  "business_object_params": [
    {"name": "TABELA", "type": "string"},
    {"name": "CAMPO", "type": "string"},
    {"name": "VALOR", "type": "string"}
  ],
  "parameter_mappings": [
    {"parameter_name": "TABELA", "source_type": "static", "static_value": "usuarios"},
    {"parameter_name": "CAMPO", "source_type": "static", "static_value": "email"},
    {"parameter_name": "VALOR", "source_type": "variable", "variable_source": {"step_index": 0, "field_name": "email"}}
  ]
}
```

## Diagrama de Execução

```
┌─────────────────────────────────────────────────────┐
│ SQL executado (começa com DECLARE/BEGIN)           │
└────────────┬────────────────────────────────────────┘
             │
             ├─ Detecta T-SQL block
             │
             ├─ Create raw connection (não SQLAlchemy)
             │
             ├─ cursor.execute(full_sql)
             │
             ├─ Loop: enquanto cursor.nextset()
             │  ├─ Se tem colunas (SELECT)
             │  │  └─ Adiciona ao all_results
             │  └─ Próximo result set
             │
             └─ Retorna: all_results[-1]
                        (último SELECT)
```

## Tipos de Comando Suportados

| Tipo | Exemplo | Retorna |
|------|---------|---------|
| `select` | SELECT ... | Array de objetos com os dados |
| `insert` | INSERT ... | `{"insertedId": rowcount}` |
| `update` | UPDATE ... | `{"affectedRows": rowcount}` |
| `delete` | DELETE ... | `{"affectedRows": rowcount}` |

## Logs

Ao executar, você verá logs detalhados:

```
Detected T-SQL block with multiple statements, using raw connection
Raw connection created for T-SQL block execution
T-SQL block executed successfully
Fetching result set with columns: ['cnt_num']
Result set has 1 rows
Returning last result set from T-SQL block (1 total sets)
```

## Limitações

1. **Não suporta PL/pgSQL** (PostgreSQL) - use sintaxe PostgreSQL nativa
2. **Raw connection** pode não fazer pool de conexões - use com cuidado em alta concorrência
3. **Hints de lock** (WITH ROWLOCK) - apenas SQL Server, PostgreSQL usa sintaxe diferente
4. **Variáveis globais** (@@IDENTITY) - nem sempre funcionam em conexões paralelas

## Troubleshooting

### Erro: "This result object does not return rows"
- **Causa**: Tentar ler resultado após commit
- **Solução**: Já foi corrigido! Agora lê antes de commit

### Erro: "HY010 - Function sequence error"
- **Causa**: Executando T-SQL com múltiplos statements (UPDATE + SELECT)
- **O que acontecia**: SQLAlchemy tentava ler resultado set após UPDATE (que não retorna dados)
- **Solução**: Agora verifica `cursor.description` antes de tentar ler linhas
- **Como debug**: Veja os logs - você verá `"Result set has no columns (non-SELECT statement like UPDATE/DELETE)"`

Exemplo de log esperado:
```
Result set has no columns (non-SELECT statement like UPDATE/DELETE)
Moving to next result set
Fetching result set with columns: ['cnt_num']
Result set has 1 rows
Returning last result set from T-SQL block (2 total sets)
```

### Erro: "nextset() not available"
- **Causa**: Usando PostgreSQL com T-SQL syntax
- **Solução**: Converta para PL/pgSQL ou use SQL Server

### Parâmetros não substituídos
- **Verificar**: Nome dos parâmetros bate com `:NOME` no SQL?
- **Verificar**: Type correto no business_object_params?

### Erro: "pyodbc.Error - unixODBC"
- **Causa**: Usando unixODBC em Linux com SQL Server
- **Solução**:
  1. Instale ODBC driver: `apt-get install unixodbc odbcinst`
  2. Configure `/etc/odbcinst.ini` com o SQL Server driver
  3. Configure `/etc/odbc.ini` com a conexão
  4. Teste: `isql -v SEU_DSN_NAME usuario senha`
- **Alternative**: Use freetds driver se Microsoft ODBC não funcionar

## Exemplo Completo de Chain

```json
POST /api/v1/execute-chain

{
  "connection_id": "meu-sqlserver",
  "chain": [
    {
      "order": 1,
      "business_object_id": "bo-incrementar-contador",
      "business_object_name": "Incrementar contador",
      "business_object_params": [
        {"name": "SERIE", "type": "int"}
      ],
      "parameter_mappings": [
        {
          "parameter_name": "SERIE",
          "source_type": "static",
          "static_value": 118
        }
      ]
    }
  ]
}
```

**Resposta**:
```json
{
  "success": true,
  "steps": 1,
  "result": [
    {
      "cnt_num": 125
    }
  ],
  "allResults": [
    [
      {
        "cnt_num": 125
      }
    ]
  ]
}
```

## Dicas

1. **Sempre coloque o SELECT final** que contém os dados desejados
2. **Use variáveis** para passar valores entre statements
3. **Mantenha transações pequenas** para melhor performance
4. **Teste localmente** com SQL Server Management Studio primeiro
5. **Verifique logs** para debug - eles mostram exatamente o que foi executado

