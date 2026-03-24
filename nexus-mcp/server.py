# CONTEXTLIB: A standard library module for utilities involving context managers.
# WHY: Useful for making safer and cleaner code blocks.
from mcp.server.fastmcp import FastMCP
from sqlmodel import Session, select

from database import User, engine, init_db

# Initialize FastMCP server
# HOW: FastMCP is a high-level framework for building MCP (Model Context Protocol) servers.
# WHY: It abstracts away the low-level JSON-RPC communication, allowing you to
# focus on the actual tools and resources you want to expose to an AI agent.
mcp = FastMCP("HR Directory Server", host="0.0.0.0", port=8000)  # noqa: S104

# ==============================================================================
# EDUCATIONAL NOTE: Startup Initialization
# We call init_db() to guarantee the database schema exists and mock data
# is populated before the server fully starts accepting MCP requests.
# ==============================================================================
init_db()


# TOOL DECORATOR: @mcp.tool() registers a function as an MCP tool.
# HOW: The AI orchestrator will see this function's name, docstring, and arguments.
# WHY: This is the primary way to give an LLM "agency" or the ability to
# perform actions in the real world (like querying a database).
@mcp.tool()
def search_directory(department: str = None, name: str = None) -> str:
    """
    Searches the corporate HR directory. You can search by department or partial name.
    Returns a formatted list of employee records.
    """
    # ==============================================================================
    # EDUCATIONAL NOTE: Using the ORM Session
    # Using `with Session(engine) as session:` handles the opening and closing of
    # the database connection automatically.
    # By using SQLModel's `select` statements instead of raw string formatting
    # (e.g., f"SELECT * FROM users WHERE name='{name}'"), we completely eliminate
    # the risk of SQL Injection attacks.
    # ==============================================================================
    with Session(engine) as session:
        statement = select(User)

        # Dynamically build the query based on provided arguments
        if department:
            statement = statement.where(User.department == department)
        if name:
            # Using `.contains()` results in a secure 'LIKE %name%' query
            statement = statement.where(User.name.contains(name))

        # Execute the query
        results = session.exec(statement).all()

        if not results:
            return "No employees found matching the criteria."

        # Format the results into a human-readable string for the LLM
        formatted = ["HR Directory Results:"]
        for user in results:
            formatted.append(
                f"- Name: {user.name}, Dept: {user.department}, Email: {user.email}"
            )

        # STRING JOIN: Joins a list of strings into one string with newlines.
        # WHY: More efficient than repeatedly using '+=' on strings.
        return "\n".join(formatted)


# RESOURCE DECORATOR: @mcp.resource() exposes static or semi-static data.
# HOW: Resources are identified by a URI (e.g., 'system://status').
# WHY: Useful for providing reference material, logs, or status info that the agent
# can "read" rather than "execute" as a tool.
@mcp.resource("system://status")
def get_system_status() -> str:
    """
    A static resource representing the 'status' of this MCP server.
    """
    return "All systems operational. HR Directory Server is connected."


if __name__ == "__main__":
    # TRANSPORT: MCP supports different communication methods.
    # HOW: 'sse' stands for Server-Sent Events, which is great for web-based clients.
    # WHY: Choosing the right transport allows the MCP server to integrate with
    # various frontend and orchestrator environments.
    mcp.run(transport="sse")
