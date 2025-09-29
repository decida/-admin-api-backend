/**
 * Admin API Client
 *
 * Client JavaScript para consumir a API Admin Backend
 * Suporta autenticação básica HTTP
 */

class ApiClient {
  /**
   * @param {Object} config - Configuração do cliente
   * @param {string} config.baseURL - URL base da API
   * @param {string} [config.username] - Usuário para autenticação básica
   * @param {string} [config.password] - Senha para autenticação básica
   * @param {number} [config.timeout=30000] - Timeout em milissegundos
   */
  constructor(config) {
    this.baseURL = config.baseURL || 'http://localhost:8000';
    this.username = config.username;
    this.password = config.password;
    this.timeout = config.timeout || 30000;
    this.apiPrefix = '/api/v1';
  }

  /**
   * Cria headers para requisição
   * @private
   */
  _getHeaders() {
    const headers = {
      'Content-Type': 'application/json',
    };

    // Adiciona autenticação básica se credenciais foram fornecidas
    if (this.username && this.password) {
      const credentials = btoa(`${this.username}:${this.password}`);
      headers['Authorization'] = `Basic ${credentials}`;
    }

    return headers;
  }

  /**
   * Faz requisição HTTP
   * @private
   */
  async _request(method, endpoint, data = null) {
    const url = `${this.baseURL}${this.apiPrefix}${endpoint}`;

    const config = {
      method,
      headers: this._getHeaders(),
      signal: AbortSignal.timeout(this.timeout),
    };

    if (data && (method === 'POST' || method === 'PATCH' || method === 'PUT')) {
      config.body = JSON.stringify(data);
    }

    try {
      const response = await fetch(url, config);

      // Para DELETE com 204, retorna sucesso sem body
      if (response.status === 204) {
        return { success: true };
      }

      const responseData = await response.json();

      if (!response.ok) {
        throw {
          status: response.status,
          message: responseData.detail || 'Erro na requisição',
          data: responseData,
        };
      }

      return responseData;
    } catch (error) {
      if (error.name === 'TimeoutError') {
        throw {
          status: 0,
          message: 'Timeout na requisição',
          error,
        };
      }
      throw error;
    }
  }

  /**
   * Health Check
   */
  async healthCheck() {
    const url = `${this.baseURL}/health`;
    const response = await fetch(url);
    return response.json();
  }

  // ==================== Database Endpoints ====================

  /**
   * Lista todas as conexões de banco de dados
   * @param {Object} [params] - Parâmetros de paginação
   * @param {number} [params.skip=0] - Quantos registros pular
   * @param {number} [params.limit=100] - Limite de registros
   * @returns {Promise<Array>}
   */
  async listDatabases(params = {}) {
    const { skip = 0, limit = 100 } = params;
    const endpoint = `/databases/?skip=${skip}&limit=${limit}`;
    return this._request('GET', endpoint);
  }

  /**
   * Busca uma conexão de banco de dados por ID
   * @param {string} id - UUID da conexão
   * @returns {Promise<Object>}
   */
  async getDatabase(id) {
    return this._request('GET', `/databases/${id}`);
  }

  /**
   * Cria uma nova conexão de banco de dados
   * @param {Object} data - Dados da conexão
   * @param {string} data.name - Nome da conexão
   * @param {string} data.type - Tipo do banco (ex: 'sqlserver', 'postgresql')
   * @param {string} data.connection_string - String de conexão
   * @param {string} [data.description] - Descrição
   * @param {string} [data.status='active'] - Status ('active' ou 'inactive')
   * @returns {Promise<Object>}
   */
  async createDatabase(data) {
    return this._request('POST', '/databases/', data);
  }

  /**
   * Atualiza uma conexão de banco de dados
   * @param {string} id - UUID da conexão
   * @param {Object} data - Dados para atualizar
   * @returns {Promise<Object>}
   */
  async updateDatabase(id, data) {
    return this._request('PATCH', `/databases/${id}`, data);
  }

  /**
   * Deleta uma conexão de banco de dados
   * @param {string} id - UUID da conexão
   * @returns {Promise<Object>}
   */
  async deleteDatabase(id) {
    return this._request('DELETE', `/databases/${id}`);
  }

  // ==================== Métodos auxiliares ====================

  /**
   * Atualiza credenciais de autenticação
   * @param {string} username - Novo usuário
   * @param {string} password - Nova senha
   */
  setAuth(username, password) {
    this.username = username;
    this.password = password;
  }

  /**
   * Remove autenticação
   */
  clearAuth() {
    this.username = null;
    this.password = null;
  }

  /**
   * Atualiza a URL base
   * @param {string} baseURL - Nova URL base
   */
  setBaseURL(baseURL) {
    this.baseURL = baseURL;
  }
}

// Export para uso em módulos ES6
export default ApiClient;

// Export para uso em CommonJS (Node.js)
if (typeof module !== 'undefined' && module.exports) {
  module.exports = ApiClient;
}