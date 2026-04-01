# Benchmarking API

Run benchmarking on **xlsx** files: send a workbook for processing, see how far along the run is, fetch the filled-in result, or download a blank template to fill in.

Use `unique_sdk.Benchmarking`:

- **`process_upload` / `process_upload_async`** — submit a file (`bytes` + `filename`). Optional `force` if you need to replace or re-queue work the API allows to override.
- **`get_status` / `get_status_async`** — read progress (fields depend on the backend; often includes counts like `done` / `total`).
- **`download_processed` / `download_processed_async`** — save the processed xlsx under a temp directory (same layout as `file_io.download_file`) and return that `pathlib.Path`.
- **`download_template` / `download_template_async`** — same for the starter template.

```python
import unique_sdk

with open("benchmark.xlsx", "rb") as f:
    data = f.read()
uploaded = unique_sdk.Benchmarking.process_upload(
    user_id=user_id,
    company_id=company_id,
    file=data,
    filename="benchmark.xlsx",
    force=True,
)

status = unique_sdk.Benchmarking.get_status(user_id=user_id, company_id=company_id)

result_path = unique_sdk.Benchmarking.download_processed(
    user_id=user_id,
    company_id=company_id,
)

template_path = unique_sdk.Benchmarking.download_template(
    user_id=user_id,
    company_id=company_id,
)
```

Async: use the same names with `_async` and `await`.

To upload a path on disk, wait until processing finishes, and optionally write the result file in one go, use the [Benchmarking run utility](../utilities/benchmarking_run.md).
