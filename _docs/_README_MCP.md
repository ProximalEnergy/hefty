# Model Context Protocol

[Model Context Protocol](https://modelcontextprotocol.io/introduction) (MCP) is a standard specifying how applications provide context to LLMs.

MCPs are often used to provide LLMs access to APIs through tools. The Proximal API has implemented an MCP server using FastAPI-MCP ([GitHub](https://github.com/tadata-org/fastapi_mcp/tree/main), [docs](https://fastapi-mcp.tadata.com/getting-started/welcome)).

To connect to the MCP, first install [`mcp-remote`](https://github.com/geelen/mcp-remote) using `npm install -g mcp-remote`. Depending on your editor/client of choice, you will need to add a custom MCP server configuration similar to the following.

```
{
  "mcpServers": {
    "Proximal API": {
      "command": "npx",
      "args": [
        "mcp-remote",
        "http://localhost:8000/mcp",
        "--header",
        "x-api-key:${API_KEY}"
      ],
      "env": {
        "API_KEY": "<your-api-key>"
      }
    }
  }
}
```

To learn more about configuring MCP servers in your editor, see the [Cursor](https://docs.cursor.com/context/mcp) and [Zed](https://zed.dev/docs/ai/mcp) documentation.