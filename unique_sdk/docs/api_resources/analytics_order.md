# Analytics Order API

The Analytics Order API generates and manages async analytics reports (e.g. chat usage exports) for a company.

## Overview

Create and manage analytics orders with:

- Report generation for configurable date ranges and types
- Optional filtering by assistant
- Status polling until completion
- CSV download once the order is done

## Methods

??? example "`unique_sdk.AnalyticsOrder.create` - Create an analytics order"

    Start a new analytics order. The order is processed asynchronously — poll `retrieve` until `state` reaches `DONE` or `ERROR`.

    **Parameters:**

    - `type` (str, required) - Analytics type (e.g. `"CHAT_ANALYTICS"`)
    - `start_date` (str, required) - Report start date in ISO 8601 format (e.g. `"2024-01-01"`)
    - `end_date` (str, required) - Report end date in ISO 8601 format (e.g. `"2024-12-31"`)
    - `assistant_id` (str, optional) - Filter the report to a specific assistant

    **Returns:**

    Returns an [`AnalyticsOrder`](#analyticsorder) object.

    **Example:**

    ```python
    order = unique_sdk.AnalyticsOrder.create(
        user_id=user_id,
        company_id=company_id,
        type="CHAT_ANALYTICS",
        start_date="2024-01-01",
        end_date="2024-12-31",
    )
    print(order["id"], order["state"])  # e.g. "ord_abc123", "PENDING"
    ```

    **Scoped to an assistant:**

    ```python
    order = unique_sdk.AnalyticsOrder.create(
        user_id=user_id,
        company_id=company_id,
        type="CHAT_ANALYTICS",
        start_date="2024-01-01",
        end_date="2024-12-31",
        assistant_id="asst_xyz789",
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

#### AnalyticsOrder {#analyticsorder}

??? note "The `AnalyticsOrder` object represents an analytics report order"

    **Fields:**

    - `id` (str) - Unique order identifier
    - `type` (str) - Analytics type (e.g. `"CHAT_ANALYTICS"`)
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
