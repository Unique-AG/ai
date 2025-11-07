import pytest
from pydantic import BaseModel

from unique_quartr.helpers import endpoint


class MockRequest(BaseModel):
    """Mock request model for testing."""

    param1: str
    param2: int | None = None


class MockResponse(BaseModel):
    """Mock response model for testing."""

    result: str
    value: int


class MockClient:
    """Mock client for testing."""

    def __init__(self, response_data: dict):
        self.response_data = response_data
        self.last_endpoint = None
        self.last_params = None

    def request(self, endpoint_path: str, params: dict) -> dict:
        """Mock request method."""
        self.last_endpoint = endpoint_path
        self.last_params = params
        return self.response_data


class TestEndpoint:
    """Test cases for the endpoint decorator/function."""

    def test_endpoint_basic_usage(self):
        """Test basic endpoint function usage."""
        # Create an endpoint function
        test_endpoint = endpoint(
            params=MockRequest,
            response_type=MockResponse,
        )

        # Create a mock client with expected response
        client = MockClient(response_data={"result": "success", "value": 42})

        # Create request parameters
        request_params = MockRequest(param1="test", param2=123)

        # Call the endpoint
        response = test_endpoint(client, request_params)

        # Verify response
        assert isinstance(response, MockResponse)
        assert response.result == "success"
        assert response.value == 42

        # Verify client was called with correct params
        assert client.last_params == {"param1": "test", "param2": 123}

    def test_endpoint_exclude_unset(self):
        """Test that endpoint excludes unset parameters."""
        test_endpoint = endpoint(
            params=MockRequest,
            response_type=MockResponse,
        )

        client = MockClient(response_data={"result": "success", "value": 99})

        # Create request with only required params
        request_params = MockRequest(param1="test")

        test_endpoint(client, request_params)

        # Verify optional param was excluded
        assert "param2" not in client.last_params
        assert client.last_params == {"param1": "test"}

    def test_endpoint_with_alias(self):
        """Test endpoint with field aliases."""

        class RequestWithAlias(BaseModel):
            field_name: str

            class Config:
                populate_by_name = True

        class ResponseWithAlias(BaseModel):
            result_field: str

        test_endpoint = endpoint(
            params=RequestWithAlias,
            response_type=ResponseWithAlias,
        )

        client = MockClient(response_data={"result_field": "aliased"})
        request_params = RequestWithAlias(field_name="value")

        response = test_endpoint(client, request_params)

        assert response.result_field == "aliased"

    def test_endpoint_response_validation(self):
        """Test that endpoint validates response against response_type."""
        test_endpoint = endpoint(
            params=MockRequest,
            response_type=MockResponse,
        )

        # Response missing required field should raise validation error
        client = MockClient(response_data={"result": "success"})  # Missing 'value'
        request_params = MockRequest(param1="test")

        with pytest.raises(Exception):  # Pydantic will raise validation error
            test_endpoint(client, request_params)

    def test_endpoint_returns_callable(self):
        """Test that endpoint returns a callable."""
        test_endpoint = endpoint(
            params=MockRequest,
            response_type=MockResponse,
        )

        assert callable(test_endpoint)
