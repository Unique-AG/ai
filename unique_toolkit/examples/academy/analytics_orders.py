# %%
# =============================================================================
# Unique Academy — Analytics Orders
# =============================================================================
#
# In this session you will learn how to:
#   1. Create an analytics order for a date range
#   2. Poll the order until it finishes
#   3. Download the CSV result
#   4. List and clean up orders
#   5. Run the full flow in one call with the utility helper
#
# Prerequisites
# -------------
# - unique-sdk installed  (`pip install unique-sdk`)
# - UNIQUE_API_KEY, UNIQUE_APP_ID, UNIQUE_USER_ID, UNIQUE_COMPANY_ID set
#   in your environment (or fill in the variables below directly)
#
# Analytics orders are *asynchronous jobs*. You create one, the platform
# processes it in the background, and you fetch the result once done.
# The state machine is:
#
#   PENDING → RUNNING → DONE
#                    ↘ ERROR
# =============================================================================

import asyncio
import os
import time

import unique_sdk
from unique_sdk.utils.analytics_order_run import run_analytics_order

unique_sdk.api_key = os.environ["UNIQUE_API_KEY"]
unique_sdk.app_id  = os.environ["UNIQUE_APP_ID"]

USER_ID    = os.environ["UNIQUE_USER_ID"]
COMPANY_ID = os.environ["UNIQUE_COMPANY_ID"]

# %%
# -----------------------------------------------------------------------------
# 1. Create an analytics order
# -----------------------------------------------------------------------------
# An order defines *what* to report (type) and *when* (date range).
# The response comes back immediately with state="PENDING" — processing
# happens asynchronously on the server.

order = unique_sdk.AnalyticsOrder.create(
    user_id=USER_ID,
    company_id=COMPANY_ID,
    type="CHAT_ANALYTICS",
    start_date="2024-01-01",
    end_date="2024-12-31",
)

print("Created order:", order["id"])
print("Initial state:", order["state"])   # PENDING

ORDER_ID = order["id"]

# %%
# -----------------------------------------------------------------------------
# 2. Poll until the order reaches a terminal state
# -----------------------------------------------------------------------------
# Retrieve the order on an interval until state is DONE or ERROR.
# In production code use the run_analytics_order() utility instead —
# it handles this loop for you (see section 5).

while True:
    order = unique_sdk.AnalyticsOrder.retrieve(USER_ID, COMPANY_ID, ORDER_ID)
    print("State:", order["state"])
    if order["state"] in ("DONE", "ERROR"):
        break
    time.sleep(5)

print("Final state:", order["state"])

# %%
# -----------------------------------------------------------------------------
# 3. Download the CSV
# -----------------------------------------------------------------------------
# download() returns the raw CSV content as a string.
# The order must be in DONE state — calling it on an ERROR or PENDING order
# will raise an exception.

if order["state"] == "DONE":
    csv_content = unique_sdk.AnalyticsOrder.download(USER_ID, COMPANY_ID, ORDER_ID)
    with open("analytics_report.csv", "w", encoding="utf-8") as f:
        f.write(csv_content)
    print("Saved to analytics_report.csv")
    print("Preview:", csv_content[:200])
else:
    print("Order did not complete successfully — no CSV available.")

# %%
# -----------------------------------------------------------------------------
# 4. List orders and clean up
# -----------------------------------------------------------------------------
# list() returns a page of orders sorted by creation date descending.
# Use skip + take to paginate.

orders = unique_sdk.AnalyticsOrder.list(
    user_id=USER_ID,
    company_id=COMPANY_ID,
    skip=0,
    take=20,
)

print(f"Found {len(orders)} orders:")
for o in orders:
    print(f"  {o['id']}  state={o['state']}  type={o['type']}")

# Delete any orders that errored
for o in orders:
    if o["state"] == "ERROR":
        unique_sdk.AnalyticsOrder.delete(USER_ID, COMPANY_ID, o["id"])
        print(f"Deleted failed order: {o['id']}")

# %%
# -----------------------------------------------------------------------------
# 5. End-to-end in one call — the run utility
# -----------------------------------------------------------------------------
# run_analytics_order() wraps create → poll → download into a single
# async call. Pass save_csv_to to write the file automatically.

async def main():
    result = await run_analytics_order(
        user_id=USER_ID,
        company_id=COMPANY_ID,
        type="CHAT_ANALYTICS",
        start_date="2024-01-01",
        end_date="2024-12-31",
        save_csv_to="analytics_report_utility.csv",
        poll_interval=5.0,
        max_wait=600.0,
    )
    print("State:", result["order"]["state"])
    print("CSV saved to:", result.get("csv_path"))

asyncio.run(main())

# %%
# =============================================================================
# EXERCISES
# =============================================================================

# %%
# Exercise 1 — Scoped report
# --------------------------
# Create an analytics order filtered to a specific assistant.
# Replace "YOUR_ASSISTANT_ID" with a real ID from your environment.
#
# After creating it, print the order ID and initial state.
#
# YOUR CODE HERE ↓

# %%
# Exercise 2 — Poll with a timeout
# ---------------------------------
# Write a polling loop that gives up after 60 seconds and prints
# "Timed out" if the order has not completed.
# Hint: record time.time() before the loop and check the elapsed time.
#
# YOUR CODE HERE ↓

# %%
# Exercise 3 — List and summarise
# --------------------------------
# Retrieve up to 50 orders and print a summary table:
#
#   ID | Type | State | Created At
#
# Count how many are DONE vs ERROR vs still running.
#
# YOUR CODE HERE ↓

# %%
# Exercise 4 — Async scoped report with the utility
# --------------------------------------------------
# Use run_analytics_order() to generate a monthly report for January 2024
# (start_date="2024-01-01", end_date="2024-01-31") scoped to an assistant.
# Save the result to "january_2024.csv".
# Adjust poll_interval to 2 s and max_wait to 120 s.
#
# YOUR CODE HERE ↓
