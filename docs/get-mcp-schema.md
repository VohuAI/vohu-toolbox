



```bash
curl -i -X POST http://localhost:8069/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "MCP-Protocol-Version: 2025-06-18" \
  -H "Authorization: Bearer 76cbc38bd5b7b28e147336164fb66f7138e77955" \
  -d '{
    "jsonrpc": "2.0",
    "method": "initialize",
    "params": {
      "protocolVersion": "2025-06-18",
      "capabilities": {},
      "clientInfo": {
        "name": "curl-inspector",
        "version": "1.0.0"
      }
    },
    "id": 1
  }'
```




curl -i -X POST http://localhost:8069/mcp \
  -H "Authorization: Bearer 76cbc38bd5b7b28e147336164fb66f7138e77955" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "MCP-Protocol-Version: 2025-06-18" \
  -H "Mcp-Session-Id: YOUR_SESSION_ID" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/list",
    "params": {},
    "id": 2
  }'




curl http://localhost:8000/v1/models \
  -H "Authorization: Bearer ${VLLM_API_KEY}"