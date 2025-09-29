# SQL Scripts

Scripts SQL para criação e gerenciamento do banco de dados.

## Ordem de Execução

### Criar Estrutura do Banco

Execute os scripts na seguinte ordem:

1. **001_create_databases_table.sql** - Cria tabela databases com enum e triggers

### Como Executar

#### Opção 1: Via psql (linha de comando)

```bash
# Conectar ao banco
psql -h localhost -U admin -d admindb

# Executar script
\i sql/001_create_databases_table.sql

# Ou executar diretamente
psql -h localhost -U admin -d admindb -f sql/001_create_databases_table.sql
```

#### Opção 2: Via Docker

```bash
# Copiar script para o container
docker cp sql/001_create_databases_table.sql admin-api-db:/tmp/

# Executar no container
docker exec -i admin-api-db psql -U admin -d admindb -f /tmp/001_create_databases_table.sql

# Ou diretamente via stdin
docker exec -i admin-api-db psql -U admin -d admindb < sql/001_create_databases_table.sql
```

#### Opção 3: Via cliente SQL (DBeaver, pgAdmin, etc.)

Abra o arquivo SQL e execute no seu cliente preferido.

## Scripts Disponíveis

- **001_create_databases_table.sql**: Cria a estrutura completa
  - Enum `database_status` (active, inactive)
  - Tabela `databases` com UUID auto-gerado
  - Índices
  - Trigger para atualizar `updated_at` automaticamente

- **999_drop_all.sql**: Remove toda a estrutura (⚠️ CUIDADO - uso apenas em desenvolvimento)

## Verificar Estrutura

```sql
-- Ver tabelas
\dt

-- Ver tipos enum
\dT+

-- Ver estrutura da tabela databases
\d databases

-- Ver triggers
\dy
```