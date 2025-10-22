"""
Usage examples for Admin API SDK
"""

from sdk.python import AdminAPIClient, ExecutionError, ResourceNotFoundError


def example_basic_usage():
    """Basic usage example"""
    # Initialize client
    client = AdminAPIClient("http://localhost:8000")

    # Check API health
    if client.health_check():
        print("✓ API is healthy")

    # List all resources
    resources = client.list_resources()
    print(f"Found {len(resources)} resources")

    for resource in resources:
        print(f"  - {resource.path} ({resource.method})")


def example_get_resource():
    """Get specific resource example"""
    client = AdminAPIClient("http://localhost:8000")

    # Get by ID
    try:
        resource = client.get_resource_by_id("0b07939c-4ced-4e18-a519-48b03e744cb7")
        print(f"Resource: {resource.path}")
        print(f"Active: {resource.is_active}")
        print(f"Business Object: {resource.business_object_name}")

        if resource.execution_chain:
            print(f"Chain steps: {len(resource.execution_chain)}")
    except ResourceNotFoundError:
        print("Resource not found")

    # Get by path
    resource = client.get_resource_by_path("/api/v1/consultar-paciente")
    if resource:
        print(f"Found resource: {resource.id}")


def example_execute_resource():
    """Execute resource example"""
    client = AdminAPIClient("http://localhost:8000")

    # Execute by path
    try:
        result = client.execute(
            path="/api/v1/consultar-paciente",
            connection_id="your-connection-uuid",
            parameters={
                "cpf": "12345678900"
            }
        )

        if result.success:
            print(f"✓ Execution successful")

            # Check if it's a chain result
            if hasattr(result, 'steps'):
                print(f"  Steps executed: {result.steps}")
                print(f"  Final result: {result.result}")
                print(f"  All results: {result.all_results}")
            else:
                print(f"  Rows returned: {result.row_count}")
                print(f"  Data: {result.rows}")
        else:
            print(f"✗ Execution failed: {result.error}")

    except ExecutionError as e:
        print(f"Execution error: {e.message}")
        if e.step:
            print(f"  Failed at step: {e.step}")
        if e.business_object_name:
            print(f"  Business object: {e.business_object_name}")


def example_execute_by_id():
    """Execute resource by ID example"""
    client = AdminAPIClient("http://localhost:8000")

    result = client.execute_by_id(
        resource_id="0b07939c-4ced-4e18-a519-48b03e744cb7",
        connection_id="your-connection-uuid",
        parameters={"param1": "value1"}
    )

    print(f"Success: {result.success}")


def example_create_resource():
    """Create resource example"""
    client = AdminAPIClient("http://localhost:8000")

    # Simple resource (single business object)
    resource = client.create_resource(
        path="/api/v1/my-new-endpoint",
        business_object_id="business-object-uuid",
        description="My custom endpoint",
        is_active=True
    )

    print(f"Created resource: {resource.id}")


def example_create_resource_with_chain():
    """Create resource with execution chain"""
    client = AdminAPIClient("http://localhost:8000")

    execution_chain = [
        {
            "businessObjectId": "bo-uuid-1",
            "businessObjectName": "Query Cliente",
            "businessObjectType": "select",
            "businessObjectParams": [
                {"name": "clienteId", "type": "number", "required": True}
            ],
            "order": 1,
            "parameterMappings": []
        },
        {
            "businessObjectId": "bo-uuid-2",
            "businessObjectName": "Insert Log",
            "businessObjectType": "insert",
            "businessObjectParams": [
                {"name": "clienteId", "type": "number", "required": True}
            ],
            "order": 2,
            "parameterMappings": [
                {
                    "parameterName": "clienteId",
                    "sourceType": "variable",
                    "staticValue": "",
                    "variableSource": {
                        "stepIndex": 0,
                        "fieldName": "id"
                    }
                }
            ]
        }
    ]

    resource = client.create_resource(
        path="/api/v1/cliente-with-log",
        business_object_id="bo-uuid-1",
        description="Cliente query with automatic log",
        execution_chain=execution_chain
    )

    print(f"Created resource with chain: {resource.id}")


def example_update_resource():
    """Update resource example"""
    client = AdminAPIClient("http://localhost:8000")

    resource = client.update_resource(
        resource_id="resource-uuid",
        description="Updated description",
        is_active=False
    )

    print(f"Updated resource: {resource.path}")


def example_toggle_resource():
    """Toggle resource active status"""
    client = AdminAPIClient("http://localhost:8000")

    resource = client.toggle_resource("resource-uuid")
    print(f"Resource is now: {'active' if resource.is_active else 'inactive'}")


def example_search_resources():
    """Search resources example"""
    client = AdminAPIClient("http://localhost:8000")

    # Search by path or description
    results = client.search_resources("paciente")

    print(f"Found {len(results)} resources matching 'paciente'")
    for resource in results:
        print(f"  - {resource.path}")


def example_filter_active_resources():
    """Filter active resources"""
    client = AdminAPIClient("http://localhost:8000")

    active = client.get_active_resources()
    inactive = client.get_inactive_resources()

    print(f"Active resources: {len(active)}")
    print(f"Inactive resources: {len(inactive)}")


def example_with_authentication():
    """Example with API key authentication (if implemented)"""
    client = AdminAPIClient(
        "http://localhost:8000",
        api_key="your-api-key-here"
    )

    resources = client.list_resources()
    print(f"Authenticated access: {len(resources)} resources")


def example_error_handling():
    """Comprehensive error handling example"""
    from sdk.python import (
        ConnectionError,
        AuthenticationError,
        ResourceNotFoundError,
        ValidationError,
        ExecutionError
    )

    client = AdminAPIClient("http://localhost:8000")

    try:
        result = client.execute(
            path="/api/v1/test",
            connection_id="conn-uuid",
            parameters={"test": "value"}
        )
    except ConnectionError as e:
        print(f"Connection failed: {e.message}")
    except AuthenticationError as e:
        print(f"Authentication failed: {e.message}")
    except ResourceNotFoundError as e:
        print(f"Resource not found: {e.message}")
    except ValidationError as e:
        print(f"Validation error: {e.message}")
        print(f"Details: {e.details}")
    except ExecutionError as e:
        print(f"Execution failed: {e.message}")
        if e.step:
            print(f"Failed at step {e.step}: {e.business_object_name}")
    except Exception as e:
        print(f"Unexpected error: {e}")


def example_integration_in_backend():
    """
    Example of integrating SDK in another backend application.
    This shows how to wrap SDK calls in your own API endpoints.
    """

    # In your backend (e.g., Flask, FastAPI, Django)
    from flask import Flask, request, jsonify

    app = Flask(__name__)
    admin_client = AdminAPIClient("http://localhost:8000")

    @app.route("/consultar-paciente", methods=["POST"])
    def consultar_paciente():
        """Wrapper endpoint that uses Admin API SDK"""
        data = request.get_json()

        try:
            result = admin_client.execute(
                path="/api/v1/consultar-paciente",
                connection_id=data["connection_id"],
                parameters={"cpf": data["cpf"]}
            )

            if result.success:
                return jsonify({
                    "success": True,
                    "data": result.rows
                })
            else:
                return jsonify({
                    "success": False,
                    "error": result.error
                }), 500

        except Exception as e:
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    # Your backend now provides a simpler interface to your frontend
    # while leveraging the power of Admin API Backend


if __name__ == "__main__":
    # Run examples
    print("=== Basic Usage ===")
    example_basic_usage()

    print("\n=== Get Resource ===")
    example_get_resource()

    print("\n=== Execute Resource ===")
    example_execute_resource()

    print("\n=== Search Resources ===")
    example_search_resources()

    print("\n=== Filter Resources ===")
    example_filter_active_resources()
