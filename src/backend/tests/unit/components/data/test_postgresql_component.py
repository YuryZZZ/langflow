import os
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest
from langchain_community.utilities import SQLDatabase
from langchain_core.documents import Document

from langflow.components.data.postgresql_component import PostgreSQLComponent
from langflow.schema.data import Data


class TestPostgreSQLComponent:
    @pytest.fixture
    def component_class(self):
        return PostgreSQLComponent

    @pytest.fixture
    def default_kwargs(self):
        return {
            "host": "localhost",
            "port": 5432,
            "database": "test_db",
            "username": "test_user",
            "password": "test_password",
            "query": "SELECT 1 as test_column;",
            "use_env_vars": False,
            "limit": 100,
            "return_as_documents": True,
        }

    @pytest.fixture
    def env_kwargs(self):
        return {
            "host": "",
            "port": 5432,
            "database": "",
            "username": "",
            "password": "",
            "query": "SELECT version();",
            "use_env_vars": True,
            "limit": 100,
            "return_as_documents": False,
        }

    def test_component_initialization(self, component_class, default_kwargs):
        """Test that the component initializes correctly."""
        component = component_class(**default_kwargs)

        assert component.display_name == "PostgreSQL Database"
        assert component.name == "PostgreSQLDatabase"
        assert component.host == "localhost"
        assert component.port == 5432
        assert component.database == "test_db"
        assert component.username == "test_user"
        assert component.password == "test_password"
        assert component.use_env_vars is False

    def test_get_connection_params_from_inputs(self, component_class, default_kwargs):
        """Test getting connection parameters from input values."""
        component = component_class(**default_kwargs)

        params = component._get_connection_params()

        assert params["host"] == "localhost"
        assert params["port"] == 5432
        assert params["database"] == "test_db"
        assert params["user"] == "test_user"
        assert params["password"] == "test_password"

    def test_get_connection_params_from_env_vars(self, component_class, env_kwargs):
        """Test getting connection parameters from environment variables."""
        with patch.dict(
            os.environ,
            {
                "POSTGRES_HOST": "env_host",
                "POSTGRES_PORT": "5433",
                "POSTGRES_DB": "env_db",
                "POSTGRES_USER": "env_user",
                "POSTGRES_PASSWORD": "env_password",
            },
        ):
            component = component_class(**env_kwargs)

            params = component._get_connection_params()

            assert params["host"] == "env_host"
            assert params["port"] == 5433
            assert params["database"] == "env_db"
            assert params["user"] == "env_user"
            assert params["password"] == "env_password"

    def test_get_connection_params_missing_required(self, component_class):
        """Test error handling when required parameters are missing."""
        component = component_class(
            host="",
            port=5432,
            database="",
            username="",
            password="",
            use_env_vars=False,
        )

        with pytest.raises(ValueError, match="Missing required connection parameters"):
            component._get_connection_params()

    def test_get_connection_string(self, component_class, default_kwargs):
        """Test connection string generation."""
        component = component_class(**default_kwargs)

        connection_string = component._get_connection_string()

        expected = "postgresql://test_user:test_password@localhost:5432/test_db"
        assert connection_string == expected

    @patch("langflow.components.data.postgresql_component.create_engine")
    @patch("langflow.components.data.postgresql_component.SQLDatabase")
    def test_get_sql_database(self, mock_sql_database, mock_create_engine, component_class, default_kwargs):
        """Test LangChain SQLDatabase creation."""
        component = component_class(**default_kwargs)
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine
        mock_sql_db = MagicMock()
        mock_sql_database.return_value = mock_sql_db

        result = component.get_sql_database()

        mock_create_engine.assert_called_once()
        mock_sql_database.assert_called_once_with(mock_engine)
        assert result == mock_sql_db
        assert component._sql_database == mock_sql_db

    @patch("langflow.components.data.postgresql_component.pd.read_sql_query")
    @patch("langflow.components.data.postgresql_component.create_engine")
    def test_execute_query_as_documents(self, mock_create_engine, mock_read_sql, component_class, default_kwargs):
        """Test query execution returning Document objects."""
        component = component_class(**default_kwargs)

        # Mock pandas DataFrame
        mock_df = pd.DataFrame({"id": [1, 2], "name": ["Alice", "Bob"], "age": [25, 30]})
        mock_read_sql.return_value = mock_df
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        result = component.execute_query()

        assert isinstance(result, list)
        assert len(result) == 2

        # Check first result
        first_data = result[0]
        assert isinstance(first_data, Data)
        assert isinstance(first_data.data, dict)
        assert first_data.data["source"] == "postgresql"
        assert "1" in first_data.data["id"]
        assert "Alice" in first_data.data["name"]

    @patch("langflow.components.data.postgresql_component.pd.read_sql_query")
    @patch("langflow.components.data.postgresql_component.create_engine")
    def test_execute_query_as_structured_data(self, mock_create_engine, mock_read_sql, component_class, default_kwargs):
        """Test query execution returning structured data."""
        # Modify kwargs to return structured data
        default_kwargs["return_as_documents"] = False
        component = component_class(**default_kwargs)

        # Mock pandas DataFrame
        mock_df = pd.DataFrame({"id": [1, 2], "name": ["Alice", "Bob"]})
        mock_read_sql.return_value = mock_df
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        result = component.execute_query()

        assert isinstance(result, list)
        assert len(result) == 2

        # Check first result
        first_data = result[0]
        assert isinstance(first_data, Data)
        assert isinstance(first_data.data, dict)
        assert first_data.data["id"] == 1
        assert first_data.data["name"] == "Alice"

    @patch("langflow.components.data.postgresql_component.pd.read_sql_query")
    @patch("langflow.components.data.postgresql_component.create_engine")
    def test_execute_query_with_limit(self, mock_create_engine, mock_read_sql, component_class, default_kwargs):
        """Test query execution with result limit."""
        default_kwargs["limit"] = 1
        component = component_class(**default_kwargs)

        # Mock pandas DataFrame with more rows than limit
        mock_df = pd.DataFrame({"id": [1, 2, 3], "name": ["Alice", "Bob", "Charlie"]})
        mock_read_sql.return_value = mock_df
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        result = component.execute_query()

        # Should only return 1 result due to limit
        assert len(result) == 1

    @patch("langflow.components.data.postgresql_component.create_engine")
    def test_execute_query_error_handling(self, mock_create_engine, component_class, default_kwargs):
        """Test error handling during query execution."""
        component = component_class(**default_kwargs)
        mock_create_engine.side_effect = Exception("Connection failed")

        result = component.execute_query()

        assert isinstance(result, list)
        assert len(result) == 1
        assert "error" in result[0].data
        assert "Connection failed" in result[0].data["error"]

    def test_run_model(self, component_class, default_kwargs):
        """Test run_model method."""
        component = component_class(**default_kwargs)

        with patch.object(component, "execute_query") as mock_execute:
            mock_execute.return_value = [Data(data={"test": "result"})]

            result = component.run_model()

            mock_execute.assert_called_once()
            assert result == [Data(data={"test": "result"})]

    @patch("langflow.components.data.postgresql_component.create_engine")
    @patch("langflow.components.data.postgresql_component.SQLDatabase")
    def test_get_table_info(self, mock_sql_database, mock_create_engine, component_class, default_kwargs):
        """Test getting table information."""
        component = component_class(**default_kwargs)
        mock_sql_db = MagicMock()
        mock_sql_db.get_table_info.return_value = "Table info"
        mock_sql_database.return_value = mock_sql_db

        result = component.get_table_info()

        assert result == "Table info"
        mock_sql_db.get_table_info.assert_called_once()

    @patch("langflow.components.data.postgresql_component.create_engine")
    @patch("langflow.components.data.postgresql_component.SQLDatabase")
    def test_list_tables(self, mock_sql_database, mock_create_engine, component_class, default_kwargs):
        """Test listing database tables."""
        component = component_class(**default_kwargs)
        mock_sql_db = MagicMock()
        mock_sql_db.get_usable_table_names.return_value = ["table1", "table2"]
        mock_sql_database.return_value = mock_sql_db

        result = component.list_tables()

        assert result == ["table1", "table2"]
        mock_sql_db.get_usable_table_names.assert_called_once()

    def test_cleanup_connection(self, component_class, default_kwargs):
        """Test connection cleanup in destructor."""
        component = component_class(**default_kwargs)
        mock_connection = MagicMock()
        component._connection = mock_connection

        # Trigger destructor
        del component

        mock_connection.close.assert_called_once()
