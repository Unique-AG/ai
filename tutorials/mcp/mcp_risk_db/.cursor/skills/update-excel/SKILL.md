# Risk Database MCP: Update bundled Excel

Use when replacing the bundled Excel file with a new version (e.g. from Downloads) and redeploying the Azure app.

## Steps

1. **Compare new Excel vs current**  
   - Inspect new file: sheet names, column names per sheet, row counts.  
   - Compare to current `data/risk_database.xlsx`: same sheets? same columns? any renames/added/removed?  
   - If only row-count or data changes (no new/removed sheets, no column renames): no code change.  
   - If columns renamed or sheets added/removed: decide if server.py or tool descriptions need updates (generic tools usually need none).

2. **Replace Excel**  
   - Copy new file to `data/risk_database.xlsx` (overwrite).  
   - Example: `cp "/Users/tinoroz/Downloads/Ascendant_Risk_Database (date).xlsx" data/risk_database.xlsx`

3. **Deploy**  
   - From project root: `./deploy.sh`  
   - Wait for the build and web app update to finish.

4. **Restart instance**   
   - `az webapp restart -n risk-db-mcp-app -g rg-lab-demo-001-risk-db-mcp`  
   - On startup the app reloads Excel into memory and **re-syncs the Postgres mirror** (if configured).

5. **Verify**  
   - Tell user to watch Azure logs after restart.  
   - Summarize Excel differences and suggest 1–2 Unique AI test queries that would surface those changes (e.g. new column, new sheet, or “show recent pnl” if more rows).

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
