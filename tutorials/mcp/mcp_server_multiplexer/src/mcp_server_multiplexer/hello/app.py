from fastmcp import FastMCP

mcp = FastMCP("Hello Server")


@mcp.tool
def hello(name: str) -> str:
    return f"Hello, {name}!"
