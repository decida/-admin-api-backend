# Admin API Client - JavaScript/TypeScript

Cliente JavaScript para consumir a Admin API Backend. Suporta autenticação HTTP Basic e pode ser usado em projetos React, Vue, ou qualquer aplicação JavaScript moderna.

## 📦 Instalação

Copie os arquivos do diretório `client/` para seu projeto:

```
src/
├── api/
│   ├── api-client.js
│   └── types.d.ts (opcional, para TypeScript)
```

## 🚀 Uso Básico

### 1. Configuração Inicial

```javascript
import ApiClient from './api/api-client';

const apiClient = new ApiClient({
  baseURL: 'http://localhost:8000',
  username: 'admin',      // Opcional: para autenticação básica
  password: 'secret123',  // Opcional: para autenticação básica
  timeout: 30000,         // Opcional: timeout em ms (padrão: 30000)
});
```

### 2. Com Vite + React

Crie um arquivo `.env`:

```env
VITE_API_URL=http://localhost:8000
VITE_API_USERNAME=admin
VITE_API_PASSWORD=secret123
```

Use no código:

```javascript
const apiClient = new ApiClient({
  baseURL: import.meta.env.VITE_API_URL,
  username: import.meta.env.VITE_API_USERNAME,
  password: import.meta.env.VITE_API_PASSWORD,
});
```

## 📚 API Reference

### Health Check

```javascript
const health = await apiClient.healthCheck();
// { status: "healthy" }
```

### Databases

#### Listar todos

```javascript
const databases = await apiClient.listDatabases({ skip: 0, limit: 100 });
```

#### Buscar por ID

```javascript
const database = await apiClient.getDatabase('uuid-here');
```

#### Criar

```javascript
const newDatabase = await apiClient.createDatabase({
  name: 'My SQLServer',
  type: 'sqlserver',
  connection_string: 'Server=localhost;Database=mydb;User Id=sa;Password=pass;',
  description: 'Production database',
  status: 'active', // 'active' ou 'inactive'
});
```

#### Atualizar

```javascript
const updated = await apiClient.updateDatabase('uuid-here', {
  status: 'inactive',
  description: 'Updated description',
});
```

#### Deletar

```javascript
await apiClient.deleteDatabase('uuid-here');
```

## 🔐 Autenticação

### Configurar na inicialização

```javascript
const apiClient = new ApiClient({
  baseURL: 'http://localhost:8000',
  username: 'admin',
  password: 'secret123',
});
```

### Atualizar em runtime

```javascript
// Login
apiClient.setAuth('admin', 'newpassword');

// Logout
apiClient.clearAuth();
```

### Exemplo de formulário de login

```jsx
function LoginForm() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');

  const handleLogin = async (e) => {
    e.preventDefault();
    apiClient.setAuth(username, password);

    try {
      await apiClient.healthCheck();
      alert('Login bem-sucedido!');
    } catch (err) {
      alert('Falha no login');
      apiClient.clearAuth();
    }
  };

  return (
    <form onSubmit={handleLogin}>
      <input
        type="text"
        value={username}
        onChange={(e) => setUsername(e.target.value)}
      />
      <input
        type="password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
      />
      <button type="submit">Login</button>
    </form>
  );
}
```

## 🎣 Hook Customizado para React

```javascript
import { useState, useEffect } from 'react';
import ApiClient from './api-client';

const apiClient = new ApiClient({
  baseURL: import.meta.env.VITE_API_URL,
  username: import.meta.env.VITE_API_USERNAME,
  password: import.meta.env.VITE_API_PASSWORD,
});

function useDatabases() {
  const [databases, setDatabases] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchDatabases = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiClient.listDatabases();
      setDatabases(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const createDatabase = async (databaseData) => {
    setLoading(true);
    try {
      const newDb = await apiClient.createDatabase(databaseData);
      setDatabases((prev) => [...prev, newDb]);
      return newDb;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const updateDatabase = async (id, updates) => {
    const updated = await apiClient.updateDatabase(id, updates);
    setDatabases((prev) =>
      prev.map((db) => (db.id === id ? updated : db))
    );
    return updated;
  };

  const deleteDatabase = async (id) => {
    await apiClient.deleteDatabase(id);
    setDatabases((prev) => prev.filter((db) => db.id !== id));
  };

  useEffect(() => {
    fetchDatabases();
  }, []);

  return {
    databases,
    loading,
    error,
    refresh: fetchDatabases,
    createDatabase,
    updateDatabase,
    deleteDatabase,
  };
}

// Uso no componente
function DatabaseList() {
  const { databases, loading, error, createDatabase, deleteDatabase } = useDatabases();

  if (loading) return <div>Carregando...</div>;
  if (error) return <div>Erro: {error}</div>;

  return (
    <div>
      <h1>Databases ({databases.length})</h1>
      {databases.map((db) => (
        <div key={db.id}>
          <h3>{db.name}</h3>
          <p>{db.type} - {db.status}</p>
          <button onClick={() => deleteDatabase(db.id)}>Deletar</button>
        </div>
      ))}
    </div>
  );
}
```

## 🔧 Configuração Avançada

### Alterar URL base

```javascript
apiClient.setBaseURL('https://api.producao.com.br');
```

### Timeout customizado

```javascript
const apiClient = new ApiClient({
  baseURL: 'http://localhost:8000',
  timeout: 60000, // 60 segundos
});
```

## ⚠️ Tratamento de Erros

```javascript
try {
  const database = await apiClient.getDatabase('invalid-id');
} catch (error) {
  console.error('Status:', error.status);      // 404
  console.error('Mensagem:', error.message);   // "Database with id ... not found"
  console.error('Dados:', error.data);         // Objeto completo do erro
}
```

## 📘 TypeScript

O arquivo `types.d.ts` fornece tipos completos:

```typescript
import ApiClient, { Database, DatabaseCreate } from './api-client';

const apiClient = new ApiClient({
  baseURL: 'http://localhost:8000',
  username: 'admin',
  password: 'secret',
});

const database: Database = await apiClient.getDatabase('uuid');

const newDb: DatabaseCreate = {
  name: 'My DB',
  type: 'sqlserver',
  connection_string: 'connection-string',
  status: 'active',
};
```

## 📝 Exemplo Completo

Veja o arquivo `example-usage.jsx` para exemplos completos de:
- Hook customizado `useDatabases()`
- Componente de listagem completo
- Formulário de login
- Uso direto da API

## 🌐 CORS

Certifique-se de que a API está configurada para aceitar requisições do seu frontend:

```python
# app/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # URL do Vite
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## 📦 Build para Produção

O client é JavaScript puro e será bundled automaticamente pelo Vite/Webpack do seu projeto. Não requer configuração adicional.