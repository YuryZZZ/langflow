import json
from typing import Any

from langchain.tools import StructuredTool
from langchain_core.tools import ToolException
from loguru import logger
from pydantic import BaseModel, Field

from langflow.api.v2.mcp import get_server
from langflow.base.langchain_utilities.model import LCToolComponent
from langflow.base.mcp.util import MCPSseClient, MCPStdioClient, update_tools
from langflow.field_typing import Tool
from langflow.inputs.inputs import DropdownInput, MessageTextInput, StrInput
from langflow.schema.data import Data
from langflow.services.auth.utils import create_user_longterm_token
from langflow.services.database.models.user.crud import get_user_by_id
from langflow.services.deps import get_session, get_settings_service, get_storage_service


class MCPToolComponent(LCToolComponent):
    display_name = "MCP Tool"
    description = "Execute tools from Model Context Protocol (MCP) servers"
    name = "MCPTool"
    icon = "tool"

    inputs = [
        DropdownInput(
            name="server_name",
            display_name="MCP Server",
            info="Select the MCP server to use",
            options=[
                "github.com/Garoth/echo-mcp",
                "github.com/pashpashpash/perplexity-mcp",
                "github.com/modelcontextprotocol/servers/tree/main/src/memory",
                "github.com/Saik0s/mcp-browser-use",
                "github.com/executeautomation/mcp-playwright",
                "github.com/zcaceres/fetch-mcp",
                "github.com/modelcontextprotocol/servers/tree/main/src/sequentialthinking",
                "github.com/apify/actors-mcp-server",
                "github.com/modelcontextprotocol/servers/tree/main/src/filesystem",
                "github.com/browserbase/mcp-server-browserbase",
                "github.com/browserbase/mcp-server-browserbase/tree/main/stagehand",
            ],
            value="github.com/Garoth/echo-mcp",
        ),
        StrInput(
            name="tool_name",
            display_name="Tool Name",
            info="Name of the tool to execute on the MCP server",
            value="echo",
        ),
        MessageTextInput(
            name="arguments",
            display_name="Tool Arguments",
            info="JSON string containing the arguments for the tool",
            value='{"message": "Hello from Langflow!"}',
        ),
        StrInput(
            name="name",
            display_name="Tool Name (for LangChain)",
            info="The name of this tool when used in LangChain",
            value="mcp_tool",
        ),
        StrInput(
            name="description",
            display_name="Tool Description",
            info="Description of what this tool does",
            value="Execute tools from MCP servers",
        ),
    ]

    class MCPToolSchema(BaseModel):
        server_name: str = Field(..., description="The MCP server to use")
        tool_name: str = Field(..., description="The name of the tool to execute")
        arguments: str = Field(..., description="JSON string containing the tool arguments")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.stdio_client = MCPStdioClient()
        self.sse_client = MCPSseClient()
        self._tool_cache = {}

    def _parse_arguments(self, arguments_str: str) -> dict[str, Any]:
        """Parse the arguments string into a dictionary."""
        try:
            if isinstance(arguments_str, str):
                if not arguments_str.strip():
                    return {}
                return json.loads(arguments_str)
            elif isinstance(arguments_str, dict):
                return arguments_str
            else:
                return {}
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse arguments JSON: {e}")
            raise ToolException(f"Invalid JSON in arguments: {e}") from e

    async def _get_mcp_tool(self, server_name: str, tool_name: str) -> StructuredTool | None:
        """Get the MCP tool from the server."""
        try:
            # Get server configuration
            async for db in get_session():
                user_id, _ = await create_user_longterm_token(db)
                current_user = await get_user_by_id(db, user_id)

                server_config = await get_server(
                    server_name,
                    current_user,
                    db,
                    storage_service=get_storage_service(),
                    settings_service=get_settings_service(),
                )

                if not server_config:
                    logger.error(f"Server configuration not found for {server_name}")
                    return None

                # Update tools from the server
                _, tool_list, tool_cache = await update_tools(
                    server_name=server_name,
                    server_config=server_config,
                    mcp_stdio_client=self.stdio_client,
                    mcp_sse_client=self.sse_client,
                )

                # Cache the tools
                self._tool_cache = tool_cache

                # Find the specific tool
                if tool_name in tool_cache:
                    return tool_cache[tool_name]
                else:
                    logger.error(f"Tool {tool_name} not found in server {server_name}")
                    available_tools = [tool.name for tool in tool_list]
                    logger.info(f"Available tools: {available_tools}")
                    return None

        except Exception as e:
            logger.error(f"Failed to get MCP tool {tool_name} from {server_name}: {e}")
            return None

    async def _execute_mcp_tool(self, server_name: str, tool_name: str, arguments: dict[str, Any]) -> Any:
        """Execute the MCP tool using the actual MCP infrastructure."""
        try:
            # Get the tool from the MCP server
            mcp_tool = await self._get_mcp_tool(server_name, tool_name)

            if not mcp_tool:
                raise ToolException(f"Tool {tool_name} not found on server {server_name}")

            # Execute the tool
            if hasattr(mcp_tool, "coroutine") and mcp_tool.coroutine:
                # Use async execution if available
                result = await mcp_tool.coroutine(**arguments)
            else:
                # Fall back to sync execution
                result = mcp_tool.func(**arguments)

            return result

        except Exception as e:
            logger.error(f"Failed to execute MCP tool {tool_name} on {server_name}: {e}")
            raise ToolException(f"MCP tool execution failed: {e}") from e

    def build_tool(self) -> Tool:
        async def run_mcp_tool_async(server_name: str, tool_name: str, arguments: str) -> str:
            try:
                parsed_args = self._parse_arguments(arguments)
                result = await self._execute_mcp_tool(server_name, tool_name, parsed_args)

                # Convert result to string for LangChain tool compatibility
                if isinstance(result, dict):
                    return json.dumps(result, indent=2)
                else:
                    return str(result)

            except Exception as e:
                logger.opt(exception=True).debug("Error running MCP tool")
                raise ToolException(str(e)) from e

        def run_mcp_tool_sync(server_name: str, tool_name: str, arguments: str) -> str:
            import asyncio

            try:
                loop = asyncio.get_event_loop()
                return loop.run_until_complete(run_mcp_tool_async(server_name, tool_name, arguments))
            except Exception as e:
                logger.opt(exception=True).debug("Error running MCP tool")
                raise ToolException(str(e)) from e

        tool = StructuredTool.from_function(
            name=self.name,
            description=self.description,
            func=run_mcp_tool_sync,
            coroutine=run_mcp_tool_async,
            args_schema=self.MCPToolSchema,
        )

        self.status = f"MCP Tool created for server: {self.server_name}, tool: {self.tool_name}"
        return tool

    def run_model(self) -> list[Data]:
        """Execute the MCP tool directly and return the result."""
        import asyncio

        try:
            parsed_args = self._parse_arguments(self.arguments)

            # Run the async method
            loop = asyncio.get_event_loop()
            result = loop.run_until_complete(self._execute_mcp_tool(self.server_name, self.tool_name, parsed_args))

            # Set status for UI feedback
            self.status = f"Executed {self.tool_name} on {self.server_name}"

            return [Data(data={"result": result, "server": self.server_name, "tool": self.tool_name})]

        except Exception as e:
            logger.opt(exception=True).debug("Error in MCP tool run_model")
            error_msg = f"Failed to execute MCP tool: {e}"
            self.status = error_msg
            return [Data(data={"error": error_msg, "server": self.server_name, "tool": self.tool_name})]
