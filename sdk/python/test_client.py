"""
Simple tests for Admin API SDK
Run with: python -m pytest test_client.py
Or without pytest: python test_client.py
"""

import sys
from typing import Any

from client import AdminAPIClient
from exceptions import ConnectionError, ResourceNotFoundError


class TestResult:
    """Simple test result tracker"""
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []

    def assert_true(self, condition: bool, message: str):
        if condition:
            self.passed += 1
            print(f"  ✓ {message}")
        else:
            self.failed += 1
            self.errors.append(message)
            print(f"  ✗ {message}")

    def assert_equal(self, actual: Any, expected: Any, message: str):
        if actual == expected:
            self.passed += 1
            print(f"  ✓ {message}")
        else:
            self.failed += 1
            error = f"{message} (expected: {expected}, got: {actual})"
            self.errors.append(error)
            print(f"  ✗ {error}")

    def assert_not_none(self, value: Any, message: str):
        self.assert_true(value is not None, message)

    def summary(self):
        total = self.passed + self.failed
        print(f"\n{'='*60}")
        print(f"Test Results: {self.passed}/{total} passed")
        if self.failed > 0:
            print(f"\nFailed tests:")
            for error in self.errors:
                print(f"  - {error}")
        print(f"{'='*60}")
        return self.failed == 0


def test_client_initialization():
    """Test client initialization"""
    print("\n=== Test: Client Initialization ===")
    result = TestResult()

    client = AdminAPIClient("http://localhost:8000")
    result.assert_equal(client.base_url, "http://localhost:8000", "Base URL is set correctly")
    result.assert_equal(client.timeout, 30, "Default timeout is 30 seconds")
    result.assert_equal(client.api_prefix, "/api/v1", "API prefix is correct")

    client_with_key = AdminAPIClient("http://localhost:8000", api_key="test-key")
    result.assert_equal(client_with_key.api_key, "test-key", "API key is set correctly")

    return result.summary()


def test_health_check():
    """Test health check (requires running backend)"""
    print("\n=== Test: Health Check ===")
    result = TestResult()

    client = AdminAPIClient("http://localhost:8000")

    try:
        is_healthy = client.health_check()
        result.assert_true(is_healthy, "API health check returns True")
    except ConnectionError:
        print("  ⚠ Backend not running - skipping health check test")

    return result.summary()


def test_list_resources():
    """Test listing resources (requires running backend)"""
    print("\n=== Test: List Resources ===")
    result = TestResult()

    client = AdminAPIClient("http://localhost:8000")

    try:
        resources = client.list_resources()
        result.assert_true(isinstance(resources, list), "list_resources returns a list")
        print(f"  Found {len(resources)} resources")
    except ConnectionError:
        print("  ⚠ Backend not running - skipping list resources test")

    return result.summary()


def test_get_resource_not_found():
    """Test getting non-existent resource"""
    print("\n=== Test: Get Non-Existent Resource ===")
    result = TestResult()

    client = AdminAPIClient("http://localhost:8000")

    try:
        client.get_resource_by_id("00000000-0000-0000-0000-000000000000")
        result.assert_true(False, "Should raise ResourceNotFoundError")
    except ResourceNotFoundError:
        result.assert_true(True, "ResourceNotFoundError raised correctly")
    except ConnectionError:
        print("  ⚠ Backend not running - skipping test")

    return result.summary()


def test_search_functionality():
    """Test search and filter methods"""
    print("\n=== Test: Search and Filter ===")
    result = TestResult()

    client = AdminAPIClient("http://localhost:8000")

    try:
        # Test search
        all_resources = client.list_resources()
        if len(all_resources) > 0:
            # Search by path
            first_path = all_resources[0].path
            search_term = first_path.split("/")[-1] if "/" in first_path else first_path
            search_results = client.search_resources(search_term)
            result.assert_true(len(search_results) > 0, f"Search finds resources for '{search_term}'")

            # Test active/inactive filters
            active = client.get_active_resources()
            inactive = client.get_inactive_resources()
            result.assert_equal(
                len(active) + len(inactive),
                len(all_resources),
                "Active + inactive equals total resources"
            )
        else:
            print("  ⚠ No resources found - skipping search tests")

    except ConnectionError:
        print("  ⚠ Backend not running - skipping search tests")

    return result.summary()


def test_model_parsing():
    """Test model parsing from mock data"""
    print("\n=== Test: Model Parsing ===")
    result = TestResult()

    client = AdminAPIClient("http://localhost:8000")

    # Mock API resource data
    mock_data = {
        "id": "123e4567-e89b-12d3-a456-426614174000",
        "path": "/api/v1/test",
        "method": "POST",
        "description": "Test resource",
        "isActive": True,
        "businessObjectId": "223e4567-e89b-12d3-a456-426614174000",
        "businessObjectName": "Test BO",
        "businessObjectParams": [
            {"name": "param1", "type": "string", "required": True, "defaultValue": None}
        ],
        "executionChain": None,
        "createdAt": "2024-01-01T00:00:00Z",
        "updatedAt": "2024-01-01T00:00:00Z"
    }

    resource = client._parse_api_resource(mock_data)

    result.assert_equal(resource.id, mock_data["id"], "Resource ID parsed correctly")
    result.assert_equal(resource.path, mock_data["path"], "Resource path parsed correctly")
    result.assert_equal(resource.is_active, True, "Resource is_active parsed correctly")
    result.assert_not_none(resource.created_at, "Created timestamp parsed")
    result.assert_equal(len(resource.business_object_params), 1, "Business object params parsed")

    return result.summary()


def test_execution_result_parsing():
    """Test execution result parsing"""
    print("\n=== Test: Execution Result Parsing ===")
    result = TestResult()

    client = AdminAPIClient("http://localhost:8000")

    # Test legacy result
    legacy_data = {
        "success": True,
        "rows": [{"id": 1, "name": "Test"}],
        "rowCount": 1
    }

    legacy_result = client._parse_execution_result(legacy_data)
    result.assert_equal(legacy_result.success, True, "Legacy result success parsed")
    result.assert_equal(legacy_result.row_count, 1, "Legacy result row count parsed")

    # Test chain result
    chain_data = {
        "success": True,
        "steps": 2,
        "result": {"id": 1},
        "allResults": [{"id": 1}, {"insertedId": 2}]
    }

    chain_result = client._parse_execution_result(chain_data)
    result.assert_equal(chain_result.success, True, "Chain result success parsed")
    result.assert_equal(chain_result.steps, 2, "Chain result steps parsed")
    result.assert_not_none(chain_result.all_results, "Chain result all_results parsed")

    return result.summary()


def run_all_tests():
    """Run all tests"""
    print("="*60)
    print("Admin API SDK Test Suite")
    print("="*60)

    all_passed = True

    all_passed &= test_client_initialization()
    all_passed &= test_model_parsing()
    all_passed &= test_execution_result_parsing()
    all_passed &= test_health_check()
    all_passed &= test_list_resources()
    all_passed &= test_get_resource_not_found()
    all_passed &= test_search_functionality()

    print("\n" + "="*60)
    if all_passed:
        print("✓ All tests passed!")
        print("="*60)
        return 0
    else:
        print("✗ Some tests failed")
        print("="*60)
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
