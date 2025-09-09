import os
from unittest.mock import Mock

import pytest

from unique_toolkit._common.tracing_frameworks.opik import (
    LangChainTracer,
    get_langchain_tracer,
)
from unique_toolkit._common.tracing_frameworks.opik.track import get_tracking_decorator

##############################################################################
# Test tracing functionality to ensure it does not break production code.
# Opik is not available in the test environment and thus not tested
##############################################################################


# Get the no-op track decorator
@pytest.fixture
def prod_track():
    os.environ["ENABLE_OPIK"] = "True"
    os.environ["ENV"] = "prod"
    return get_tracking_decorator()


# Get the no-op track decorator
@pytest.fixture
def prod_no_track():
    os.environ["ENABLE_OPIK"] = "False"
    os.environ["ENV"] = "prod"
    return get_tracking_decorator()


# Test simple decorator usage (@track)
@pytest.mark.parametrize("track_fixture", ["prod_track", "prod_no_track"])
def test_simple_decorator(request, track_fixture):
    track = request.getfixturevalue(track_fixture)

    @track
    def test_func():
        return "test_func called"

    result = test_func()
    assert result == "test_func called"


# Test simple decorator usage (@track())
@pytest.mark.parametrize("track_fixture", ["prod_track", "prod_no_track"])
def test_simple_decorator_called(request, track_fixture):
    track = request.getfixturevalue(track_fixture)

    @track()
    def test_func():
        return "test_func called"

    result = test_func()
    assert result == "test_func called"


# Test decorator with arguments (@track(...))
@pytest.mark.parametrize("track_fixture", ["prod_track", "prod_no_track"])
def test_decorator_with_args(request, track_fixture):
    track = request.getfixturevalue(track_fixture)

    @track(project_name="test", experiment_name="test")
    def test_func():
        return "test_func called"

    result = test_func()
    assert result == "test_func called"


# Test function call usage (track(func))
@pytest.mark.parametrize("track_fixture", ["prod_track", "prod_no_track"])
def test_function_call(request, track_fixture):
    track = request.getfixturevalue(track_fixture)

    def test_func():
        return "test_func called"

    wrapped_func = track(test_func)
    result = wrapped_func()
    assert result == "test_func called"


# Test with arguments to the decorated function
@pytest.mark.parametrize("track_fixture", ["prod_track", "prod_no_track"])
def test_with_function_args(request, track_fixture):
    track = request.getfixturevalue(track_fixture)

    @track
    def test_func(arg1, arg2=None):
        return f"test_func called with {arg1} and {arg2}"

    result = test_func("value1", arg2="value2")
    assert result == "test_func called with value1 and value2"


# Test with class methods
@pytest.mark.parametrize("track_fixture", ["prod_track", "prod_no_track"])
def test_class_method(request, track_fixture):
    track = request.getfixturevalue(track_fixture)

    class TestClass:
        @track
        def test_method(self):
            return "test_method called"

    obj = TestClass()
    result = obj.test_method()
    assert result == "test_method called"


##############################################################################
# Test LangGraph/LangChain tracing integration
##############################################################################


@pytest.fixture
def opik_disabled_env():
    """Set environment for Opik disabled."""
    original_enable = os.environ.get("ENABLE_OPIK")
    original_env = os.environ.get("ENV")

    os.environ["ENABLE_OPIK"] = "False"
    os.environ["ENV"] = "prod"

    yield

    # Cleanup
    if original_enable is not None:
        os.environ["ENABLE_OPIK"] = original_enable
    else:
        os.environ.pop("ENABLE_OPIK", None)

    if original_env is not None:
        os.environ["ENV"] = original_env
    else:
        os.environ.pop("ENV", None)


def test_langchain_tracer_when_disabled(opik_disabled_env):
    """Test that we get a no-op tracer when Opik is disabled."""
    tracer_class = get_langchain_tracer()
    tracer = tracer_class(graph=Mock(), project_name="test")

    # Should work without errors
    assert tracer is not None

    # Should be callable
    result = tracer("test")  # type: ignore
    assert result == tracer

    # Should handle method chaining
    chained = tracer.method1().method2()  # type: ignore
    assert chained == tracer


def test_pre_instantiated_langchain_tracer(opik_disabled_env):
    """Test the pre-instantiated LangchainTracer."""
    tracer = LangChainTracer(graph=Mock())
    assert tracer is not None

    # Should handle any method calls
    result = tracer.some_method()  # type: ignore
    assert result == tracer
