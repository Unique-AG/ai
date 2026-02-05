# Testing the MCP Search Service

This guide shows you how to test your deployed MCP Search service.

## Quick Test

Use the automated test command:

```bash
cd terraform
./deploy.sh test
```

This tests:
- Root endpoint (`/`)
- Health endpoint (`/health`)
- Direct container access
- MCP protocol endpoint

## Manual Testing

### 1. Basic HTTP Endpoints

**Get application URLs:**
```bash
cd terraform
terraform output application_url      # https://lab-demo-001.unique.ch
terraform output aci_fqdn            # aci-search-mcp-p33drs.swedencentral.azurecontainer.io
terraform output aci_ip_address      # 20.240.158.77
```

**Test root endpoint:**
```bash
curl http://$(terraform output -raw aci_fqdn)/
# Expected: {"server":"running"}
```

**Test health endpoint:**
```bash
curl http://$(terraform output -raw aci_fqdn)/health
# Expected: {"status":"healthy"}
```

**Test via domain (if DNS configured):**
```bash
curl https://lab-demo-001.unique.ch/health
```

### 2. Direct Container Access (Bypass Caddy)

Test the MCP application directly on port 8000:

```bash
curl http://$(terraform output -raw aci_fqdn):8000/health
curl http://$(terraform output -raw aci_fqdn):8000/
```

### 3. MCP Protocol Testing

The MCP server uses the Model Context Protocol (MCP) over HTTP. The endpoint is at `/mcp`.

#### Test MCP Initialization

```bash
ENDPOINT="http://$(terraform output -raw aci_fqdn):8000"

curl -X POST "$ENDPOINT/mcp" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
      "protocolVersion": "2024-11-05",
      "capabilities": {},
      "clientInfo": {
        "name": "test-client",
        "version": "1.0"
      }
    }
  }'
```

#### Using MCP Inspector (Recommended)

The easiest way to test MCP protocol is using the official MCP Inspector:

1. **Get your endpoint URL:**
   ```bash
   cd terraform
   echo "http://$(terraform output -raw aci_fqdn):8000/mcp"
   ```

2. **Open MCP Inspector:**
   - Go to: https://modelcontextprotocol.io/inspector
   - Enter your endpoint URL
   - Configure authentication (OAuth/Zitadel if required)

3. **Test MCP operations:**
   - List tools
   - Call tools
   - Test search functionality

#### Using Python MCP Client

If you have the code locally, you can use the test client:

```bash
# From project root
cd src/mcp_search

# Update mcp_client.py with your endpoint
# Change: Client("http://localhost:8003/mcp", auth="oauth")
# To: Client("http://YOUR_ENDPOINT/mcp", auth="oauth")

python -m mcp_search.mcp_client
```

### 4. Check Container Status

```bash
./deploy.sh status
```

Look for:
- ✅ State: "Running"
- ✅ Containers: Both `mcp-search` and `caddy` should be running
- ✅ No high restart counts

### 5. View Logs

**Real-time logs:**
```bash
./deploy.sh logs mcp-search -f
./deploy.sh logs caddy -f
```

**Persistent logs (Log Analytics):**
```bash
./deploy.sh logs mcp-search --analytics
./deploy.sh logs caddy --analytics
```

**Access Log Analytics in Azure Portal:**
```bash
terraform output log_analytics_portal_url
# Opens in browser
```

## Expected Responses

### Root Endpoint (`/`)
```json
{"server": "running"}
```

### Health Endpoint (`/health`)
```json
{"status": "healthy"}
```

### MCP Initialize Response
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "protocolVersion": "2024-11-05",
    "capabilities": {...},
    "serverInfo": {
      "name": "Knowledge Base Search 🚀",
      "version": "..."
    }
  }
}
```

## Troubleshooting

### Containers Not Running

```bash
./deploy.sh status
./deploy.sh restart
```

### No Response from Endpoints

1. **Check if containers are running:**
   ```bash
   ./deploy.sh status
   ```

2. **Check logs for errors:**
   ```bash
   ./deploy.sh logs mcp-search
   ./deploy.sh logs caddy
   ```

3. **Verify DNS is configured** (if using domain):
   ```bash
   nslookup lab-demo-001.unique.ch
   # Should resolve to: $(terraform output -raw aci_ip_address)
   ```

### MCP Protocol Not Working

1. **Check authentication:** The MCP server uses OAuth/Zitadel authentication
2. **Verify endpoint:** Make sure you're using `/mcp` endpoint
3. **Check logs:** Look for authentication errors in logs
4. **Test direct access:** Try bypassing Caddy on port 8000

## Next Steps

Once testing is successful:

1. **Configure DNS** (if not already done):
   ```bash
   terraform output dns_configuration
   ```

2. **Access via domain:**
   ```bash
   curl https://lab-demo-001.unique.ch/health
   ```

3. **Integrate with MCP clients:**
   - Claude Desktop
   - MCP Inspector
   - Custom MCP clients
