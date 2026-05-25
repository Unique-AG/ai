import httpx

_EVALUATE_FLAG_QUERY = "query EvaluateFlag($key: String!) { evaluateFlag(key: $key) }"

_TIMEOUT = httpx.Timeout(2.0, connect=1.0)


async def evaluate_flag(
    *,
    url: str,
    flag: str,
    service_id: str,
    company_id: str,
    user_id: str | None,
) -> bool:
    """Call configuration-backend's ``evaluateFlag`` GraphQL query.

    Args:
        url: Base URL of configuration-backend (no trailing slash).
        flag: Upper-snake flag key, e.g. ``FEATURE_FLAG_ENABLE_MY_FEATURE``.
        service_id: Value sent as ``x-service-id`` header.
        company_id: Value sent as ``x-company-id`` header.
        user_id: Value sent as ``x-user-id`` header. Omitted when ``None``.

    Returns:
        The boolean evaluation result from the server.

    Raises:
        httpx.HTTPError: On transport or HTTP-level errors.
        RuntimeError: On GraphQL errors or a non-boolean response value.
    """
    headers: dict[str, str] = {
        "x-service-id": service_id,
        "x-company-id": company_id,
        "Content-Type": "application/json",
    }
    if user_id is not None:
        headers["x-user-id"] = user_id

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        response = await client.post(
            f"{url}/graphql",
            json={"query": _EVALUATE_FLAG_QUERY, "variables": {"key": flag}},
            headers=headers,
        )
        response.raise_for_status()
        data = response.json()

    if "errors" in data:
        raise RuntimeError(f"GraphQL error evaluating '{flag}': {data['errors']}")

    value = data.get("data", {}).get("evaluateFlag")
    if not isinstance(value, bool):
        raise RuntimeError(
            f"evaluateFlag returned unexpected value for '{flag}': {value!r}"
        )
    return value
