# Analytics Order API

The Analytics Order API generates and manages async analytics reports (e.g. chat usage exports) for a company.

## Overview

Create and manage analytics orders with:

- Report generation for configurable date ranges and types
- Optional filtering by assistant
- Status polling until completion
- CSV download once the order is done

## Analytics types

Report `type` must be one of the strings in [`AnalyticsOrder.ANALYTICS_TYPE_VALUES`](#analytics-type-literal). The static type of `type` is [`AnalyticsOrder.AnalyticsTypeLiteral`](#analytics-type-literal) (a `Literal[...]` of the same set), matching the product **AnalyticsType** values:

`ACTIVE_USER`, `CHAT_INTERACTION`, `CHAT_INTERACTION_DETAILED`, `INGESTION_STAT`, `MODEL_USAGE`, `NPS`, `PRODUCT_METRICS`, `REFERENCE_STAT`, `USER_CHAT_EXPORT`.

## Methods

??? example "`unique_sdk.AnalyticsOrder.create` - Create an analytics order"

    Start a new analytics order. The order is processed asynchronously — poll `retrieve` until `state` reaches `DONE` or `ERROR`.

    **Parameters:**

    - `type` (str, required) - Analytics type; must be a member of [Analytics types](#analytics-types) (e.g. `"CHAT_INTERACTION"`)
    - `startDate` (str, required) - Report start date in ISO 8601 format (e.g. `"2024-01-01"`)
    - `endDate` (str, required) - Report end date in ISO 8601 format (e.g. `"2024-12-31"`)
    - `assistantId` (str, optional) - Filter the report to a specific assistant

    **Returns:**

    Returns an [`AnalyticsOrder`](#analyticsorder) object.

    **Example:**

    ```python
    order = unique_sdk.AnalyticsOrder.create(
        user_id=user_id,
        company_id=company_id,
        type="CHAT_INTERACTION",
        startDate="2024-01-01",
        endDate="2024-12-31",
    )
    print(order["id"], order["state"])  # e.g. "ord_abc123", "PENDING"
    ```

    **Scoped to an assistant:**

    ```python
    order = unique_sdk.AnalyticsOrder.create(
        user_id=user_id,
        company_id=company_id,
        type="CHAT_INTERACTION",
        startDate="2024-01-01",
        endDate="2024-12-31",
        assistantId="asst_xyz789",
    )
    ```

??? example "`unique_sdk.AnalyticsOrder.list` - List analytics orders"

    List analytics orders for the company, sorted by creation date descending.

    **Parameters:**

    - `skip` (int, optional) - Number of orders to skip (default: `0`)
    - `take` (int, optional) - Number of orders to return (default: `20`, max: `100`)

    **Returns:**

    Returns a list of [`AnalyticsOrder`](#analyticsorder) objects.

    **Example:**

    ```python
    orders = unique_sdk.AnalyticsOrder.list(
        user_id=user_id,
        company_id=company_id,
        skip=0,
        take=20,
    )
    for order in orders:
        print(order["id"], order["state"])
    ```

??? example "`unique_sdk.AnalyticsOrder.retrieve` - Get an analytics order"

    Fetch a single analytics order by ID. Use this to poll for status changes.

    **Parameters:**

    - `order_id` (str, required) - Analytics order ID

    **Returns:**

    Returns an [`AnalyticsOrder`](#analyticsorder) object.

    **Example:**

    ```python
    order = unique_sdk.AnalyticsOrder.retrieve(
        user_id=user_id,
        company_id=company_id,
        order_id="ord_abc123",
    )
    print(order["state"])  # "PENDING" | "RUNNING" | "DONE" | "ERROR"
    ```

??? example "`unique_sdk.AnalyticsOrder.delete` - Delete an analytics order"

    Delete an analytics order by ID.

    **Parameters:**

    - `order_id` (str, required) - Analytics order ID

    **Returns:**

    Returns the deleted [`AnalyticsOrder`](#analyticsorder) object.

    **Example:**

    ```python
    deleted = unique_sdk.AnalyticsOrder.delete(
        user_id=user_id,
        company_id=company_id,
        order_id="ord_abc123",
    )
    print(deleted["id"])
    ```

??? example "`unique_sdk.AnalyticsOrder.download` - Download analytics order CSV"

    Download the CSV content of a completed analytics order. The order must be in `DONE` state.

    **Parameters:**

    - `order_id` (str, required) - Analytics order ID

    **Returns:**

    Returns the CSV content as a `str`.

    **Example:**

    ```python
    csv_content = unique_sdk.AnalyticsOrder.download(
        user_id=user_id,
        company_id=company_id,
        order_id="ord_abc123",
    )
    with open("report.csv", "w") as f:
        f.write(csv_content)
    ```

## Use Cases

??? example "List and clean up old orders"

    ```python
    import unique_sdk

    orders = unique_sdk.AnalyticsOrder.list(
        user_id=user_id,
        company_id=company_id,
        take=100,
    )

    for order in orders:
        if order["state"] == "ERROR":
            unique_sdk.AnalyticsOrder.delete(user_id, company_id, order["id"])
            print(f"Deleted failed order: {order['id']}")
    ```

## Return Types

#### AnalyticsTypeLiteral and ANALYTICS_TYPE_VALUES {#analytics-type-literal}

`AnalyticsOrder` exposes:

- `AnalyticsTypeLiteral` — a `typing.Literal[...]` of the allowed `type` strings.
- `ANALYTICS_TYPE_VALUES` — a `tuple[str, ...]` of the same strings (suitable for membership checks, UI dropdowns, or validation at runtime).

#### AnalyticsOrder {#analyticsorder}

??? note "The `AnalyticsOrder` object represents an analytics report order"

    **Fields:**

    - `id` (str) - Unique order identifier
    - `type` (str) - Analytics type (one of the values in [Analytics types](#analytics-types))
    - `state` (str) - Current state: `"PENDING"`, `"RUNNING"`, `"DONE"`, or `"ERROR"`
    - `configuration` (dict) - Order configuration (includes `startDate`, `endDate`, and optionally `assistantId`)
    - `createdAt` (str) - Creation timestamp (ISO 8601)
    - `updatedAt` (str) - Last update timestamp (ISO 8601)
    - `stateUpdatedAt` (str) - Timestamp of the last state change (ISO 8601)
    - `object` (str) - Always `"analytics-order"`

    **Returned by:** `AnalyticsOrder.create()`, `AnalyticsOrder.retrieve()`, `AnalyticsOrder.delete()`

## Related Resources

- [Analytics order run utility](../utilities/analytics_order_run.md) - End-to-end create → poll → download helper
- [Benchmarking API](benchmarking.md) - Similar async job pattern for xlsx benchmarking
