# google_sheets_mcp.py - HTTP-based MCP server for Azure AI Foundry
"""
Model Context Protocol server exposing Google Sheets recipe data as tools.
Uses HTTP transport compatible with Azure AI Foundry agents.
"""
import asyncio
import os
import traceback
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from mcp.server import Server
from mcp.types import TextContent, Tool

from sheets_utils import fetch_recipe_data

# Load environment variables from .env file
load_dotenv()

# MCP server instance
mcp_server = Server("google-sheets-recipes")


@mcp_server.list_tools()
async def list_tools():
    """Define available MCP tools for recipe management."""
    return [
        Tool(
            name="get_recipes",
            description="Fetch all recipes from the Google Sheet",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="get_dinner_history",
            description="Fetch dinner history to avoid repeating recent meals",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="search_recipes",
            description="Search recipes by season or preference",
            inputSchema={
                "type": "object",
                "properties": {
                    "season": {
                        "type": "string",
                        "description": "Filter by season: winter/spring/summer/fall",
                    },
                    "preference": {
                        "type": "string",
                        "description": "Filter by dietary preference: pescetarian/vegetarian/poultry",
                    },
                },
            },
        ),
    ]


@mcp_server.call_tool()
async def call_tool(name: str, arguments: dict):
    """Execute MCP tool calls and return results."""
    try:
        if name == "get_recipes":
            df = fetch_recipe_data(worksheet_index=0)
            return [TextContent(type="text", text=df.to_json(orient="records"))]

        elif name == "get_dinner_history":
            df = fetch_recipe_data(worksheet_index=2, limit=14)
            return [TextContent(type="text", text=df.to_json(orient="records"))]

        elif name == "search_recipes":
            df = fetch_recipe_data(worksheet_index=0)

            # Apply filters (using English column names)
            if "season" in arguments:
                # Match season even when multiple seasons are in the same cell (e.g., "fall, winter")
                season_term = arguments["season"].strip()
                df = df[
                    df["Season"]
                    .fillna("")
                    .str.lower()
                    .str.contains(
                        season_term.lower(), case=False, na=False, regex=False
                    )
                ]
            if "preference" in arguments:
                # Match preference even when multiple preferences are in the same cell
                pref_term = arguments["preference"].strip()
                df = df[
                    df["Preference"]
                    .fillna("")
                    .str.lower()
                    .str.contains(pref_term.lower(), case=False, na=False, regex=False)
                ]

            return [TextContent(type="text", text=df.to_json(orient="records"))]

        else:
            raise ValueError(f"Unknown tool: {name}")

    except Exception as e:
        # Log the full error for debugging
        print(f"Error in call_tool({name}): {e}")
        traceback.print_exc()
        raise


# FastAPI app for HTTP transport
@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifecycle manager."""
    print("Starting MCP server...")
    print(f"google_sheet_id: {os.getenv('google_sheet_id')}")
    print(f"google_app_credentials: {os.getenv('google_app_credentials')}")
    yield
    print("Shutting down MCP server...")


app = FastAPI(lifespan=lifespan)


@app.post("/mcp")
async def mcp_endpoint(request: Request):
    """MCP HTTP endpoint - handles MCP protocol messages."""
    try:
        body = await request.json()
        method = body.get("method")

        if method == "tools/list":
            tools = await list_tools()
            return JSONResponse(
                {
                    "tools": [
                        {
                            "name": tool.name,
                            "description": tool.description,
                            "inputSchema": tool.inputSchema,
                        }
                        for tool in tools
                    ]
                }
            )

        elif method == "tools/call":
            params = body.get("params", {})
            tool_name = params.get("name")
            arguments = params.get("arguments", {})

            result = await call_tool(tool_name, arguments)
            return JSONResponse(
                {
                    "content": [
                        {"type": content.type, "text": content.text}
                        for content in result
                    ]
                }
            )

        else:
            return JSONResponse({"error": f"Unknown method: {method}"}, status_code=400)

    except Exception as e:
        print(f"Error in mcp_endpoint: {e}")
        traceback.print_exc()
        return JSONResponse(
            {"error": str(e), "type": type(e).__name__}, status_code=500
        )


@app.get("/health")
async def health_check():
    """Health check endpoint for container orchestration."""
    return {"status": "healthy", "server": "google-sheets-recipes"}


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
