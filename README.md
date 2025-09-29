# Admin API Backend

API backend desenvolvida com FastAPI, PostgreSQL e SQLAlchemy.

## Tecnologias

- **Python 3.11**
- **FastAPI** - Framework web moderno e rápido
- **SQLAlchemy 2.0** - ORM para banco de dados
- **PostgreSQL** - Banco de dados relacional
- **Poetry** - Gerenciamento de dependências
- **Docker & Docker Compose** - Containerização

## Estrutura do Projeto

```
.
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── endpoints/      # Endpoints da API
│   │       └── router.py       # Router principal da API v1
│   ├── core/
│   │   └── config.py          # Configurações da aplicação
│   ├── db/
│   │   ├── base.py            # Base declarativa do SQLAlchemy
│   │   └── session.py         # Sessão do banco de dados
│   ├── models/                # Modelos do SQLAlchemy
│   ├── schemas/               # Schemas Pydantic
│   └── main.py               # Ponto de entrada da aplicação
├── sql/                      # Scripts SQL para criação do banco
├── docker-compose.yml        # Configuração Docker Compose
├── Dockerfile               # Dockerfile da aplicação
└── pyproject.toml          # Dependências Poetry
```

## Configuração

### Pré-requisitos

- Python 3.11+
- Poetry
- PostgreSQL 15+
- Docker e Docker Compose (opcional)

### Variáveis de Ambiente

Copie o arquivo `.env.example` para `.env` e ajuste as variáveis conforme necessário:

```bash
cp .env.example .env
```

## Instalação e Execução

### 1. Instalar Dependências

```bash
poetry install
```

### 2. Configurar Banco de Dados

#### Opção A: Com Docker (Recomendado)

```bash
# Iniciar PostgreSQL
docker-compose up -d db

# Executar scripts SQL
docker exec -i admin-api-db psql -U admin -d admindb < sql/001_create_databases_table.sql
```

#### Opção B: PostgreSQL Local

```bash
# Via psql
psql -h localhost -U admin -d admindb -f sql/001_create_databases_table.sql

# Ou conectar e executar
psql -h localhost -U admin -d admindb
\i sql/001_create_databases_table.sql
```

### 3. Iniciar a API

#### Com Docker Compose

```bash
docker-compose up --build
```

#### Sem Docker

```bash
poetry run uvicorn app.main:app --reload
```

A API estará disponível em `http://localhost:8000`

## Scripts SQL

Todos os scripts SQL estão no diretório `sql/`. Consulte `sql/README.md` para instruções detalhadas.

- **001_create_databases_table.sql** - Cria estrutura completa (tabelas, enum, triggers)
- **999_drop_all.sql** - Remove toda estrutura (⚠️ apenas desenvolvimento)

## Comandos Úteis

### Desenvolvimento

```bash
# Iniciar servidor de desenvolvimento
poetry run uvicorn app.main:app --reload
# Ou
make run
```

### Testes

```bash
poetry run pytest
# Ou
make test
```

### Linting e Formatação

```bash
# Formatar código com Black
poetry run black app/

# Lint com Ruff
poetry run ruff check app/

# Type checking com MyPy
poetry run mypy app/

# Ou usar o Makefile
make format
make lint
```

## Documentação da API

Após iniciar o servidor, acesse:

- **Swagger UI**: http://localhost:8000/api/v1/docs
- **ReDoc**: http://localhost:8000/api/v1/redoc

## Exemplo de Uso

### Criar uma conexão de banco de dados

```bash
curl -X POST "http://localhost:8000/api/v1/databases/" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My SQLServer DB",
    "type": "sqlserver",
    "connection_string": "Server=myserver;Database=mydb;User Id=sa;Password=pass;",
    "description": "Production database",
    "status": "active"
  }'
```

### Listar todas as conexões

```bash
curl "http://localhost:8000/api/v1/databases/"
```

### Buscar por ID

```bash
curl "http://localhost:8000/api/v1/databases/{uuid}"
```

### Atualizar

```bash
curl -X PATCH "http://localhost:8000/api/v1/databases/{uuid}" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "inactive"
  }'
```

### Deletar

```bash
curl -X DELETE "http://localhost:8000/api/v1/databases/{uuid}"
```