!!! warning "Experimental"

    The `Identity` service lives under `unique_toolkit.experimental.identity`.
    Its public API, method names, argument shapes, and return types may change
    without notice and are **not** covered by the toolkit's normal stability
    guarantees. Pin your toolkit version if you depend on a specific shape.

    Import it via:

    ```python
    from unique_toolkit.experimental.identity import Identity
    # or, with sub-services:
    from unique_toolkit.experimental.identity import Identity, Users, Groups
    ```

    `Identity` is a thin facade — it wires two CRUD-style sub-services,
    [`Users`](#unique_toolkit.experimental.identity.service.Users) and
    [`Groups`](#unique_toolkit.experimental.identity.service.Groups), behind
    `identity.users` and `identity.groups` respectively. Constructors are
    keyword-only, so callers always write `Identity(user_id=..., company_id=...)`.

### Service
::: unique_toolkit.experimental.identity.service

### Schemas
::: unique_toolkit.experimental.identity.schemas
