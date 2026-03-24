import sqlite3
# CONTEXTLIB: A standard library module for utilities involving context managers.
# WHY: It provides the @contextmanager decorator, which is the easiest way 
# to create a custom context manager without writing a full class with 
# __enter__ and __exit__ methods.
from contextlib import contextmanager
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP server
# HOW: FastMCP is a high-level framework for building MCP (Model Context Protocol) servers.
# WHY: It abstracts away the low-level JSON-RPC communication, allowing you to 
# focus on the actual tools and resources you want to expose to an AI agent.
mcp = FastMCP("HR Directory Server", host="0.0.0.0", port=8000)

# Mock Database Setup
def init_db():
    """
    Initializes a local SQLite database with some sample data.
    """
    # SQLITE3: A lightweight, file-based SQL database engine that comes built-in with Python.
    # WHY: Perfect for prototypes and local tools as it requires no separate server process.
    conn = sqlite3.connect("hr.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY, name TEXT, department TEXT, email TEXT)''')
    
    # Populate mock data if empty
    c.execute("SELECT COUNT(*) FROM users")
    if c.fetchone()[0] == 0:
        users = [
            ("Alice Smith", "Engineering", "alice@company.com"),
            ("Bob Jones", "Marketing", "bob@company.com"),
            ("Charlie Brown", "Engineering", "charlie@company.com"),
            ("Diana Prince", "HR", "diana@company.com")
        ]
        # EXECUTEMANY: Efficiently inserts multiple rows in a single call.
        # WHY: Better performance and cleaner code than a loop with multiple 'INSERT' calls.
        c.executemany("INSERT INTO users (name, department, email) VALUES (?, ?, ?)", users)
        conn.commit()
    conn.close()

init_db()

# DECORATOR: @contextmanager turns a generator function into a context manager.
# HOW: This allows us to use 'with get_db() as conn:'.
# WHY: Context managers are essential for resource management. They guarantee 
# that the database connection is closed even if an error occurs inside the 'with' block.
@contextmanager
def get_db():
    conn = sqlite3.connect("hr.db")
    try:
        # YIELD: Suspends the function and provides the 'conn' object to the 'with' block.
        # WHY: Everything before 'yield' happens during setup; everything after 
        # 'yield' happens during cleanup (the 'finally' block).
        yield conn
    finally:
        conn.close()

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
    # WITH STATEMENT: Uses the context manager defined above.
    # WHY: It makes the code cleaner and safer by handling connection closing automatically.
    with get_db() as conn:
        c = conn.cursor()
        # PARAMETERIZED QUERIES: Using '?' instead of f-strings or concatenation.
        # WHY: This prevents SQL Injection attacks, a critical security vulnerability.
        query = "SELECT name, department, email FROM users WHERE 1=1"
        params = []
        
        if department:
            query += " AND department = ?"
            params.append(department)
        if name:
            query += " AND name LIKE ?"
            params.append(f"%{name}%")
            
        c.execute(query, params)
        results = c.fetchall()
        
        if not results:
            return "No employees found matching the criteria."
            
        formatted = ["HR Directory Results:"]
        for row in results:
            formatted.append(f"- Name: {row[0]}, Dept: {row[1]}, Email: {row[2]}")
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
    return "All systems operational. HR Directory Server is connected to hr.db."

if __name__ == "__main__":
    # TRANSPORT: MCP supports different communication methods.
    # HOW: 'sse' stands for Server-Sent Events, which is great for web-based clients.
    # WHY: Choosing the right transport allows the MCP server to integrate with 
    # various frontend and orchestrator environments.
    mcp.run(transport='sse')
