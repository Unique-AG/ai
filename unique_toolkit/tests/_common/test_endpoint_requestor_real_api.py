"""
Test script for endpoint_requestor.py using real APIs.
This script tests all requestor types (requests, httpx, aiohttp) with real API endpoints.
"""

from string import Template

from pydantic import BaseModel

from unique_toolkit._common.endpoint_builder import HttpMethods, build_api_operation
from unique_toolkit._common.endpoint_requestor import (
    RequestContext,
    RequestorType,
    build_aiohttp_requestor,
    build_fake_requestor,
    build_httpx_requestor,
    build_request_requestor,
    build_requestor,
)


# Test models for JSONPlaceholder API
class PostPathParams(BaseModel):
    """Path parameters for getting a specific post."""

    post_id: int


class PostQueryParams(BaseModel):
    """Query parameters for posts endpoint."""

    _limit: int = 10
    _page: int = 1


class PostResponse(BaseModel):
    """Response model for a single post."""

    id: int
    title: str
    body: str
    userId: int


class PostsListResponse(BaseModel):
    """Response model for posts list."""

    posts: list[PostResponse]


class CreatePostPayload(BaseModel):
    """Payload for creating a new post."""

    title: str
    body: str
    userId: int


class CreatePostResponse(BaseModel):
    """Response model for creating a post."""

    id: int
    title: str
    body: str
    userId: int


class CombinedGetPostParams(PostPathParams, PostQueryParams):
    """Combined parameters for getting a post."""

    pass


class CombinedCreatePostParams(PostPathParams, CreatePostPayload):
    """Combined parameters for creating a post."""

    pass


def test_fake_requestor():
    """Test the fake requestor with mock data."""
    # Create API operation for getting a post
    GetPostEndpoint = build_api_operation(
        method=HttpMethods.GET,
        url_template=Template("https://jsonplaceholder.typicode.com/posts/${post_id}"),
        path_params_constructor=PostPathParams,
        payload_constructor=PostQueryParams,
        response_model_type=PostResponse,
    )

    # Create fake requestor
    FakePostRequestor = build_fake_requestor(
        operation_type=GetPostEndpoint,
        combined_model=CombinedGetPostParams,
        return_value={
            "id": 1,
            "title": "Fake Post Title",
            "body": "This is a fake post body for testing purposes.",
            "userId": 1,
        },
    )

    # Test the fake requestor
    response = FakePostRequestor.request(
        context=RequestContext(headers={"Content-Type": "application/json"}),
        post_id=1,
        _limit=10,
        _page=1,
    )

    # Assertions
    assert isinstance(response, PostResponse)
    assert response.id == 1
    assert response.title == "Fake Post Title"
    assert response.body == "This is a fake post body for testing purposes."
    assert response.userId == 1


def test_requests_requestor():
    """Test the requests-based requestor with real API."""
    # Create API operation for getting a post (simplified - no query params for now)
    GetPostEndpoint = build_api_operation(
        method=HttpMethods.GET,
        url_template=Template("https://jsonplaceholder.typicode.com/posts/${post_id}"),
        path_params_constructor=PostPathParams,
        payload_constructor=PostPathParams,  # Use same model for both path and payload for GET
        response_model_type=PostResponse,
    )

    # Create requests requestor
    RequestsPostRequestor = build_request_requestor(
        operation_type=GetPostEndpoint,
        combined_model=PostPathParams,  # Simplified combined model
    )

    # Test the requests requestor
    response = RequestsPostRequestor.request(
        context=RequestContext(headers={"Content-Type": "application/json"}), post_id=1
    )

    # Assertions
    assert isinstance(response, PostResponse)
    assert response.id == 1
    assert response.userId == 1
    assert isinstance(response.title, str)
    assert isinstance(response.body, str)
    assert len(response.title) > 0
    assert len(response.body) > 0


def test_httpx_requestor():
    """Test the httpx-based requestor with real API."""
    # Create API operation for getting a post
    GetPostEndpoint = build_api_operation(
        method=HttpMethods.GET,
        url_template=Template("https://jsonplaceholder.typicode.com/posts/${post_id}"),
        path_params_constructor=PostPathParams,
        payload_constructor=PostPathParams,  # Use same model for both
        response_model_type=PostResponse,
    )

    # Create httpx requestor
    HttpxPostRequestor = build_httpx_requestor(
        operation_type=GetPostEndpoint,
        combined_model=PostPathParams,  # Simplified
    )

    # Test the httpx requestor (sync)
    response = HttpxPostRequestor.request(
        context=RequestContext(headers={"Content-Type": "application/json"}), post_id=2
    )

    # Assertions
    assert isinstance(response, PostResponse)
    assert response.id == 2
    assert response.userId == 1
    assert isinstance(response.title, str)
    assert isinstance(response.body, str)
    assert len(response.title) > 0
    assert len(response.body) > 0


async def test_httpx_async_requestor():
    """Test the httpx-based async requestor with real API."""
    # Create API operation for getting a post
    GetPostEndpoint = build_api_operation(
        method=HttpMethods.GET,
        url_template=Template("https://jsonplaceholder.typicode.com/posts/${post_id}"),
        path_params_constructor=PostPathParams,
        payload_constructor=PostPathParams,  # Use same model
        response_model_type=PostResponse,
    )

    # Create httpx requestor
    HttpxPostRequestor = build_httpx_requestor(
        operation_type=GetPostEndpoint,
        combined_model=PostPathParams,  # Simplified
    )

    # Test the httpx requestor (async)
    response = await HttpxPostRequestor.request_async(
        context=RequestContext(headers={"Content-Type": "application/json"}), post_id=3
    )

    # Assertions
    assert isinstance(response, PostResponse)
    assert response.id == 3
    assert response.userId == 1
    assert isinstance(response.title, str)
    assert isinstance(response.body, str)
    assert len(response.title) > 0
    assert len(response.body) > 0


async def test_aiohttp_requestor():
    """Test the aiohttp-based async requestor with real API."""
    # Create API operation for getting a post
    GetPostEndpoint = build_api_operation(
        method=HttpMethods.GET,
        url_template=Template("https://jsonplaceholder.typicode.com/posts/${post_id}"),
        path_params_constructor=PostPathParams,
        payload_constructor=PostPathParams,  # Use same model
        response_model_type=PostResponse,
    )

    # Create aiohttp requestor
    AiohttpPostRequestor = build_aiohttp_requestor(
        operation_type=GetPostEndpoint,
        combined_model=PostPathParams,  # Simplified
    )

    # Test the aiohttp requestor (async)
    response = await AiohttpPostRequestor.request_async(
        context=RequestContext(headers={"Content-Type": "application/json"}), post_id=4
    )

    # Assertions
    assert isinstance(response, PostResponse)
    assert response.id == 4
    assert response.userId == 1
    assert isinstance(response.title, str)
    assert isinstance(response.body, str)
    assert len(response.title) > 0
    assert len(response.body) > 0


def test_post_request():
    """Test a POST request with real API."""
    # Create API operation for creating a post
    CreatePostEndpoint = build_api_operation(
        method=HttpMethods.POST,
        url_template=Template("https://jsonplaceholder.typicode.com/posts"),
        path_params_constructor=PostPathParams,  # Not used for POST
        payload_constructor=CreatePostPayload,
        response_model_type=CreatePostResponse,
    )

    # Create requests requestor for POST
    CreatePostRequestor = build_request_requestor(
        operation_type=CreatePostEndpoint,
        combined_model=CombinedCreatePostParams,
    )

    # Test the POST request
    response = CreatePostRequestor.request(
        context=RequestContext(headers={"Content-Type": "application/json"}),
        post_id=0,  # Not used for POST
        title="Test Post Title",
        body="This is a test post body created via the endpoint requestor.",
        userId=1,
    )

    # Assertions
    assert isinstance(response, CreatePostResponse)
    assert response.id == 101  # JSONPlaceholder returns 101 for new posts
    assert response.title == "Test Post Title"
    assert (
        response.body == "This is a test post body created via the endpoint requestor."
    )
    assert response.userId == 1


def test_build_requestor_factory():
    """Test the build_requestor factory function."""
    # Create API operation
    GetPostEndpoint = build_api_operation(
        method=HttpMethods.GET,
        url_template=Template("https://jsonplaceholder.typicode.com/posts/${post_id}"),
        path_params_constructor=PostPathParams,
        payload_constructor=PostQueryParams,
        response_model_type=PostResponse,
    )

    # Test factory with requests type
    FactoryRequestor = build_requestor(
        requestor_type=RequestorType.REQUESTS,
        operation_type=GetPostEndpoint,
        combined_model=PostPathParams,  # Simplified
    )

    response = FactoryRequestor.request(
        context=RequestContext(headers={"Content-Type": "application/json"}), post_id=5
    )

    # Assertions for requests factory
    assert isinstance(response, PostResponse)
    assert response.id == 5
    assert response.userId == 1
    assert isinstance(response.title, str)
    assert isinstance(response.body, str)
    assert len(response.title) > 0
    assert len(response.body) > 0

    # Test factory with fake type
    FactoryFakeRequestor = build_requestor(
        requestor_type=RequestorType.FAKE,
        operation_type=GetPostEndpoint,
        combined_model=PostPathParams,  # Simplified
        return_value={
            "id": 999,
            "title": "Factory Fake Post",
            "body": "This is a fake post from the factory.",
            "userId": 999,
        },
    )

    response = FactoryFakeRequestor.request(
        context=RequestContext(headers={"Content-Type": "application/json"}),
        post_id=999,
    )

    # Assertions for fake factory
    assert isinstance(response, PostResponse)
    assert response.id == 999
    assert response.title == "Factory Fake Post"
    assert response.body == "This is a fake post from the factory."
    assert response.userId == 999
