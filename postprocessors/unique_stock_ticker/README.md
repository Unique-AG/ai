# Unique stock ticker post processor.

## SIX API credentials

This package expects the SIX credentials in `six_api_creds` (base64-encoded JSON) and the active company list in `six_api_activated_companies`.

The credential helper script is no longer in this package. Use the shared script from the `unique_six` connector:

- `connectors/unique_six/unique_six/get_creds.sh`
