#!/bin/bash
# Exemplos de requisições para testar a API de Business Objects com Parâmetros

BASE_URL="http://localhost:8000/api/v1/business-objects"

echo "=================================="
echo "1. Criar Business Object com Parâmetros"
echo "=================================="

# SQL: SELECT * FROM users WHERE status = :status AND created_at > :startDate
SQL_BASE64="U0VMRUNUICogRlJPTSB1c2VycyBXSEVSRSBzdGF0dXMgPSA6c3RhdHVzIEFORCBjcmVhdGVkX2F0ID4gOnN0YXJ0RGF0ZQ=="

curl -X POST "$BASE_URL" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Usuários Ativos",
    "command_type": "select",
    "sqlCommand": "'"$SQL_BASE64"'",
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
  }'

echo -e "\n\n=================================="
echo "2. Criar Business Object SEM Parâmetros (válido)"
echo "=================================="

# SQL: SELECT * FROM users
SQL_NO_PARAMS="U0VMRUNUICogRlJPTSB1c2Vycw=="

curl -X POST "$BASE_URL" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Todos os Usuários",
    "command_type": "select",
    "sqlCommand": "'"$SQL_NO_PARAMS"'",
    "params": [],
    "tags": ["users"]
  }'

echo -e "\n\n=================================="
echo "3. Criar Business Object com Parâmetro Faltando (erro esperado)"
echo "=================================="

# SQL: SELECT * FROM users WHERE id = :userId AND status = :status
SQL_MISSING="U0VMRUNUICogRlJPTSB1c2VycyBXSEVSRSBpZCA9IDp1c2VySWQgQU5EIHN0YXR1cyA9IDpzdGF0dXM="

curl -X POST "$BASE_URL" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Usuário por ID (inválido)",
    "command_type": "select",
    "sqlCommand": "'"$SQL_MISSING"'",
    "params": [
      {
        "name": "userId",
        "type": "number",
        "required": true
      }
    ],
    "tags": ["users"]
  }'

echo -e "\n\n=================================="
echo "4. Criar Business Object com Parâmetro Não Usado (erro esperado)"
echo "=================================="

# SQL: SELECT * FROM users
SQL_UNUSED="U0VMRUNUICogRlJPTSB1c2Vycw=="

curl -X POST "$BASE_URL" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Todos os Usuários (inválido)",
    "command_type": "select",
    "sqlCommand": "'"$SQL_UNUSED"'",
    "params": [
      {
        "name": "userId",
        "type": "number",
        "required": true
      }
    ],
    "tags": ["users"]
  }'

echo -e "\n\n=================================="
echo "5. Listar Todos os Business Objects"
echo "=================================="

curl -X GET "$BASE_URL"

echo -e "\n\n=================================="
echo "6. Atualizar Parâmetros de um Business Object"
echo "=================================="
echo "Substitua {id} pelo ID retornado na criação"
echo "=================================="

# SQL atualizado: SELECT * FROM users WHERE status = :status
SQL_UPDATED="U0VMRUNUICogRlJPTSB1c2VycyBXSEVSRSBzdGF0dXMgPSA6c3RhdHVz"

# Exemplo (não executado - precisa do ID):
cat << 'EOF'
curl -X PATCH "$BASE_URL/{id}" \
  -H "Content-Type: application/json" \
  -d '{
    "sqlCommand": "U0VMRUNUICogRlJPTSB1c2VycyBXSEVSRSBzdGF0dXMgPSA6c3RhdHVz",
    "params": [
      {
        "name": "status",
        "type": "string",
        "required": true,
        "defaultValue": "active"
      }
    ]
  }'
EOF

echo -e "\n\n=================================="
echo "Comandos para gerar BASE64"
echo "=================================="

echo "# Linux/Mac:"
echo 'echo -n "SELECT * FROM users WHERE status = :status" | base64'

echo ""
echo "# Windows PowerShell:"
echo '[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes("SELECT * FROM users WHERE status = :status"))'

echo ""
echo "# Python:"
echo 'import base64; base64.b64encode(b"SELECT * FROM users WHERE status = :status").decode()'

echo -e "\n=================================="
