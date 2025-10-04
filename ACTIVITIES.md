## 🎉 Sistema de Activities/Audit Log Criado!

Estrutura completa para armazenar logs de auditoria e atividades de usuários.

### 📋 Estrutura da Tabela

```sql
CREATE TABLE activities (
    id BIGSERIAL PRIMARY KEY,
    action VARCHAR(255) NOT NULL,
    item VARCHAR(500) NOT NULL,
    icon activity_icon NOT NULL DEFAULT 'info',
    color activity_color NOT NULL DEFAULT 'blue',
    user_email VARCHAR(255),
    user_id UUID,
    extra_data JSONB,
    ip_address INET,
    user_agent TEXT,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
```

### 🎨 Enums Disponíveis

**Icons (activity_icon):**
- `database`, `edit`, `delete`, `add`, `user`, `settings`
- `upload`, `download`, `sync`
- `warning`, `error`, `success`, `info`

**Colors (activity_color):**
- `blue`, `green`, `red`, `yellow`, `purple`, `orange`, `gray`, `indigo`, `pink`

### 🚀 Endpoints da API

#### 1. GET /api/v1/activities

Listar atividades com paginação e filtros.

```bash
# Todas atividades (50 mais recentes)
curl http://localhost:8000/api/v1/activities/

# Com filtros
curl "http://localhost:8000/api/v1/activities/?user_email=user@example.com&limit=100"

# Buscar por ação específica
curl "http://localhost:8000/api/v1/activities/?action=Created"
```

**Resposta:**
```json
{
  "activities": [
    {
      "id": 1,
      "action": "Created database connection",
      "item": "Production DB",
      "icon": "database",
      "color": "blue",
      "user_email": "user@example.com",
      "user_id": null,
      "extra_data": {"database_type": "sqlserver"},
      "ip_address": "192.168.1.100",
      "user_agent": "Mozilla/5.0...",
      "timestamp": "2024-01-01T10:00:00Z",
      "created_at": "2024-01-01T10:00:00Z"
    }
  ],
  "total": 150,
  "skip": 0,
  "limit": 50,
  "has_more": true
}
```

#### 2. GET /api/v1/activities/stats

Estatísticas de atividades.

```bash
curl http://localhost:8000/api/v1/activities/stats
```

**Resposta:**
```json
{
  "total_activities": 1500,
  "activities_today": 45,
  "activities_this_week": 320,
  "activities_this_month": 890,
  "most_active_user": "admin@example.com",
  "most_common_action": "Created database connection"
}
```

#### 3. GET /api/v1/activities/{id}

Buscar atividade específica por ID.

```bash
curl http://localhost:8000/api/v1/activities/123
```

#### 4. POST /api/v1/activities

Criar nova atividade.

```bash
curl -X POST http://localhost:8000/api/v1/activities/ \
  -H "Content-Type: application/json" \
  -d '{
    "action": "Updated database settings",
    "item": "Production DB",
    "icon": "edit",
    "color": "green",
    "user_email": "user@example.com",
    "extra_data": {
      "fields_changed": ["connection_string"],
      "reason": "New credentials"
    }
  }'
```

**Nota:** IP address e User-Agent são capturados automaticamente!

#### 5. DELETE /api/v1/activities/{id}

Deletar atividade específica.

```bash
curl -X DELETE http://localhost:8000/api/v1/activities/123
```

#### 6. DELETE /api/v1/activities?days=90

Limpar atividades antigas (GDPR compliance).

```bash
# Deletar atividades com mais de 90 dias
curl -X DELETE "http://localhost:8000/api/v1/activities/?days=90"

# Deletar atividades com mais de 30 dias
curl -X DELETE "http://localhost:8000/api/v1/activities/?days=30"
```

### 💻 Uso Programático

#### Python (usando helper functions)

```python
from app.utils.activity_logger import (
    log_database_created,
    log_database_updated,
    log_database_deleted,
    log_backup_created,
)

# Ao criar database
log_database_created(
    db=db,
    database_name="Production DB",
    user_email="user@example.com",
    extra_data={"type": "sqlserver", "status": "active"}
)

# Ao atualizar database
log_database_updated(
    db=db,
    database_name="Production DB",
    user_email="admin@example.com",
    extra_data={"fields_changed": ["connection_string"]}
)

# Ao deletar database
log_database_deleted(
    db=db,
    database_name="Test DB",
    user_email="admin@example.com",
    extra_data={"reason": "no longer needed"}
)

# Ao criar backup
log_backup_created(
    db=db,
    backup_size_mb=2.5,
    total_records=150,
    user_email="admin@example.com"
)
```

#### Logging genérico

```python
from app.utils.activity_logger import log_activity
from app.models.activity import ActivityIcon, ActivityColor

log_activity(
    db=db,
    action="Custom action performed",
    item="Item name",
    icon=ActivityIcon.settings,
    color=ActivityColor.purple,
    user_email="user@example.com",
    extra_data={"custom_field": "value"}
)
```

### 🎨 Frontend Integration

Mapeando para o formato do seu componente:

```javascript
// Buscar atividades da API
const response = await fetch('http://localhost:8000/api/v1/activities/');
const data = await response.json();

// Formatar para o componente
const formattedActivities = data.activities.map((activity, index) => ({
  id: activity.id,  // Usar ID real do banco ao invés de index
  action: activity.action,
  item: activity.item,
  time: formatRelativeTime(activity.timestamp),
  icon: getIconComponent(activity.icon),
  color: activity.color,
  userEmail: activity.user_email
}));
```

**Helper para ícones:**
```javascript
function getIconComponent(iconName) {
  const iconMap = {
    'database': DatabaseIcon,
    'edit': EditIcon,
    'delete': DeleteIcon,
    'add': AddIcon,
    'user': UserIcon,
    'settings': SettingsIcon,
    'upload': UploadIcon,
    'download': DownloadIcon,
    'sync': SyncIcon,
    'warning': WarningIcon,
    'error': ErrorIcon,
    'success': SuccessIcon,
    'info': InfoIcon
  };
  return iconMap[iconName] || InfoIcon;
}
```

**Helper para tempo relativo:**
```javascript
function formatRelativeTime(timestamp) {
  const now = new Date();
  const then = new Date(timestamp);
  const seconds = Math.floor((now - then) / 1000);

  if (seconds < 60) return 'just now';
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  if (seconds < 604800) return `${Math.floor(seconds / 86400)}d ago`;
  return then.toLocaleDateString();
}
```

### 📊 Índices para Performance

A tabela possui índices em:
- `timestamp` (DESC) - para queries ordenadas por data
- `user_email` - para filtrar por usuário
- `user_id` - para filtrar por UUID de usuário
- `action` - para filtrar por tipo de ação
- `extra_data` (GIN) - para busca no JSON

### 🔧 Instalação

```bash
# 1. Executar script SQL
docker exec -i admin-api-db psql -U admin -d admindb < sql/003_create_activities_table.sql

# Ou localmente
psql -h localhost -U admin -d admindb -f sql/003_create_activities_table.sql

# 2. Reiniciar API (já está tudo configurado!)
```

### 📁 Arquivos Criados

1. **`sql/003_create_activities_table.sql`** - Script de criação da tabela
2. **`app/models/activity.py`** - Modelo SQLAlchemy
3. **`app/schemas/activity.py`** - Schemas Pydantic (request/response)
4. **`app/api/v1/endpoints/activities.py`** - Endpoints da API
5. **`app/utils/activity_logger.py`** - Helper functions para logging
6. **`ACTIVITIES.md`** - Esta documentação

### 🎯 Exemplo Completo

```python
# No endpoint de criação de database
from app.utils.activity_logger import log_database_created

@router.post("/")
async def create_database(database_in: DatabaseCreate, db: Session = Depends(get_db)):
    # ... código de criação ...

    # Log da atividade
    log_database_created(
        db=db,
        database_name=database.name,
        user_email="user@example.com",  # Pegar do JWT/session
        extra_data={
            "slug": database.slug,
            "type": database.type,
            "status": database.status.value
        }
    )

    return database
```

### 🔐 GDPR Compliance

Limpeza automática de logs antigos:

```python
# Script de limpeza (pode ser agendado)
import requests

# Deletar atividades com mais de 90 dias
requests.delete("http://localhost:8000/api/v1/activities/?days=90")
```

### 🎨 Cores Recomendadas por Tipo de Ação

| Ação | Cor | Ícone |
|------|-----|-------|
| Criar | blue | database/add |
| Editar | green | edit |
| Deletar | red | delete |
| Erro | red | error |
| Aviso | yellow | warning |
| Sucesso | green | success |
| Backup | purple | download |
| Upload | indigo | upload |
| Sync | orange | sync |

**Tudo pronto para usar! 🚀**
