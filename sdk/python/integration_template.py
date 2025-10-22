"""
Integration Template for Admin API SDK
Copy this template to your project and customize as needed
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass
from functools import lru_cache

from admin_api_sdk import (
    AdminAPIClient,
    AdminAPIError,
    ConnectionError,
    ResourceNotFoundError,
    ExecutionError,
)


# ============================================================================
# Configuration
# ============================================================================

@dataclass
class Config:
    """Configuration for Admin API integration"""
    admin_api_url: str = "http://localhost:8000"
    admin_api_key: Optional[str] = None
    timeout: int = 30
    cache_resources: bool = True


# ============================================================================
# Singleton Client Instance
# ============================================================================

_client_instance: Optional[AdminAPIClient] = None


def get_admin_api_client(config: Optional[Config] = None) -> AdminAPIClient:
    """
    Get singleton instance of Admin API client.

    Usage:
        client = get_admin_api_client()
        resources = client.list_resources()
    """
    global _client_instance

    if _client_instance is None:
        if config is None:
            config = Config()

        _client_instance = AdminAPIClient(
            base_url=config.admin_api_url,
            timeout=config.timeout,
            api_key=config.admin_api_key
        )

    return _client_instance


# ============================================================================
# Service Layer - Wrapper around SDK
# ============================================================================

class AdminAPIService:
    """
    Service layer that wraps Admin API SDK with additional business logic.

    This is where you add:
    - Caching
    - Logging
    - Error handling
    - Business validations
    - Transformations
    """

    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()
        self.client = get_admin_api_client(config)
        self._resource_cache: Dict[str, Any] = {}

    # === Resource Management ===

    @lru_cache(maxsize=128)
    def get_resource_by_path(self, path: str):
        """
        Get resource by path with caching.
        Cache is cleared on any resource modification.
        """
        return self.client.get_resource_by_path(path)

    def clear_cache(self):
        """Clear resource cache"""
        self._resource_cache.clear()
        self.get_resource_by_path.cache_clear()

    # === Execution Methods ===

    def execute_resource(
        self,
        path: str,
        connection_id: str,
        parameters: Optional[Dict[str, Any]] = None,
        validate: bool = True
    ) -> Dict[str, Any]:
        """
        Execute resource with additional validation and error handling.

        Args:
            path: Resource path
            connection_id: Database connection ID
            parameters: Parameters for execution
            validate: Whether to validate parameters before execution

        Returns:
            Standardized response dict

        Raises:
            ValueError: If validation fails
            AdminAPIError: If execution fails
        """
        # Pre-execution validation
        if validate:
            resource = self.get_resource_by_path(path)
            if not resource:
                raise ValueError(f"Resource not found: {path}")

            if not resource.is_active:
                raise ValueError(f"Resource is inactive: {path}")

            self._validate_parameters(resource, parameters or {})

        # Execute
        try:
            result = self.client.execute(path, connection_id, parameters)

            # Transform to standardized response
            return self._standardize_response(result)

        except ExecutionError as e:
            # Log error (add your logging here)
            print(f"Execution error: {e.message}")
            raise

        except ConnectionError as e:
            # Log error (add your logging here)
            print(f"Connection error: {e.message}")
            raise

    def _validate_parameters(self, resource, parameters: Dict[str, Any]):
        """Validate parameters against resource definition"""
        for param in resource.business_object_params:
            if param.required and param.name not in parameters:
                raise ValueError(
                    f"Required parameter missing: {param.name}"
                )

    def _standardize_response(self, result) -> Dict[str, Any]:
        """
        Standardize response format.

        Your backend might have a specific response format.
        Transform SDK response to match your format here.
        """
        # Check if it's a chain result
        if hasattr(result, 'steps'):
            return {
                "success": result.success,
                "type": "chain",
                "steps": result.steps,
                "data": result.result,
                "all_results": result.all_results,
                "error": result.error.message if result.error else None
            }
        else:
            return {
                "success": result.success,
                "type": "single",
                "data": result.rows,
                "count": result.row_count,
                "error": result.error
            }

    # === Convenience Methods ===

    def health_check(self) -> bool:
        """Check if Admin API is healthy"""
        return self.client.health_check()

    def list_active_resources(self):
        """List all active resources"""
        return self.client.get_active_resources()


# ============================================================================
# Domain-Specific Services (Example)
# ============================================================================

class PacienteService:
    """
    Domain-specific service for patient operations.

    This layer adds business logic specific to your domain.
    """

    def __init__(self, admin_service: AdminAPIService):
        self.admin = admin_service

    def consultar_por_cpf(self, cpf: str, connection_id: str) -> Dict[str, Any]:
        """Query patient by CPF"""
        # Add business validations
        if not self._validate_cpf(cpf):
            raise ValueError("Invalid CPF format")

        # Execute resource
        return self.admin.execute_resource(
            path="/api/v1/consultar-paciente",
            connection_id=connection_id,
            parameters={"cpf": cpf}
        )

    def listar_agendamentos(
        self,
        paciente_id: int,
        connection_id: str
    ) -> Dict[str, Any]:
        """List patient appointments"""
        return self.admin.execute_resource(
            path="/api/v1/listar-agendamentos",
            connection_id=connection_id,
            parameters={"pacienteId": paciente_id}
        )

    @staticmethod
    def _validate_cpf(cpf: str) -> bool:
        """Validate CPF format (simplified)"""
        return len(cpf.replace(".", "").replace("-", "")) == 11


# ============================================================================
# Flask Integration Example
# ============================================================================

def create_flask_app():
    """Example Flask app using the SDK"""
    from flask import Flask, request, jsonify

    app = Flask(__name__)

    # Initialize services
    config = Config()
    admin_service = AdminAPIService(config)
    paciente_service = PacienteService(admin_service)

    @app.route("/health")
    def health():
        """Health check endpoint"""
        api_healthy = admin_service.health_check()
        return jsonify({
            "status": "healthy" if api_healthy else "degraded",
            "admin_api": "up" if api_healthy else "down"
        })

    @app.route("/paciente/<cpf>")
    def get_paciente(cpf):
        """Get patient by CPF"""
        try:
            connection_id = request.headers.get("X-Connection-ID")
            if not connection_id:
                return jsonify({"error": "Connection ID required"}), 400

            result = paciente_service.consultar_por_cpf(cpf, connection_id)
            return jsonify(result)

        except ValueError as e:
            return jsonify({"error": str(e)}), 400

        except AdminAPIError as e:
            return jsonify({"error": e.message}), 500

    @app.route("/resources")
    def list_resources():
        """List active resources"""
        try:
            resources = admin_service.list_active_resources()
            return jsonify({
                "resources": [
                    {
                        "id": str(r.id),
                        "path": r.path,
                        "description": r.description
                    }
                    for r in resources
                ]
            })
        except AdminAPIError as e:
            return jsonify({"error": e.message}), 500

    return app


# ============================================================================
# FastAPI Integration Example
# ============================================================================

def create_fastapi_app():
    """Example FastAPI app using the SDK"""
    from fastapi import FastAPI, HTTPException, Header
    from pydantic import BaseModel

    app = FastAPI()

    # Initialize services
    config = Config()
    admin_service = AdminAPIService(config)
    paciente_service = PacienteService(admin_service)

    class HealthResponse(BaseModel):
        status: str
        admin_api: str

    @app.get("/health", response_model=HealthResponse)
    async def health():
        """Health check endpoint"""
        api_healthy = admin_service.health_check()
        return {
            "status": "healthy" if api_healthy else "degraded",
            "admin_api": "up" if api_healthy else "down"
        }

    @app.get("/paciente/{cpf}")
    async def get_paciente(cpf: str, x_connection_id: str = Header(...)):
        """Get patient by CPF"""
        try:
            result = paciente_service.consultar_por_cpf(cpf, x_connection_id)
            return result

        except ValueError as e:
            raise HTTPException(400, str(e))

        except AdminAPIError as e:
            raise HTTPException(500, e.message)

    @app.get("/resources")
    async def list_resources():
        """List active resources"""
        try:
            resources = admin_service.list_active_resources()
            return {
                "resources": [
                    {
                        "id": str(r.id),
                        "path": r.path,
                        "description": r.description
                    }
                    for r in resources
                ]
            }
        except AdminAPIError as e:
            raise HTTPException(500, e.message)

    return app


# ============================================================================
# Usage Examples
# ============================================================================

if __name__ == "__main__":
    # Example 1: Direct service usage
    print("=== Direct Service Usage ===")
    config = Config(admin_api_url="http://localhost:8000")
    service = AdminAPIService(config)

    if service.health_check():
        print("✓ Admin API is healthy")

        resources = service.list_active_resources()
        print(f"Active resources: {len(resources)}")

    # Example 2: Domain service usage
    print("\n=== Domain Service Usage ===")
    paciente_service = PacienteService(service)

    try:
        result = paciente_service.consultar_por_cpf(
            cpf="12345678900",
            connection_id="your-connection-id"
        )
        print(f"Result: {result}")
    except ValueError as e:
        print(f"Validation error: {e}")
    except AdminAPIError as e:
        print(f"API error: {e.message}")

    # Example 3: Run Flask app
    # flask_app = create_flask_app()
    # flask_app.run(debug=True, port=5000)

    # Example 4: Run FastAPI app
    # fastapi_app = create_fastapi_app()
    # import uvicorn
    # uvicorn.run(fastapi_app, host="0.0.0.0", port=8080)
