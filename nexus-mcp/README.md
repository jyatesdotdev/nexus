# MCP HR Directory Server

This project implements a Model Context Protocol (MCP) server that provides a secure interface to a corporate HR directory. It allows LLMs (Large Language Models) to query employee information stored in a local SQLite database through well-defined tools and resources.

## What it does

The HR Directory Server exposes a single tool, `search_directory`, which allows for searching employees by department or name. It also provides a static resource `system://status` to report the server's health.

- **Tools:**
  - `search_directory(department, name)`: Query the HR database for employee records including name, department, and email.
- **Resources:**
  - `system://status`: A static resource that confirms the server's operational status and database connection.

## How it works

The server is built using the [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) Python SDK, specifically the `FastMCP` framework.

1.  **Database:** Upon startup, the server initializes a local SQLite database (`hr.db`) and populates it with mock employee data if it doesn't already exist.
2.  **MCP Implementation:** The server uses the `FastMCP` library to define tools and resources.
3.  **Transport:** It uses the **SSE (Server-Sent Events)** transport layer, which allows for asynchronous, unidirectional communication from the server to the client.
4.  **Security:** The server runs in a Docker container as a non-root user, ensuring a secure and isolated environment.

### HOW/WHY Documentation

*   **HOW:** We use the `@mcp.tool()` decorator to expose Python functions directly as tools that an LLM can invoke.
*   **WHY:** This approach decouples the LLM from the underlying data source. The LLM doesn't need to know how to write SQL or have direct network access to the database; it simply calls the `search_directory` tool, and the MCP server handles the secure execution of the query.
*   **HOW:** We use the `@mcp.resource()` decorator to expose static or semi-static data as URIs.
*   **WHY:** Resources provide a way for agents to "read" data from the server, similar to how they might read a file or an API endpoint, but within the structured context of the MCP protocol.

## How to run it

### Using Docker (Recommended)

To build and run the HR Directory Server using Docker:

1.  **Build the image:**
    ```bash
    docker build -t mcp-hr-server .
    ```
2.  **Run the container:**
    ```bash
    docker run -p 8000:8000 mcp-hr-server
    ```
    The server will be available at `http://localhost:8000`.

### Manual Run

To run the server locally without Docker:

1.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
2.  **Start the server:**
    ```bash
    python server.py
    ```

## Role as an MCP Server

In an agentic architecture, this server acts as a **Capability Provider**. It doesn't have any autonomous logic itself; instead, it provides specific "skills" (tools) and "knowledge" (resources) to an orchestrator or an agent. This modularity allows for:
- **Separation of Concerns:** The HR server only cares about HR data and SQLite queries.
- **Security:** Sensitive database credentials never leave the MCP server.
- **Reusability:** Any MCP-compliant client can connect to and use this HR directory.
