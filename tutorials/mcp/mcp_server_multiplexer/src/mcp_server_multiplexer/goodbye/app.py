from fastmcp import FastMCP

mcp = FastMCP("Goodbye Server")


@mcp.tool
def bye(name: str) -> str:
    return f"Goodbye, {name}!"
