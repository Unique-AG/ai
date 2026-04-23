# Analytics Order API

Create, monitor, and download analytics reports (e.g. chat usage exports) as **analytics orders**. An order is an async job: you create it, poll until it reaches `DONE` or `ERROR`, then download the CSV result.

Use `unique_sdk.AnalyticsOrder`:

- **`create` / `create_async`** — start a new analytics order. Required: `type`, `start_date`, `end_date`. Optional: `assistant_id` to scope the report to a single assistant.
- **`list` / `list_async`** — list orders for the company. Optional `skip` and `take` for pagination (default page size: 20, max: 100).
- **`retrieve` / `retrieve_async`** — fetch a single order by ID (poll this for status changes).
- **`delete` / `delete_async`** — cancel and remove an order.
- **`download` / `download_async`** — fetch the CSV content as a string. The order must be in `DONE` state.

## Order lifecycle

```
PENDING → RUNNING → DONE
                 ↘ ERROR
```

Poll `retrieve` until `state` is `"DONE"` or `"ERROR"`, then call `download` to get the CSV.

## Examples

### Create an order

```python
import unique_sdk

order = unique_sdk.AnalyticsOrder.create(
    user_id=user_id,
    company_id=company_id,
    type="CHAT_ANALYTICS",
    start_date="2024-01-01",
    end_date="2024-12-31",
)
print(order["id"], order["state"])  # e.g. "ord_abc123", "PENDING"
```

### Poll until done, then download CSV

```python
import time
import unique_sdk

order_id = order["id"]
while True:
    order = unique_sdk.AnalyticsOrder.retrieve(user_id, company_id, order_id)
    if order["state"] in ("DONE", "ERROR"):
        break
    time.sleep(5)

if order["state"] == "DONE":
    csv_text = unique_sdk.AnalyticsOrder.download(user_id, company_id, order_id)
    with open("report.csv", "w") as f:
        f.write(csv_text)
```

### List orders

```python
orders = unique_sdk.AnalyticsOrder.list(
    user_id=user_id,
    company_id=company_id,
    skip=0,
    take=20,
)
for o in orders:
    print(o["id"], o["state"])
```

### Delete an order

```python
unique_sdk.AnalyticsOrder.delete(user_id, company_id, order_id)
```

Async: use the same names with `_async` and `await`.

To create an order, wait for it to finish, and save the CSV in one call, use the [Analytics order run utility](../utilities/analytics_order_run.md).
