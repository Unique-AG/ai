# Benchmarking API

The Benchmarking API runs evaluation jobs for xlsx workbooks.

Use `unique_sdk.Benchmarking` to:

- upload an input workbook,
- check run status,
- download the processed result workbook,
- download the starter template workbook.

## Methods

??? example "`unique_sdk.Benchmarking.process_upload` - Upload benchmarking workbook"

    Upload an xlsx file for benchmarking processing.

    **Parameters:**

    - `user_id` (str, required) - User identifier
    - `company_id` (str, required) - Company identifier
    - `file` (bytes, required) - Workbook bytes
    - `filename` (str, required) - Uploaded file name (for example `benchmark.xlsx`)
    - `force` (bool, optional) - If set, requests replacement/re-queue where supported by the backend

    **Returns:**

    - `Benchmarking.ProcessUploadResponse` with `benchmarkStatus` (`done`, `error`, `total`)

    **Example:**

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
    print(uploaded)
    ```

??? example "`unique_sdk.Benchmarking.get_status` - Read benchmarking status"

    Read the current status snapshot for the company.

    **Parameters:**

    - `user_id` (str, required) - User identifier
    - `company_id` (str, required) - Company identifier

    **Returns:**

    - `Benchmarking.StatusSnapshot` with fields such as `done`, `error`, `total`, `filename`, `status`

    **Example:**

    ```python
    status = unique_sdk.Benchmarking.get_status(
        user_id=user_id,
        company_id=company_id,
    )
    print(status)
    ```

??? example "`unique_sdk.Benchmarking.download_processed` - Download processed workbook"

    Download the generated result workbook to a temporary file path.

    **Parameters:**

    - `user_id` (str, required) - User identifier
    - `company_id` (str, required) - Company identifier
    - `filename` (str, optional) - Local output filename (default: `benchmarking_result.xlsx`)

    **Returns:**

    - `pathlib.Path` to the downloaded file

    **Example:**

    ```python
    result_path = unique_sdk.Benchmarking.download_processed(
        user_id=user_id,
        company_id=company_id,
    )
    print(result_path)
    ```

??? example "`unique_sdk.Benchmarking.download_template` - Download template workbook"

    Download the input template workbook to a temporary file path.

    **Parameters:**

    - `user_id` (str, required) - User identifier
    - `company_id` (str, required) - Company identifier
    - `filename` (str, optional) - Local output filename (default: `benchmarking_template.xlsx`)

    **Returns:**

    - `pathlib.Path` to the downloaded file

    **Example:**

    ```python
    template_path = unique_sdk.Benchmarking.download_template(
        user_id=user_id,
        company_id=company_id,
    )
    print(template_path)
    ```

## Async variants

Every method also has an async counterpart:

- `process_upload_async`
- `get_status_async`
- `download_processed_async`
- `download_template_async`

## Utility helper

For end-to-end flow from local path (upload, poll until done, optional save), use [Benchmarking run utility](../utilities/benchmarking_run.md).
