import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain.tools import StructuredTool

from langflow.components.tools.mcp_tool import MCPToolComponent
from langflow.schema.data import Data


class TestMCPToolComponent:
    @pytest.fixture
    def component_class(self):
        return MCPToolComponent

    @pytest.fixture
    def default_kwargs(self):
        return {
            "server_name": "github.com/Garoth/echo-mcp",
            "tool_name": "echo",
            "arguments": '{"message": "Hello from test!"}',
            "name": "test_mcp_tool",
            "description": "Test MCP tool",
        }

    def test_component_initialization(self, component_class, default_kwargs):
        """Test that the component initializes correctly."""
        component = component_class(**default_kwargs)

        assert component.display_name == "MCP Tool"
        assert component.name == "MCPTool"
        assert component.server_name == "github.com/Garoth/echo-mcp"
        assert component.tool_name == "echo"
        assert hasattr(component, "stdio_client")
        assert hasattr(component, "sse_client")

    def test_parse_arguments_valid_json(self, component_class, default_kwargs):
        """Test parsing valid JSON arguments."""
        component = component_class(**default_kwargs)

        # Test string JSON
        result = component._parse_arguments('{"key": "value"}')
        assert result == {"key": "value"}

        # Test dict input
        result = component._parse_arguments({"key": "value"})
        assert result == {"key": "value"}

        # Test empty input
        result = component._parse_arguments("")
        assert result == {}

    def test_parse_arguments_invalid_json(self, component_class, default_kwargs):
        """Test parsing invalid JSON arguments."""
        component = component_class(**default_kwargs)

        with pytest.raises(Exception):  # Should raise ToolException
            component._parse_arguments('{"invalid": json}')

    @pytest.mark.asyncio
    async def test_get_mcp_tool_success(self, component_class, default_kwargs):
        """Test successful MCP tool retrieval."""
        component = component_class(**default_kwargs)

        # Mock the dependencies
        mock_tool = MagicMock(spec=StructuredTool)
        mock_tool.name = "echo"

        with (
            patch("langflow.components.tools.mcp_tool.get_session") as mock_session,
            patch("langflow.components.tools.mcp_tool.create_user_longterm_token") as mock_token,
            patch("langflow.components.tools.mcp_tool.get_user_by_id") as mock_user,
            patch("langflow.components.tools.mcp_tool.get_server") as mock_get_server,
            patch("langflow.components.tools.mcp_tool.update_tools") as mock_update_tools,
        ):
            # Setup mocks
            mock_session.return_value.__aenter__.return_value = AsyncMock()
            mock_token.return_value = ("user_id", "token")
            mock_user.return_value = MagicMock()
            mock_get_server.return_value = {"command": "echo", "args": []}
            mock_update_tools.return_value = ("Stdio", [mock_tool], {"echo": mock_tool})

            # Test the method
            result = await component._get_mcp_tool("github.com/Garoth/echo-mcp", "echo")

            assert result == mock_tool
            assert "echo" in component._tool_cache

    @pytest.mark.asyncio
    async def test_get_mcp_tool_not_found(self, component_class, default_kwargs):
        """Test MCP tool retrieval when tool is not found."""
        component = component_class(**default_kwargs)

        with (
            patch("langflow.components.tools.mcp_tool.get_session") as mock_session,
            patch("langflow.components.tools.mcp_tool.create_user_longterm_token") as mock_token,
            patch("langflow.components.tools.mcp_tool.get_user_by_id") as mock_user,
            patch("langflow.components.tools.mcp_tool.get_server") as mock_get_server,
            patch("langflow.components.tools.mcp_tool.update_tools") as mock_update_tools,
        ):
            # Setup mocks
            mock_session.return_value.__aenter__.return_value = AsyncMock()
            mock_token.return_value = ("user_id", "token")
            mock_user.return_value = MagicMock()
            mock_get_server.return_value = {"command": "echo", "args": []}
            mock_update_tools.return_value = ("Stdio", [], {})  # No tools returned

            # Test the method
            result = await component._get_mcp_tool("github.com/Garoth/echo-mcp", "nonexistent")

            assert result is None

    @pytest.mark.asyncio
    async def test_execute_mcp_tool_success(self, component_class, default_kwargs):
        """Test successful MCP tool execution."""
        component = component_class(**default_kwargs)

        # Mock tool with coroutine
        mock_tool = MagicMock(spec=StructuredTool)
        mock_tool.coroutine = AsyncMock(return_value="Echo response")

        with patch.object(component, "_get_mcp_tool", return_value=mock_tool):
            result = await component._execute_mcp_tool("github.com/Garoth/echo-mcp", "echo", {"message": "test"})

            assert result == "Echo response"
            mock_tool.coroutine.assert_called_once_with(message="test")

    @pytest.mark.asyncio
    async def test_execute_mcp_tool_sync_fallback(self, component_class, default_kwargs):
        """Test MCP tool execution with sync fallback."""
        component = component_class(**default_kwargs)

        # Mock tool without coroutine
        mock_tool = MagicMock(spec=StructuredTool)
        mock_tool.coroutine = None
        mock_tool.func = MagicMock(return_value="Sync response")

        with patch.object(component, "_get_mcp_tool", return_value=mock_tool):
            result = await component._execute_mcp_tool("github.com/Garoth/echo-mcp", "echo", {"message": "test"})

            assert result == "Sync response"
            mock_tool.func.assert_called_once_with(message="test")

    def test_build_tool(self, component_class, default_kwargs):
        """Test building a LangChain tool."""
        component = component_class(**default_kwargs)

        tool = component.build_tool()

        assert isinstance(tool, StructuredTool)
        assert tool.name == "test_mcp_tool"  # Uses the 'name' input field
        assert tool.description == "Test MCP tool"
        assert hasattr(tool, "func")
        assert hasattr(tool, "coroutine")

    def test_run_model_success(self, component_class, default_kwargs):
        """Test successful run_model execution."""
        component = component_class(**default_kwargs)

        with patch.object(component, "_execute_mcp_tool") as mock_execute:
            mock_execute.return_value = "Test result"

            # Mock asyncio.get_event_loop().run_until_complete
            with patch("asyncio.get_event_loop") as mock_loop:
                mock_loop.return_value.run_until_complete.return_value = "Test result"

                result = component.run_model()

                assert isinstance(result, list)
                assert len(result) == 1
                assert isinstance(result[0], Data)
                assert result[0].data["result"] == "Test result"
                assert result[0].data["server"] == "github.com/Garoth/echo-mcp"
                assert result[0].data["tool"] == "echo"

    def test_run_model_error(self, component_class, default_kwargs):
        """Test run_model with error handling."""
        component = component_class(**default_kwargs)

        with patch("asyncio.get_event_loop") as mock_loop:
            mock_loop.return_value.run_until_complete.side_effect = Exception("Test error")

            result = component.run_model()

            assert isinstance(result, list)
            assert len(result) == 1
            assert isinstance(result[0], Data)
            assert "error" in result[0].data
            assert "Test error" in result[0].data["error"]
