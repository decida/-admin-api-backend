/**
 * Exemplos de uso do API Client em React
 */

import { useState, useEffect } from 'react';
import ApiClient from './api-client';

// ==================== Configuração do Client ====================

// Inicializar o client
const apiClient = new ApiClient({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  username: import.meta.env.VITE_API_USERNAME,
  password: import.meta.env.VITE_API_PASSWORD,
  timeout: 30000,
});

// ==================== Exemplo 1: Hook customizado ====================

/**
 * Hook para gerenciar lista de databases
 */
function useDatabases() {
  const [databases, setDatabases] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchDatabases = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiClient.listDatabases({ skip: 0, limit: 100 });
      setDatabases(data);
    } catch (err) {
      setError(err.message);
      console.error('Erro ao buscar databases:', err);
    } finally {
      setLoading(false);
    }
  };

  const createDatabase = async (databaseData) => {
    setLoading(true);
    setError(null);
    try {
      const newDatabase = await apiClient.createDatabase(databaseData);
      setDatabases((prev) => [...prev, newDatabase]);
      return newDatabase;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const updateDatabase = async (id, updates) => {
    setLoading(true);
    setError(null);
    try {
      const updated = await apiClient.updateDatabase(id, updates);
      setDatabases((prev) =>
        prev.map((db) => (db.id === id ? updated : db))
      );
      return updated;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const deleteDatabase = async (id) => {
    setLoading(true);
    setError(null);
    try {
      await apiClient.deleteDatabase(id);
      setDatabases((prev) => prev.filter((db) => db.id !== id));
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
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

// ==================== Exemplo 2: Componente de Listagem ====================

function DatabaseList() {
  const { databases, loading, error, createDatabase, updateDatabase, deleteDatabase } =
    useDatabases();

  const handleCreate = async () => {
    try {
      await createDatabase({
        name: 'New Database',
        type: 'sqlserver',
        connection_string: 'Server=localhost;Database=test;',
        description: 'Test database',
        status: 'active',
      });
      alert('Database criado com sucesso!');
    } catch (err) {
      alert('Erro ao criar database: ' + err.message);
    }
  };

  const handleToggleStatus = async (database) => {
    try {
      const newStatus = database.status === 'active' ? 'inactive' : 'active';
      await updateDatabase(database.id, { status: newStatus });
    } catch (err) {
      alert('Erro ao atualizar status: ' + err.message);
    }
  };

  const handleDelete = async (id) => {
    if (confirm('Tem certeza que deseja deletar?')) {
      try {
        await deleteDatabase(id);
        alert('Database deletado com sucesso!');
      } catch (err) {
        alert('Erro ao deletar: ' + err.message);
      }
    }
  };

  if (loading) return <div>Carregando...</div>;
  if (error) return <div>Erro: {error}</div>;

  return (
    <div>
      <h1>Databases</h1>
      <button onClick={handleCreate}>Criar Novo Database</button>

      <table>
        <thead>
          <tr>
            <th>Nome</th>
            <th>Tipo</th>
            <th>Status</th>
            <th>Descrição</th>
            <th>Ações</th>
          </tr>
        </thead>
        <tbody>
          {databases.map((db) => (
            <tr key={db.id}>
              <td>{db.name}</td>
              <td>{db.type}</td>
              <td>
                <span
                  style={{
                    color: db.status === 'active' ? 'green' : 'red',
                  }}
                >
                  {db.status}
                </span>
              </td>
              <td>{db.description || '-'}</td>
              <td>
                <button onClick={() => handleToggleStatus(db)}>
                  Toggle Status
                </button>
                <button onClick={() => handleDelete(db.id)}>Deletar</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ==================== Exemplo 3: Uso direto (sem hooks) ====================

async function directUsageExample() {
  try {
    // Health check
    const health = await apiClient.healthCheck();
    console.log('API Status:', health);

    // Listar databases
    const databases = await apiClient.listDatabases({ skip: 0, limit: 10 });
    console.log('Databases:', databases);

    // Criar database
    const newDb = await apiClient.createDatabase({
      name: 'Production DB',
      type: 'sqlserver',
      connection_string: 'Server=prod.example.com;Database=proddb;',
      description: 'Production database',
      status: 'active',
    });
    console.log('Created:', newDb);

    // Buscar por ID
    const db = await apiClient.getDatabase(newDb.id);
    console.log('Retrieved:', db);

    // Atualizar
    const updated = await apiClient.updateDatabase(newDb.id, {
      description: 'Updated description',
    });
    console.log('Updated:', updated);

    // Deletar
    await apiClient.deleteDatabase(newDb.id);
    console.log('Deleted successfully');
  } catch (error) {
    console.error('Error:', error);
  }
}

// ==================== Exemplo 4: Atualizar credenciais em runtime ====================

function LoginForm() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');

  const handleLogin = async (e) => {
    e.preventDefault();

    // Atualizar credenciais do client
    apiClient.setAuth(username, password);

    try {
      // Testar conexão
      await apiClient.healthCheck();
      alert('Login bem-sucedido!');
    } catch (err) {
      alert('Falha no login: ' + err.message);
      apiClient.clearAuth();
    }
  };

  return (
    <form onSubmit={handleLogin}>
      <input
        type="text"
        placeholder="Username"
        value={username}
        onChange={(e) => setUsername(e.target.value)}
      />
      <input
        type="password"
        placeholder="Password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
      />
      <button type="submit">Login</button>
    </form>
  );
}

// ==================== Exports ====================

export default DatabaseList;
export { useDatabases, apiClient, directUsageExample, LoginForm };