import logging
import os

logger = logging.getLogger(__name__)


def _create_tracking_decorator(opik_enabled: bool):
    if opik_enabled:
        try:
            from opik import track
        except ImportError as e:
            logger.error(
                "OPIK is not installed, but enabled in the environment. Please install the dependency or disable OPIK"
            )
            raise e

        return track
    else:
        # A simple no-op decorator that accepts any arguments and just returns the function
        def no_op_track(*args, **kwargs):
            # If called with no arguments or first arg is not callable (@track or track())
            if not args or not callable(args[0]):

                def decorator(func):
                    return func

                return decorator

            # If called with function as first argument (track(func))
            return args[0]

        return no_op_track


def get_tracking_decorator():
    """
    Get the tracking decorator as per the environment and the settings.
    """
    return _create_tracking_decorator(is_opik_enabled())


def is_opik_enabled():
    """
    Check if OPIK is enabled and the environment is local.
    """
    return (
        os.environ.get("ENABLE_OPIK") == "True"
        and os.environ.get("ENV") is not None
        and os.environ.get("ENV", "").lower() == "local"
    )


def _get_opik_context():
    """
    Get the OPIK context as per the environment and the settings.
    """
    from opik import opik_context

    return opik_context


def update_current_trace(**kwargs):
    """
    Configure the OPIK context. Has to be called with opik "update_current_span" arguments
    """
    if not is_opik_enabled():
        return
    opik_context = _get_opik_context()
    opik_context.update_current_span(**kwargs)


def get_langchain_tracer():
    """
    Get a LangGraph tracer that works in any environment.

    Returns:
        OpikTracer class if enabled, otherwise a no-op tracer class

    Example:
        ```python
        from unique_toolkit._common.tracing_frameworks.opik import get_langchain_tracer

        tracer = get_langchain_tracer()(graph=app.get_graph(xray=True))
        result = app.invoke(inputs, config={"callbacks": [tracer]})
        ```
    """
    if is_opik_enabled():
        try:
            from opik.integrations.langchain import OpikTracer

            return OpikTracer
        except ImportError:
            logger.warning(
                "OPIK enabled but not installed. Using no-op tracer. Install opik for tracing."
            )

    # Simple no-op tracer (used when disabled OR when import fails)
    class NoOpTracer:
        def __init__(self, *args, **kwargs):
            pass

        def __call__(self, *args, **kwargs):
            return self

        def __getattr__(self, name):
            return lambda *args, **kwargs: self

    return NoOpTracer


LangChainTracer = get_langchain_tracer()
track = get_tracking_decorator()
