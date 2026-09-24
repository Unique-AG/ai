# Risk Database MCP: Update bundled Excel

Use when replacing the bundled Excel file with a new version (e.g. from Downloads) and redeploying the Azure app.

## Execution policy

When the user asks to update or deploy the workbook, execute the deployment, restart, health wait, and QA verification. Do not merely return commands unless the user explicitly asks for commands only. Never print or pass API keys on a command line.

The QA verification uses:

- Space: `assistant_a9csiq8hbd10xnojpqlk6980`
- Keychain service: `unique-qa-public-api`
- Keychain account: `app_le7m7o2w3zurin746dpx88ro`
- Script: `.cursor/skills/update-excel/scripts/verify_qa_space.py`

One-time credential setup must be performed by the user in their terminal so the key is entered through Keychain's secure prompt:

```bash
security add-generic-password -U \
  -s unique-qa-public-api \
  -a app_le7m7o2w3zurin746dpx88ro \
  -w
```

## Steps

1. **Compare new Excel vs current**  
   - Inspect new file: sheet names, column names per sheet, row counts.  
   - Compare to current `data/risk_database.xlsx`: same sheets? same columns? any renames/added/removed?  
   - If only row-count or data changes (no new/removed sheets, no column renames): no code change.  
   - If columns renamed or sheets added/removed: decide if server.py or tool descriptions need updates (generic tools usually need none).

2. **Archive the current Excel**
   - Determine the latest data month in the current workbook from its snapshot/date columns.
   - Copy the current workbook to `data/risk_database_YYYY-MM.xlsx` before replacing it.
   - Use the data month, not the current month, and never overwrite an existing archive.
   - Example: `test ! -e data/risk_database_2026-06.xlsx && cp data/risk_database.xlsx data/risk_database_2026-06.xlsx`

3. **Replace Excel**
   - Copy the new file to `data/risk_database.xlsx` (overwrite).
   - Example: `cp "/Users/tinoroz/Downloads/Ascendant_Risk_Database (date).xlsx" data/risk_database.xlsx`
   - If the new file was staged in `data/` under another name, remove that duplicate only after confirming it matches the canonical workbook.
   - Example: `cmp -s data/NEW_FILE.xlsx data/risk_database.xlsx && rm data/NEW_FILE.xlsx`

4. **Capture a QA baseline**
   - Run `uv run .cursor/skills/update-excel/scripts/verify_qa_space.py --observe`.
   - Save the non-secret response in the task summary so the post-deployment result can be compared with it.

5. **Deploy**
   - From the project root, run `./deploy.sh`.
   - Wait for the command to finish and require a successful exit code.

6. **Restart instance**
   - Run `az webapp restart -n risk-db-mcp-app -g rg-lab-demo-001-risk-db-mcp`.
   - On startup the app reloads Excel into memory and **re-syncs the Postgres mirror** (if configured).

7. **Wait for health**
   - Poll `https://risk-db-mcp-app.azurewebsites.net/` every 10 seconds for up to 10 minutes.
   - Do not run the QA verification until the endpoint returns HTTP 200 with `{"server":"running","name":"risk-database-mcp"}`.
   - Treat timeout or an unexpected health response as a failed deployment and inspect the Azure log stream.

8. **Verify through the QA space**
   - Run `uv run .cursor/skills/update-excel/scripts/verify_qa_space.py`.
   - The script sends one prompt through the Unique SDK, requires the connected MCP to query `pnl_daily`, and checks the response for the expected `2026-09-22` values.
   - If the response reports `MCP server not found`, `session expired`, or requests reconnection, ask the user to open the QA space and manually reconnect the MCP. Wait for confirmation, then rerun the same verification without redeploying or restarting.
   - A non-zero exit code means the deployed MCP was not verified; inspect the response and Azure logs.

9. **Report**
   - Report the workbook differences, deployment result, health result, and QA answer.
   - State explicitly whether the QA answer contained the updated data.

## Comparison script (run from project root)

```python
uv run python -c "
import pandas as pd
from pathlib import Path
new_path = Path('/Users/tinoroz/Downloads/NEW_FILE.xlsx')
old_path = Path('data/risk_database.xlsx')
def inspect(p):
    x = pd.ExcelFile(p)
    return {n: {'cols': list(pd.read_excel(x, sheet_name=n).columns), 'rows': len(pd.read_excel(x, sheet_name=n))} for n in x.sheet_names}
new, old = inspect(new_path), inspect(old_path)
for name in sorted(set(new) | set(old)):
    cn, co = new.get(name, {}).get('cols', []), old.get(name, {}).get('cols', [])
    rn, ro = new.get(name, {}).get('rows', 0), old.get(name, {}).get('rows', 0)
    if set(cn) != set(co) or rn != ro:
        print(name, 'cols:', set(cn) - set(co), 'vs', set(co) - set(cn), 'rows:', rn, 'vs', ro)
"
```

Replace `NEW_FILE.xlsx` with the actual new filename (e.g. `Ascendant_Risk_Database (03.16.2026)_Updated.xlsx`).
