"""
Main SDK client for Admin API Backend
Provides a simple facade for interacting with API resources
"""

import json
from typing import Any, Dict, List
from datetime import datetime
import urllib.request
import urllib.error
import urllib.parse

from .exceptions import (
    AdminAPIError,
    ConnectionError,
    AuthenticationError,
    ResourceNotFoundError,
    ValidationError,
    ExecutionError,
)
from .models import (
    APIResource,
    ExecutionResult,
    ChainExecutionResult,
    ChainExecutionError,
    BusinessObjectParam,
    ExecutionChainStep,
    ParameterMapping,
    VariableSource,
)


class AdminAPIClient:
    """
    Facade client for Admin API Backend.

    Usage:
        client = AdminAPIClient("http://localhost:8000")

        # List all resources
        resources = client.list_resources()

        # Get specific resource
        resource = client.get_resource_by_id("resource-uuid")
        resource = client.get_resource_by_path("/api/v1/my-endpoint")

        # Execute resource
        result = client.execute(
            path="/api/v1/my-endpoint",
            connection_id="connection-uuid",
            parameters={"param1": "value1"}
        )

        # Or execute by resource ID
        result = client.execute_by_id(
            resource_id="resource-uuid",
            connection_id="connection-uuid",
            parameters={"param1": "value1"}
        )
    """

    def __init__(self, base_url: str, timeout: int = 30, api_key: str | None = None):
        """
        Initialize Admin API client.

        Args:
            base_url: Base URL of the Admin API Backend (e.g., "http://localhost:8000")
            timeout: Request timeout in seconds (default: 30)
            api_key: Optional API key for authentication (if implemented)
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.api_key = api_key
        self.api_prefix = "/api/v1"

    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: dict | None = None,
        params: dict | None = None
    ) -> dict | list:
        """
        Make HTTP request to the API.

        Args:
            method: HTTP method (GET, POST, PATCH, DELETE)
            endpoint: API endpoint path
            data: Request body data (for POST/PATCH)
            params: Query parameters

        Returns:
            Response data as dict or list

        Raises:
            ConnectionError: If connection fails
            AuthenticationError: If authentication fails (401)
            ResourceNotFoundError: If resource not found (404)
            ValidationError: If validation fails (400)
            AdminAPIError: For other API errors
        """
        # Build URL
        url = f"{self.base_url}{endpoint}"

        if params:
            query_string = urllib.parse.urlencode(params)
            url = f"{url}?{query_string}"

        # Prepare request
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        request_data = None
        if data:
            request_data = json.dumps(data).encode("utf-8")

        req = urllib.request.Request(
            url,
            data=request_data,
            headers=headers,
            method=method
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                response_data = response.read().decode("utf-8")
                if response_data:
                    return json.loads(response_data)
                return {}

        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8")
            error_data = {}

            try:
                error_data = json.loads(error_body)
            except json.JSONDecodeError:
                error_data = {"detail": error_body}

            error_message = error_data.get("detail", str(e))

            if e.code == 401:
                raise AuthenticationError(error_message, e.code, error_data)
            elif e.code == 404:
                raise ResourceNotFoundError(error_message, e.code, error_data)
            elif e.code == 400:
                raise ValidationError(error_message, e.code, error_data)
            else:
                raise AdminAPIError(error_message, e.code, error_data)

        except urllib.error.URLError as e:
            raise ConnectionError(f"Failed to connect to API: {str(e)}")

        except Exception as e:
            raise AdminAPIError(f"Unexpected error: {str(e)}")

    # ===== Resource Management Methods =====

    def list_resources(self, skip: int = 0, limit: int = 100) -> List[APIResource]:
        """
        List all API resources.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of APIResource objects
        """
        endpoint = f"{self.api_prefix}/api-resources"
        params = {"skip": skip, "limit": limit}

        data = self._make_request("GET", endpoint, params=params)
        return [self._parse_api_resource(item) for item in data]

    def get_resource_by_id(self, resource_id: str) -> APIResource:
        """
        Get API resource by ID.

        Args:
            resource_id: UUID of the resource

        Returns:
            APIResource object

        Raises:
            ResourceNotFoundError: If resource not found
        """
        endpoint = f"{self.api_prefix}/api-resources/{resource_id}"
        data = self._make_request("GET", endpoint)
        return self._parse_api_resource(data)

    def get_resource_by_path(self, path: str) -> APIResource | None:
        """
        Get API resource by path.

        Args:
            path: Resource path (e.g., "/api/v1/my-endpoint")

        Returns:
            APIResource object or None if not found
        """
        resources = self.list_resources()
        for resource in resources:
            if resource.path == path:
                return resource
        return None

    def create_resource(
        self,
        path: str,
        business_object_id: str,
        description: str | None = None,
        is_active: bool = True,
        execution_chain: List[dict] | None = None
    ) -> APIResource:
        """
        Create new API resource.

        Args:
            path: Resource path (must start with /)
            business_object_id: UUID of the business object
            description: Optional description
            is_active: Whether resource is active
            execution_chain: Optional execution chain configuration

        Returns:
            Created APIResource object
        """
        endpoint = f"{self.api_prefix}/api-resources"
        data = {
            "path": path,
            "businessObjectId": business_object_id,
            "description": description,
            "isActive": is_active,
        }

        if execution_chain:
            data["executionChain"] = execution_chain

        response = self._make_request("POST", endpoint, data=data)
        return self._parse_api_resource(response)

    def update_resource(
        self,
        resource_id: str,
        path: str | None = None,
        description: str | None = None,
        is_active: bool | None = None,
        business_object_id: str | None = None,
        execution_chain: List[dict] | None = None
    ) -> APIResource:
        """
        Update API resource.

        Args:
            resource_id: UUID of the resource
            path: New path (optional)
            description: New description (optional)
            is_active: New active status (optional)
            business_object_id: New business object ID (optional)
            execution_chain: New execution chain (optional)

        Returns:
            Updated APIResource object
        """
        endpoint = f"{self.api_prefix}/api-resources/{resource_id}"
        data = {}

        if path is not None:
            data["path"] = path
        if description is not None:
            data["description"] = description
        if is_active is not None:
            data["isActive"] = is_active
        if business_object_id is not None:
            data["businessObjectId"] = business_object_id
        if execution_chain is not None:
            data["executionChain"] = execution_chain

        response = self._make_request("PATCH", endpoint, data=data)
        return self._parse_api_resource(response)

    def delete_resource(self, resource_id: str) -> None:
        """
        Delete API resource.

        Args:
            resource_id: UUID of the resource
        """
        endpoint = f"{self.api_prefix}/api-resources/{resource_id}"
        self._make_request("DELETE", endpoint)

    def toggle_resource(self, resource_id: str) -> APIResource:
        """
        Toggle API resource active status.

        Args:
            resource_id: UUID of the resource

        Returns:
            Updated APIResource object
        """
        endpoint = f"{self.api_prefix}/api-resources/{resource_id}/toggle"
        response = self._make_request("PATCH", endpoint)
        return self._parse_api_resource(response)

    # ===== Execution Methods =====

    def execute(
        self,
        path: str,
        connection_id: str,
        parameters: Dict[str, Any] | None = None
    ) -> ExecutionResult | ChainExecutionResult:
        """
        Execute API resource by path.

        Args:
            path: Resource path (e.g., "/api/v1/my-endpoint")
            connection_id: UUID of the database connection
            parameters: Parameters to pass to the resource

        Returns:
            ExecutionResult or ChainExecutionResult depending on resource configuration

        Raises:
            ResourceNotFoundError: If resource not found
            ExecutionError: If execution fails
        """
        data = {
            "connectionId": connection_id,
            **(parameters or {})
        }

        try:
            response = self._make_request("POST", path, data=data)
            return self._parse_execution_result(response)
        except AdminAPIError as e:
            if e.status_code == 404:
                raise ResourceNotFoundError(f"Resource not found: {path}", e.status_code)
            raise ExecutionError(e.message, e.status_code, e.details)

    def execute_by_id(
        self,
        resource_id: str,
        connection_id: str,
        parameters: Dict[str, Any] | None = None
    ) -> ExecutionResult | ChainExecutionResult:
        """
        Execute API resource by ID.

        Args:
            resource_id: UUID of the resource
            connection_id: UUID of the database connection
            parameters: Parameters to pass to the resource

        Returns:
            ExecutionResult or ChainExecutionResult depending on resource configuration

        Raises:
            ResourceNotFoundError: If resource not found
            ExecutionError: If execution fails
        """
        # First get the resource to know its path
        resource = self.get_resource_by_id(resource_id)
        return self.execute(resource.path, connection_id, parameters)

    # ===== Helper Methods =====

    def _parse_api_resource(self, data: dict) -> APIResource:
        """Parse API resource from response data"""
        # Parse business object params
        bo_params = []
        for param in data.get("businessObjectParams", []):
            bo_params.append(BusinessObjectParam(
                name=param.get("name"),
                type=param.get("type"),
                required=param.get("required", False),
                default_value=param.get("defaultValue")
            ))

        # Parse execution chain
        execution_chain = None
        if data.get("executionChain"):
            execution_chain = []
            for step_data in data["executionChain"]:
                # Parse step params
                step_params = []
                for param in step_data.get("businessObjectParams", []):
                    step_params.append(BusinessObjectParam(
                        name=param.get("name"),
                        type=param.get("type"),
                        required=param.get("required", False),
                        default_value=param.get("defaultValue")
                    ))

                # Parse parameter mappings
                mappings = []
                for mapping in step_data.get("parameterMappings", []):
                    var_source = mapping.get("variableSource", {})
                    mappings.append(ParameterMapping(
                        parameter_name=mapping.get("parameterName"),
                        source_type=mapping.get("sourceType"),
                        static_value=mapping.get("staticValue", ""),
                        variable_source=VariableSource(
                            step_index=var_source.get("stepIndex"),
                            field_name=var_source.get("fieldName", "")
                        )
                    ))

                execution_chain.append(ExecutionChainStep(
                    business_object_id=step_data.get("businessObjectId"),
                    business_object_name=step_data.get("businessObjectName"),
                    business_object_type=step_data.get("businessObjectType"),
                    business_object_params=step_params,
                    order=step_data.get("order"),
                    parameter_mappings=mappings
                ))

        return APIResource(
            id=data["id"],
            path=data["path"],
            method=data["method"],
            description=data.get("description"),
            is_active=data["isActive"],
            business_object_id=data["businessObjectId"],
            business_object_name=data["businessObjectName"],
            business_object_params=bo_params,
            execution_chain=execution_chain,
            created_at=datetime.fromisoformat(data["createdAt"].replace("Z", "+00:00")),
            updated_at=datetime.fromisoformat(data["updatedAt"].replace("Z", "+00:00"))
        )

    def _parse_execution_result(self, data: dict) -> ExecutionResult | ChainExecutionResult:
        """Parse execution result from response data"""
        # Check if it's a chain execution result
        if "steps" in data or "allResults" in data:
            error = None
            if data.get("error"):
                error_data = data["error"]
                error = ChainExecutionError(
                    message=error_data.get("message"),
                    step=error_data.get("step"),
                    business_object_name=error_data.get("businessObjectName"),
                    details=error_data.get("details")
                )

            return ChainExecutionResult(
                success=data.get("success", False),
                steps=data.get("steps"),
                result=data.get("result"),
                all_results=data.get("allResults"),
                error=error
            )
        else:
            # Legacy single business object result
            return ExecutionResult(
                success=data.get("success", False),
                rows=data.get("rows"),
                row_count=data.get("rowCount"),
                error=data.get("error")
            )

    # ===== Convenience Methods =====

    def health_check(self) -> bool:
        """
        Check if API is healthy.

        Returns:
            True if API is healthy, False otherwise
        """
        try:
            response = self._make_request("GET", "/health")
            return response.get("status") == "healthy"
        except Exception:
            return False

    def get_active_resources(self) -> List[APIResource]:
        """
        Get all active API resources.

        Returns:
            List of active APIResource objects
        """
        resources = self.list_resources()
        return [r for r in resources if r.is_active]

    def get_inactive_resources(self) -> List[APIResource]:
        """
        Get all inactive API resources.

        Returns:
            List of inactive APIResource objects
        """
        resources = self.list_resources()
        return [r for r in resources if not r.is_active]

    def search_resources(self, query: str) -> List[APIResource]:
        """
        Search resources by path or description.

        Args:
            query: Search query

        Returns:
            List of matching APIResource objects
        """
        resources = self.list_resources()
        query_lower = query.lower()
        return [
            r for r in resources
            if query_lower in r.path.lower() or
            (r.description and query_lower in r.description.lower())
        ]
