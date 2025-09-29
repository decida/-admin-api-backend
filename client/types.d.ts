/**
 * TypeScript Type Definitions for Admin API Client
 */

export type DatabaseStatus = 'active' | 'inactive';

export interface Database {
  id: string;
  name: string;
  type: string;
  connection_string: string;
  description?: string | null;
  status: DatabaseStatus;
  created_at: string;
  updated_at: string;
}

export interface DatabaseCreate {
  name: string;
  type: string;
  connection_string: string;
  description?: string | null;
  status?: DatabaseStatus;
}

export interface DatabaseUpdate {
  name?: string;
  type?: string;
  connection_string?: string;
  description?: string | null;
  status?: DatabaseStatus;
}

export interface ApiClientConfig {
  baseURL: string;
  username?: string;
  password?: string;
  timeout?: number;
}

export interface ApiError {
  status: number;
  message: string;
  data?: any;
}

export interface HealthCheckResponse {
  status: string;
}

export interface ListParams {
  skip?: number;
  limit?: number;
}

export default class ApiClient {
  constructor(config: ApiClientConfig);

  healthCheck(): Promise<HealthCheckResponse>;

  // Database methods
  listDatabases(params?: ListParams): Promise<Database[]>;
  getDatabase(id: string): Promise<Database>;
  createDatabase(data: DatabaseCreate): Promise<Database>;
  updateDatabase(id: string, data: DatabaseUpdate): Promise<Database>;
  deleteDatabase(id: string): Promise<{ success: boolean }>;

  // Auth methods
  setAuth(username: string, password: string): void;
  clearAuth(): void;
  setBaseURL(baseURL: string): void;
}