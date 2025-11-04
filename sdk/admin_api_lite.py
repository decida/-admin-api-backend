"""
Admin API Lite SDK - Minimal single-file client for resource execution

This is a lightweight, standalone SDK that focuses on executing API resources.
It can be easily copied to other projects without dependencies (uses only stdlib).

Usage:
    from admin_api_lite import AdminAPILite

    # Initialize client
    client = AdminAPILite(
        base_url="http://localhost:8000",
        headers={"Authorization": "Bearer your-token"}  # Optional custom headers
    )

    # Execute resource by ID
    result = client.execute_by_id(
        resource_id="resource-uuid",
        connection_id="connection-uuid",
        parameters={"param1": "value1", "param2": 123}
    )

    # Check result
    if result["success"]:
        print("Execution successful!")
        if "rows" in result:
            # Single business object result
            print(f"Rows returned: {result['rowCount']}")
            print(f"Data: {result['rows']}")
        elif "steps" in result and isinstance(result["steps"], list):
            # Chain execution result
            print(f"Steps executed: {len(result['steps'])}")
            print(f"Final result: {result['result']}")
            # Detailed step information
            for step in result.get('steps', []):
                print(f"\n  Step {step['sequence']}: {step['name']}")
                print(f"    Type: {step['commandType']}")
                print(f"    Total: {step['total']}")
                if step.get('output'):
                    print(f"    Output: {step['output']}")
    else:
        print(f"Execution failed: {result.get('error')}")
"""

import json
import urllib.request
import urllib.error
from typing import Any, Dict, Optional


class AdminAPILiteError(Exception):
    """Base exception for Admin API Lite errors"""

    def __init__(self, message: str, status_code: Optional[int] = None, details: Optional[dict] = None):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class AdminAPILite:
    """
    Minimal Admin API client focused on resource execution.

    This client provides a simple interface to execute API resources by ID.
    It uses only Python standard library (urllib) and has no external dependencies.

    Attributes:
        base_url: Base URL of the Admin API Backend
        headers: Custom HTTP headers to include in all requests
        timeout: Request timeout in seconds
    """

    def __init__(
        self,
        base_url: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 30
    ):
        """
        Initialize Admin API Lite client.

        Args:
            base_url: Base URL of the Admin API Backend (e.g., "http://localhost:8000")
            headers: Optional custom headers to include in all requests
                    (e.g., {"Authorization": "Bearer token", "X-Custom-Header": "value"})
            timeout: Request timeout in seconds (default: 30)
        """
        self.base_url = base_url.rstrip("/")
        self.custom_headers = headers or {}
        self.timeout = timeout
        self.api_prefix = "/api/v1"

    def execute_by_id(
        self,
        resource_id: str,
        connection_id: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute API resource by its ID.

        This method calls the generic /api/v1/api-resources/execute endpoint
        passing the resource_id, connection_id, and parameters.

        Args:
            resource_id: UUID of the API resource to execute
            connection_id: Database connection ID (UUID) or slug (string)
            parameters: Dictionary of parameters to pass to the resource (optional)

        Returns:
            Dictionary containing execution result with the following structure:

            For single business object execution:
            {
                "success": bool,
                "rows": list[dict],      # Query results
                "rowCount": int,         # Number of rows returned
                "error": str | None      # Error message if failed
            }

            For chain execution:
            {
                "success": bool,
                "totalExecutionTime": str,  # Total execution time for the chain
                "steps": [                  # Detailed results for each step
                    {
                        "sequence": int,          # Step execution order (1-based)
                        "name": str,              # Step name (business object name)
                        "commandType": str,       # SQL command type (select, insert, update, delete)
                        "sqlCommand": str,        # Complete SQL with all parameters interpolated (single line)
                        "output": list | None,    # Query results (for SELECT statements)
                        "total": int,             # Rows returned (SELECT) or affected (DML)
                        "executionTime": str      # Formatted execution time for this step
                    },
                    ...
                ],
                "error": {               # Error details if failed
                    "message": str,
                    "step": int,
                    "businessObjectName": str,
                    "details": str
                } | None
            }

        Raises:
            AdminAPILiteError: If resource not found or execution fails

        Example:
            >>> client = AdminAPILite("http://localhost:8000")
            >>> result = client.execute_by_id(
            ...     resource_id="abc-123",
            ...     connection_id="def-456",
            ...     parameters={"user_id": 42}
            ... )
            >>> if result["success"]:
            ...     print(f"Got {result['rowCount']} rows")
        """
        # Execute resource using generic endpoint
        endpoint = f"{self.api_prefix}/api-resources/execute"
        data = {
            "resource_id": resource_id,
            "connection_id": connection_id,
            "parameters": parameters or {}
        }

        return self._make_request("POST", endpoint, data=data)

    def list_api_resources(self, active_only: bool = True) -> list[Dict[str, Any]]:
        """
        List API resources from Admin API.

        Args:
            active_only: If True, returns only active resources (default: True)

        Returns:
            List of API resource dictionaries

        Raises:
            AdminAPILiteError: If request fails

        Example:
            >>> client = AdminAPILite("http://localhost:8000")
            >>> resources = client.list_api_resources()
            >>> for resource in resources:
            ...     print(f"{resource['method']} {resource['path']}")
        """
        endpoint = f"{self.api_prefix}/api-resources"
        if active_only:
            endpoint += "?isActive=true"

        response = self._make_request("GET", endpoint)

        # Response pode ser uma lista ou um dict com 'items'
        if isinstance(response, list):
            return response
        elif isinstance(response, dict) and 'items' in response:
            return response['items']
        else:
            return []

    def get_database(self, database_id: str) -> Dict[str, Any]:
        """
        Get database connection by ID.

        Args:
            database_id: UUID of the database connection

        Returns:
            Dictionary containing database metadata

        Raises:
            AdminAPILiteError: If database not found or request fails

        Example:
            >>> client = AdminAPILite("http://localhost:8000")
            >>> db = client.get_database("abc-123-def")
            >>> print(db['connectionString'])
        """
        endpoint = f"{self.api_prefix}/databases/{database_id}"
        return self._make_request("GET", endpoint)

    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[dict] = None
    ) -> Dict[str, Any]:
        """
        Make HTTP request to the API.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            data: Request body data (for POST/PATCH)

        Returns:
            Response data as dictionary

        Raises:
            AdminAPILiteError: If request fails
        """
        # Build full URL
        url = f"{self.base_url}{endpoint}"

        # Prepare headers (merge custom headers with defaults)
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            **self.custom_headers  # Custom headers override defaults
        }

        # Prepare request body
        request_data = None
        if data:
            request_data = json.dumps(data).encode("utf-8")

        # Create request
        req = urllib.request.Request(
            url,
            data=request_data,
            headers=headers,
            method=method
        )

        try:
            # Execute request
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                response_data = response.read().decode("utf-8")
                if response_data:
                    return json.loads(response_data)
                return {}

        except urllib.error.HTTPError as e:
            # Parse error response
            error_body = e.read().decode("utf-8")
            error_data = {}

            try:
                error_data = json.loads(error_body)
            except json.JSONDecodeError:
                error_data = {"detail": error_body}

            error_message = error_data.get("detail", str(e))

            raise AdminAPILiteError(
                message=f"HTTP {e.code}: {error_message}",
                status_code=e.code,
                details=error_data
            )

        except urllib.error.URLError as e:
            raise AdminAPILiteError(f"Connection failed: {str(e)}")

        except Exception as e:
            raise AdminAPILiteError(f"Unexpected error: {str(e)}")

    def health_check(self) -> bool:
        """
        Check if API is healthy.

        Returns:
            True if API is healthy, False otherwise

        Example:
            >>> client = AdminAPILite("http://localhost:8000")
            >>> if client.health_check():
            ...     print("API is up!")
        """
        try:
            response = self._make_request("GET", "/health")
            return response.get("status") == "healthy"
        except Exception:
            return False


# ===== Example Usage =====

def example_basic_execution():
    """Example: Basic resource execution"""
    print("=== Example: Basic Resource Execution ===\n")

    # Initialize client
    client = AdminAPILite(
        base_url="http://localhost:8000",
        timeout=30
    )

    # Check if API is healthy
    if not client.health_check():
        print("ERROR: API is not healthy or not reachable")
        return

    print("✓ API is healthy\n")

    # Execute resource
    try:
        result = client.execute_by_id(
            resource_id="your-resource-uuid-here",
            connection_id="your-connection-uuid-here",
            parameters={
                "user_id": 42,
                "status": "active"
            }
        )

        if result["success"]:
            print("✓ Execution successful!")

            # Handle single business object result
            if "rows" in result:
                print(f"  Rows returned: {result['rowCount']}")
                print(f"  Data: {result['rows'][:3]}...")  # Show first 3 rows

            # Handle chain execution result
            elif "steps" in result and isinstance(result["steps"], list):
                print(f"  Chain steps executed: {len(result['steps'])}")
                if result.get("totalExecutionTime"):
                    print(f"  Total time: {result['totalExecutionTime']}")

                # Display detailed step information
                for step in result['steps']:
                    print(f"\n  Step {step['sequence']}: {step['name']}")
                    print(f"    Command Type: {step['commandType']}")
                    print(f"    Total (rows/affected): {step['total']}")
                    print(f"    SQL: {step['sqlCommand']}")
                    if step.get('executionTime'):
                        print(f"    Time: {step['executionTime']}")
                    if step.get('output') and isinstance(step['output'], list):
                        print(f"    Output rows: {len(step['output'])}")
        else:
            print(f"✗ Execution failed: {result.get('error')}")

    except AdminAPILiteError as e:
        print(f"✗ Error: {e.message}")
        if e.status_code:
            print(f"  Status code: {e.status_code}")
        if e.details:
            print(f"  Details: {e.details}")


def example_with_auth_headers():
    """Example: Using custom headers for authentication"""
    print("\n=== Example: Execution with Authentication Headers ===\n")

    # Initialize client with custom headers
    client = AdminAPILite(
        base_url="http://localhost:8000",
        headers={
            "Authorization": "Bearer your-api-token-here",
            "X-API-Key": "your-api-key-here",
            "X-Custom-Header": "custom-value"
        }
    )

    try:
        result = client.execute_by_id(
            resource_id="secured-resource-uuid",
            connection_id="connection-uuid",
            parameters={"query": "SELECT * FROM users LIMIT 10"}
        )

        print(f"✓ Authenticated execution: {result['success']}")

    except AdminAPILiteError as e:
        print(f"✗ Authentication failed: {e.message}")


def example_chain_execution():
    """Example: Chain execution with detailed step tracing"""
    print("\n=== Example: Chain Execution with Step Tracing ===\n")

    client = AdminAPILite("http://localhost:8000")

    try:
        result = client.execute_by_id(
            resource_id="chain-resource-uuid",
            connection_id="connection-uuid",
            parameters={"user_id": 1}
        )

        if result["success"] and "steps" in result and isinstance(result["steps"], list):
            print("✓ Chain execution successful!\n")

            if result.get("totalExecutionTime"):
                print(f"Total Chain Time: {result['totalExecutionTime']}\n")

            # Display execution trace for debugging
            for step in result['steps']:
                print(f"Step {step['sequence']}: {step['name']}")
                print(f"  Type: {step['commandType']}")
                print(f"  Result Count: {step['total']}")
                if step.get('executionTime'):
                    print(f"  Time: {step['executionTime']}")
                print(f"  SQL: {step['sqlCommand']}\n")

                # For SELECT steps, show sample output
                if step.get('output') and len(step['output']) > 0:
                    print(f"  Sample output (first row):")
                    first_row = step['output'][0]
                    for key, value in first_row.items():
                        print(f"    {key}: {value}")
                    print()
        else:
            print(f"✗ Execution failed: {result.get('error')}")

    except AdminAPILiteError as e:
        print(f"✗ Request error: {e.message}")


def example_error_handling():
    """Example: Comprehensive error handling"""
    print("\n=== Example: Error Handling ===\n")

    client = AdminAPILite("http://localhost:8000")

    try:
        result = client.execute_by_id(
            resource_id="non-existent-resource-id",
            connection_id="connection-id",
            parameters={}
        )

        # Check execution success
        if not result["success"]:
            if "error" in result:
                error = result["error"]

                # Handle chain execution error
                if isinstance(error, dict):
                    print(f"Chain execution failed at step {error.get('step')}")
                    print(f"Business object: {error.get('businessObjectName')}")
                    print(f"Message: {error.get('message')}")
                    print(f"Details: {error.get('details')}")

                # Handle simple error
                else:
                    print(f"Execution failed: {error}")

    except AdminAPILiteError as e:
        if e.status_code == 404:
            print("✗ Resource not found")
        elif e.status_code == 401:
            print("✗ Authentication required")
        elif e.status_code == 400:
            print("✗ Invalid parameters")
        else:
            print(f"✗ Request failed: {e.message}")


if __name__ == "__main__":
    """
    Run examples when script is executed directly.

    To use this SDK in your project, simply copy this file and import it:

        from admin_api_lite import AdminAPILite, AdminAPILiteError

        client = AdminAPILite("http://localhost:8000")
        result = client.execute_by_id(resource_id, connection_id, parameters)
    """
    print("Admin API Lite SDK - Examples\n")
    print("=" * 60)

    # Uncomment to run examples:
    # example_basic_execution()
    # example_with_auth_headers()
    # example_chain_execution()  # New: Detailed chain execution tracing
    # example_error_handling()

    print("\nℹ️  Uncomment example functions in __main__ to run them")
    print("ℹ️  Replace UUIDs with real resource and connection IDs")
    print("\nℹ️  For chain execution debugging:")
    print("    - Use example_chain_execution() to see detailed step-by-step tracing")
    print("    - Each step shows SQL, row count, and output data")
