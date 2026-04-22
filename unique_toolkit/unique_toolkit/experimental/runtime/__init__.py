"""App bootstrap and runtime plumbing.

Nothing here owns domain logic — this is how you *stand up* a Unique app:
settings, env discovery, logging, SDK init, FastAPI factory, webhook and
verification middleware, performance timers, monitoring, and protocol
support helpers.

Planned contents (current home → new home):

* settings, env discovery, logging, SDK init, FastAPI factory, webhook,
  verification ← :mod:`unique_toolkit.app`
* ``performance`` ← :mod:`unique_toolkit.app.performance`
* ``monitoring``  ← :mod:`unique_toolkit.monitoring`
* ``protocols``   ← :mod:`unique_toolkit.protocols`
"""
