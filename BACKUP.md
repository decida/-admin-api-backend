# Sistema de Backup - Database Connections

## Visão Geral

O sistema de backup gera scripts SQL completos da tabela `databases` usando a estratégia **INSERT ... ON CONFLICT** do PostgreSQL, que permite:

✅ **Inserir novos registros** se não existirem
✅ **Atualizar registros existentes** se o ID já existir
✅ **Segurança**: Não perde dados existentes
✅ **Idempotência**: Pode executar o mesmo backup múltiplas vezes

## Endpoints Disponíveis

### 1. GET /api/v1/databases/backup

Retorna backup em formato JSON com SQL codificado em base64.

**Resposta:**
```json
{
  "sql_base64": "LS0gPT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT...",
  "size_mb": 0.0025,
  "size_bytes": 2621,
  "total_records": 5,
  "format": "sql",
  "compression": "base64"
}
```

**Exemplo de uso:**
```bash
# Obter backup
curl http://localhost:8000/api/v1/databases/backup

# Decodificar base64 e salvar
curl http://localhost:8000/api/v1/databases/backup | \
  jq -r '.sql_base64' | \
  base64 -d > backup.sql
```

### 2. GET /api/v1/databases/backup/download

Faz download direto do arquivo SQL (sem base64).

**Headers de resposta:**
- `Content-Disposition`: Nome do arquivo com timestamp
- `X-Backup-Size-MB`: Tamanho em MB
- `X-Backup-Records`: Total de registros

**Exemplo de uso:**
```bash
# Download direto
curl -O -J http://localhost:8000/api/v1/databases/backup/download

# Resultado: databases_backup_20240101_143022.sql
```

## Formato do SQL Gerado

### Estrutura

O backup gera um SQL com:

1. **Cabeçalho informativo** com data e total de registros
2. **Criação do ENUM** `database_status` (se não existir)
3. **INSERT ... ON CONFLICT** para cada registro

### Exemplo de SQL Gerado

```sql
-- ===================================================================
-- Database Connections Backup
-- Generated: 2024-01-01 14:30:22
-- Total records: 5
-- ===================================================================

-- Ensure database_status enum exists
DO $$ BEGIN
    CREATE TYPE database_status AS ENUM ('active', 'inactive');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Backup record: My Database (my-database)
INSERT INTO databases (
    id, name, slug, type, connection_string, description, status, created_at, updated_at
) VALUES (
    '123e4567-e89b-12d3-a456-426614174000'::uuid,
    'My Database',
    'my-database',
    'sqlserver',
    'Server=myserver;Database=mydb;User Id=sa;Password=pass;',
    'Production database',
    'active'::database_status,
    '2024-01-01 10:00:00+00'::timestamp with time zone,
    '2024-01-01 14:00:00+00'::timestamp with time zone
)
ON CONFLICT (id) DO UPDATE SET
    name = 'My Database',
    slug = 'my-database',
    type = 'sqlserver',
    connection_string = 'Server=myserver;Database=mydb;User Id=sa;Password=pass;',
    description = 'Production database',
    status = 'active'::database_status,
    updated_at = '2024-01-01 14:00:00+00'::timestamp with time zone;

-- ===================================================================
-- Backup completed successfully
-- Total records processed: 5
-- ===================================================================
```

## Restaurando o Backup

### Método 1: Via psql (Recomendado)

```bash
# 1. Fazer backup
curl -O -J http://localhost:8000/api/v1/databases/backup/download

# 2. Restaurar
psql -h localhost -U admin -d admindb -f databases_backup_20240101_143022.sql
```

### Método 2: Via API (decodificando base64)

```bash
# 1. Obter e decodificar
curl http://localhost:8000/api/v1/databases/backup | \
  jq -r '.sql_base64' | \
  base64 -d > backup.sql

# 2. Restaurar
psql -h localhost -U admin -d admindb -f backup.sql
```

### Método 3: Via Docker

```bash
# 1. Download
curl -O -J http://localhost:8000/api/v1/databases/backup/download

# 2. Restaurar no container
docker exec -i admin-api-db psql -U admin -d admindb < databases_backup_20240101_143022.sql
```

## Segurança

### ⚠️ IMPORTANTE: O backup contém dados sensíveis!

O SQL inclui:
- **Connection strings** com credenciais de banco de dados
- **Senhas** em texto plano
- **Hosts e portas** de servidores

### Recomendações de Segurança

1. **Armazenar backups de forma segura**
   ```bash
   # Criptografar backup
   gpg --symmetric --cipher-algo AES256 backup.sql
   # Resultado: backup.sql.gpg

   # Descriptografar
   gpg --decrypt backup.sql.gpg > backup.sql
   ```

2. **Usar permissões restritas**
   ```bash
   chmod 600 backup.sql
   ```

3. **Nunca commitar backups no git**
   ```bash
   # Em .gitignore
   *.sql
   *_backup_*.sql
   ```

4. **Considerar autenticação no endpoint**
   - Adicionar middleware de autenticação
   - Limitar acesso por IP
   - Usar tokens de API

## Automação de Backups

### Cron Job (Linux/Mac)

```bash
# Editar crontab
crontab -e

# Adicionar linha (backup diário às 2 AM)
0 2 * * * curl -o /backups/databases_$(date +\%Y\%m\%d).sql http://localhost:8000/api/v1/databases/backup/download
```

### Task Scheduler (Windows)

```powershell
# PowerShell script: backup.ps1
$date = Get-Date -Format "yyyyMMdd_HHmmss"
$output = "C:\backups\databases_backup_$date.sql"
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/databases/backup/download" -OutFile $output
```

### Script Python

```python
import requests
from datetime import datetime
import base64

# Opção 1: Download direto
response = requests.get("http://localhost:8000/api/v1/databases/backup/download")
with open(f"backup_{datetime.now():%Y%m%d_%H%M%S}.sql", "w") as f:
    f.write(response.text)

# Opção 2: Via base64
response = requests.get("http://localhost:8000/api/v1/databases/backup")
data = response.json()
sql = base64.b64decode(data["sql_base64"]).decode("utf-8")
with open(f"backup_{datetime.now():%Y%m%d_%H%M%S}.sql", "w") as f:
    f.write(sql)

print(f"Backup criado: {data['size_mb']} MB, {data['total_records']} registros")
```

## Tamanho Estimado

### Cálculo por registro

Cada registro ocupa aproximadamente **500-1000 bytes**, dependendo de:
- Tamanho da connection string
- Tamanho da descrição
- Tamanho do nome

### Exemplos

| Registros | Tamanho estimado |
|-----------|------------------|
| 10 | ~10 KB |
| 100 | ~100 KB |
| 1.000 | ~1 MB |
| 10.000 | ~10 MB |
| 100.000 | ~100 MB |

## Monitoramento

### Ver tamanho antes de baixar

```bash
# Apenas informações (sem baixar SQL completo)
curl http://localhost:8000/api/v1/databases/backup | jq '{size_mb, size_bytes, total_records}'
```

**Resultado:**
```json
{
  "size_mb": 0.0025,
  "size_bytes": 2621,
  "total_records": 5
}
```

## Troubleshooting

### Erro: duplicate key value violates unique constraint "databases_pkey"

**Solução**: O SQL usa `ON CONFLICT` automaticamente. Este erro não deveria ocorrer.

### Erro: type "database_status" already exists

**Solução**: O SQL usa `DO $$ BEGIN ... EXCEPTION` para ignorar se o enum já existe.

### Backup muito grande

**Soluções**:
1. Filtrar por data ou status (implementar endpoint customizado)
2. Comprimir com gzip: `gzip backup.sql`
3. Particionar backups por período

### Restauração lenta

**Soluções**:
1. Usar `psql` com `-q` (quiet mode)
2. Desabilitar triggers temporariamente
3. Aumentar `maintenance_work_mem` do PostgreSQL
