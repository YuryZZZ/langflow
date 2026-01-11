import os
from typing import Any, Dict, List, Optional

import pandas as pd
import psycopg2
from langchain_community.utilities import SQLDatabase
from langchain_core.documents import Document
from loguru import logger
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from langflow.custom.custom_component.component import Component
from langflow.inputs import BoolInput, IntInput, MessageTextInput, SecretStrInput, StrInput
from langflow.io import Output
from langflow.schema.data import Data


class PostgreSQLComponent(Component):
    display_name = "PostgreSQL Database"
    description = "Connect to PostgreSQL database and execute queries with LangChain integration"
    name = "PostgreSQLDatabase"
    icon = "database"

    inputs = [
        StrInput(
            name="host",
            display_name="Host",
            info="PostgreSQL server host (can use POSTGRES_HOST env var)",
            value="",
            placeholder="localhost or use POSTGRES_HOST env var",
        ),
        IntInput(
            name="port",
            display_name="Port",
            info="PostgreSQL server port (can use POSTGRES_PORT env var)",
            value=5432,
        ),
        StrInput(
            name="database",
            display_name="Database",
            info="Database name (can use POSTGRES_DB env var)",
            value="",
            placeholder="database_name or use POSTGRES_DB env var",
        ),
        StrInput(
            name="username",
            display_name="Username",
            info="Database username (can use POSTGRES_USER env var)",
            value="",
            placeholder="username or use POSTGRES_USER env var",
        ),
        SecretStrInput(
            name="password",
            display_name="Password",
            info="Database password (can use POSTGRES_PASSWORD env var)",
            value="",
            placeholder="password or use POSTGRES_PASSWORD env var",
        ),
        MessageTextInput(
            name="query",
            display_name="SQL Query",
            info="SQL query to execute",
            value="SELECT version();",
            placeholder="SELECT * FROM table_name LIMIT 10;",
        ),
        BoolInput(
            name="use_env_vars",
            display_name="Use Environment Variables",
            info="Use environment variables for connection details",
            value=True,
        ),
        IntInput(
            name="limit",
            display_name="Result Limit",
            info="Maximum number of rows to return",
            value=100,
        ),
        BoolInput(
            name="return_as_documents",
            display_name="Return as Documents",
            info="Return results as LangChain Document objects",
            value=True,
        ),
    ]

    outputs = [
        Output(display_name="Data", name="data", method="execute_query"),
        Output(display_name="SQL Database", name="sql_database", method="get_sql_database"),
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._connection = None
        self._sql_database = None

    def _get_connection_params(self) -> Dict[str, Any]:
        """Get connection parameters from inputs or environment variables."""
        if self.use_env_vars:
            # Use environment variables as primary source
            params = {
                "host": os.getenv("POSTGRES_HOST", self.host),
                "port": int(os.getenv("POSTGRES_PORT", str(self.port))),
                "database": os.getenv("POSTGRES_DB", self.database),
                "user": os.getenv("POSTGRES_USER", self.username),
                "password": os.getenv("POSTGRES_PASSWORD", self.password),
            }
        else:
            # Use input values directly
            params = {
                "host": self.host,
                "port": self.port,
                "database": self.database,
                "user": self.username,
                "password": self.password,
            }

        # Validate required parameters
        missing_params = [k for k, v in params.items() if not v]
        if missing_params:
            raise ValueError(f"Missing required connection parameters: {missing_params}")

        return params

    def _get_connection_string(self) -> str:
        """Get SQLAlchemy connection string."""
        params = self._get_connection_params()
        return (
            f"postgresql://{params['user']}:{params['password']}@{params['host']}:{params['port']}/{params['database']}"
        )

    def _connect_psycopg2(self):
        """Create a psycopg2 connection for direct SQL execution."""
        if self._connection is None:
            try:
                params = self._get_connection_params()
                self._connection = psycopg2.connect(**params)
                logger.info("Successfully connected to PostgreSQL database")
            except Exception as e:
                logger.error(f"Failed to connect to PostgreSQL: {e}")
                raise

        return self._connection

    def get_sql_database(self) -> SQLDatabase:
        """Get LangChain SQLDatabase object for use with other LangChain components."""
        if self._sql_database is None:
            try:
                connection_string = self._get_connection_string()
                engine = create_engine(connection_string)
                self._sql_database = SQLDatabase(engine)
                logger.info("Successfully created LangChain SQLDatabase object")
            except Exception as e:
                logger.error(f"Failed to create SQLDatabase: {e}")
                raise

        return self._sql_database

    def execute_query(self) -> List[Data]:
        """Execute SQL query and return results."""
        try:
            # Get connection parameters
            params = self._get_connection_params()

            # Create SQLAlchemy engine for pandas
            connection_string = self._get_connection_string()
            engine = create_engine(connection_string)

            # Execute query with pandas for better data handling
            df = pd.read_sql_query(text(self.query), engine, params=None)

            # Apply limit if specified
            if self.limit > 0:
                df = df.head(self.limit)

            # Convert to appropriate format
            if self.return_as_documents:
                # Convert each row to a Document
                documents = []
                for _, row in df.iterrows():
                    # Convert row to dictionary
                    row_dict = row.to_dict()

                    # Create document content
                    content = "\n".join([f"{k}: {v}" for k, v in row_dict.items()])

                    # Create Document with metadata
                    doc = Document(
                        page_content=content,
                        metadata={
                            "source": "postgresql",
                            "query": self.query,
                            "row_index": len(documents),
                            **{str(k): str(v) for k, v in row_dict.items()},
                        },
                    )
                    documents.append(doc)

                # Convert to Data objects
                data_objects = [Data(data=doc.metadata, text_key="page_content") for doc in documents]
            else:
                # Return as structured data
                data_objects = [Data(data=row.to_dict()) for _, row in df.iterrows()]

            # Set status message
            self.status = f"Successfully executed query. Retrieved {len(data_objects)} rows."

            return data_objects

        except Exception as e:
            error_msg = f"Failed to execute query: {e}"
            logger.error(error_msg)
            self.status = error_msg
            return [Data(data={"error": error_msg, "query": self.query})]

    def get_table_info(self) -> str:
        """Get information about database tables."""
        try:
            sql_db = self.get_sql_database()
            return sql_db.get_table_info()
        except Exception as e:
            logger.error(f"Failed to get table info: {e}")
            return f"Error getting table info: {e}"

    def list_tables(self) -> List[str]:
        """List all tables in the database."""
        try:
            sql_db = self.get_sql_database()
            return sql_db.get_usable_table_names()
        except Exception as e:
            logger.error(f"Failed to list tables: {e}")
            return []

    def run_model(self) -> List[Data]:
        """Execute the query and return results."""
        return self.execute_query()

    def __del__(self):
        """Clean up database connections."""
        if self._connection:
            try:
                self._connection.close()
            except Exception:
                pass
