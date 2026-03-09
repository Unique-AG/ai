# Unique stock ticker post processor.

## SIX API credentials

This package expects the SIX credentials in `SIX_API_CREDS` (base64-encoded JSON) and the active company list in `SIX_API_ACTIVATED_COMPANIES`.

The credential helper script is no longer in this package. Use the shared script from the `unique_six` connector:

- `connectors/unique_six/unique_six/get_creds.sh`
