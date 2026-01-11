# Langflow Integration Guide

This guide covers the new integrations added to Langflow for enhanced functionality with MCP servers and PostgreSQL databases.

## Table of Contents

1. [Environment Setup](#environment-setup)
2. [MCP Tool Integration](#mcp-tool-integration)
3. [PostgreSQL Database Integration](#postgresql-database-integration)
4. [Usage Examples](#usage-examples)
5. [Troubleshooting](#troubleshooting)

## Environment Setup

### 1. API Keys Configuration

A comprehensive `.env` file has been created to manage all your API keys and configuration settings. This eliminates the need to enter API keys repeatedly.

**Location**: `.env` (in the root directory)

**Key Features**:
- **LLM API Keys**: OpenAI, Anthropic, Google, Cohere, Hugging Face, Azure OpenAI, Mistral, Perplexity
- **Tool API Keys**: Browserbase, Apify, Serper, Tavily
- **Database Configuration**: PostgreSQL connection details
- **Langflow Settings**: Server configuration, logging, caching

**Setup Instructions**:
1. Open the `.env` file in the root directory
2. Replace placeholder values with your actual API keys:
   ```env
   # Example: Replace this
   OPENAI_API_KEY=your_openai_api_key_here
   
   # With your actual key
   OPENAI_API_KEY=sk-1234567890abcdef...
   ```
3. Save the file
4. Restart Langflow for changes to take effect

**Important**: Never commit the `.env` file to version control as it contains sensitive information.

## MCP Tool Integration

### Overview

The MCP Tool component enables Langflow to interact with all your installed Model Context Protocol (MCP) servers directly within flows.

### Supported MCP Servers

- **Echo MCP**: Simple echo functionality for testing
- **Perplexity Research**: Advanced search and research capabilities
- **Knowledge Graph Memory**: Persistent memory and knowledge management
- **Browser Use**: Web browser automation
- **Playwright**: Advanced web automation and testing
- **Fetch**: HTTP requests and web content fetching
- **Sequential Thinking**: Step-by-step reasoning and analysis
- **Apify Actors**: Large-scale web scraping and data extraction
- **File System**: File and directory operations
- **Browserbase**: Cloud browser automation
- **Stagehand**: Advanced browser orchestration

### Using the MCP Tool Component

1. **Add to Flow**: In the Langflow UI, find "MCP Tool" in the Tools category
2. **Configure**:
   - **MCP Server**: Select from the dropdown (e.g., "github.com/Garoth/echo-mcp")
   - **Tool Name**: Specify the tool to execute (e.g., "echo", "search", "playwright_navigate")
   - **Arguments**: Provide JSON arguments for the tool
   - **Tool Name (for LangChain)**: Custom name for LangChain integration
   - **Description**: Description of what the tool does

3. **Example Configurations**:

   **Echo Test**:
   ```
   Server: github.com/Garoth/echo-mcp
   Tool: echo
   Arguments: {"message": "Hello from Langflow!"}
   ```

   **Perplexity Research**:
   ```
   Server: github.com/pashpashpash/perplexity-mcp
   Tool: search
   Arguments: {"query": "latest AI developments", "detail_level": "detailed"}
   ```

   **File Operations**:
   ```
   Server: github.com/modelcontextprotocol/servers/tree/main/src/filesystem
   Tool: read_file
   Arguments: {"path": "/path/to/file.txt"}
   ```

   **Web Automation**:
   ```
   Server: github.com/executeautomation/mcp-playwright
   Tool: playwright_navigate
   Arguments: {"url": "https://example.com"}
   ```

## PostgreSQL Database Integration

### Overview

The PostgreSQL Database component enables Langflow to connect to and interact with PostgreSQL databases, including your Google Cloud PostgreSQL instance.

### Features

- **Environment Variable Support**: Automatically uses credentials from `.env` file
- **LangChain Integration**: Provides SQLDatabase objects for other LangChain components
- **Flexible Output**: Returns data as LangChain Documents or structured data
- **Query Execution**: Execute any SQL query with result limiting
- **Error Handling**: Comprehensive error handling and logging

### Configuration

The component automatically uses the PostgreSQL connection details from your `.env` file:

```env
POSTGRES_HOST=34.10.108.107
POSTGRES_PORT=5432
POSTGRES_DB=postgres
POSTGRES_USER=postgres
POSTGRES_PASSWORD=#v}y3#8W
```

### Using the PostgreSQL Component

1. **Add to Flow**: Find "PostgreSQL Database" in the Data category
2. **Configure**:
   - **Use Environment Variables**: Set to `True` (default) to use `.env` credentials
   - **SQL Query**: Enter your SQL query
   - **Result Limit**: Maximum number of rows to return (default: 100)
   - **Return as Documents**: Choose between LangChain Documents or structured data

3. **Example Queries**:

   **Basic Query**:
   ```sql
   SELECT version();
   ```

   **Data Retrieval**:
   ```sql
   SELECT * FROM your_table_name LIMIT 10;
   ```

   **Aggregation**:
   ```sql
   SELECT category, COUNT(*) as count 
   FROM products 
   GROUP BY category 
   ORDER BY count DESC;
   ```

### Output Formats

**As Documents** (default):
- Each row becomes a LangChain Document
- Suitable for RAG (Retrieval-Augmented Generation) workflows
- Contains metadata with source information

**As Structured Data**:
- Each row becomes a dictionary
- Suitable for data processing and analysis
- Direct access to column values

## Usage Examples

### Example 1: Research and Database Integration

Create a flow that:
1. Uses Perplexity MCP to research a topic
2. Stores findings in PostgreSQL
3. Retrieves related data for analysis

**Flow Structure**:
```
[Input] → [MCP Tool: Perplexity] → [PostgreSQL: INSERT] → [PostgreSQL: SELECT] → [Output]
```

### Example 2: Web Scraping to Database

Create a flow that:
1. Uses Playwright MCP to scrape web data
2. Processes the data
3. Stores results in PostgreSQL

**Flow Structure**:
```
[Input: URL] → [MCP Tool: Playwright] → [Data Processing] → [PostgreSQL: INSERT] → [Confirmation]
```

### Example 3: Database-Driven AI Responses

Create a flow that:
1. Queries PostgreSQL for relevant data
2. Uses the data to enhance LLM responses
3. Provides contextual, data-driven answers

**Flow Structure**:
```
[User Query] → [PostgreSQL: SELECT] → [LLM with Context] → [Response]
```

## Troubleshooting

### Common Issues

**1. API Keys Not Working**
- Ensure `.env` file is in the root directory
- Restart Langflow after modifying `.env`
- Check that API keys are valid and have sufficient credits

**2. MCP Server Connection Issues**
- Verify MCP servers are properly installed and configured
- Check MCP server logs for errors
- Ensure server names match exactly (case-sensitive)

**3. PostgreSQL Connection Issues**
- Verify database credentials in `.env` file
- Check network connectivity to the database
- Ensure PostgreSQL server is running and accessible

**4. Component Not Appearing in UI**
- Restart Langflow backend
- Refresh browser page
- Check browser console for errors

### Getting Help

**Logs**: Check Langflow logs for detailed error messages
**Testing**: Use simple test cases first (e.g., echo MCP tool, basic SQL queries)
**Documentation**: Refer to individual MCP server documentation for specific tool usage

## Best Practices

1. **Security**: Never commit `.env` file to version control
2. **Testing**: Test components individually before building complex flows
3. **Error Handling**: Always include error handling in your flows
4. **Performance**: Use result limits for large database queries
5. **Monitoring**: Monitor API usage and database connections

## Next Steps

1. **Explore MCP Tools**: Try different MCP servers to understand their capabilities
2. **Database Integration**: Connect your existing databases and create data-driven flows
3. **Complex Workflows**: Build multi-step workflows combining MCP tools and database operations
4. **Custom Components**: Consider creating custom components for specific use cases

---

For additional support or questions, refer to the Langflow documentation or community forums.
