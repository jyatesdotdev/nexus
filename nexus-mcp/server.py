# FASTMCP IMPORTS: FastMCP is the server framework; Context gives tool functions
# access to per-request data such as the incoming HTTP headers (used for auth).
from mcp.server.fastmcp import Context, FastMCP
from mcp.server.session import ServerSession
from nexus_common import IdentityContext, bootstrap_starlette_service
from sqlmodel import Session, col, func, select

from database import User, engine, init_db

# EDUCATIONAL NOTE: Single source of truth for the bind address within this module.
# HOST/PORT are referenced by both the FastMCP app and the __main__ uvicorn.run call, so
# a maintainer changing the port edits one place, not two. S104 (bind-all-interfaces) is
# acknowledged once here: it's intentional in a containerized lab where the container
# network namespace is the isolation boundary.
HOST = "0.0.0.0"  # noqa: S104
PORT = 8000

# Initialize FastMCP server
# HOW: FastMCP is a high-level framework for building MCP (Model Context Protocol) servers.
# EDUCATIONAL NOTE: It abstracts away the low-level JSON-RPC communication, allowing you to
# focus on the actual tools and resources you want to expose to an AI agent.
mcp = FastMCP("HR Directory Server", host=HOST, port=PORT)

# ==============================================================================
# EDUCATIONAL NOTE: Startup Initialization
# We call init_db() to guarantee the database schema exists and mock data
# is populated before the server fully starts accepting MCP requests.
# ==============================================================================
init_db()

# EDUCATIONAL NOTE: Shared Infrastructure
# FastMCP uses Starlette under the hood. By instrumenting its internal app,
# we gain visibility into all incoming MCP requests.
app = mcp.sse_app()

bootstrap_starlette_service(service_name="mcp-server", app=app)

# ==============================================================================
# Helpers
# ==============================================================================


def _get_identity_from_context(ctx: Context[ServerSession, None]) -> IdentityContext:
    """
    Extracts user identity from the MCP context headers.
    [EDUCATIONAL NOTE] Abstracting context parsing keeps the tool logic focused.
    """
    auth_header = None
    if hasattr(ctx, "request_context") and hasattr(ctx.request_context, "headers"):
        auth_header = ctx.request_context.headers.get("Authorization")
    return IdentityContext(auth_header)


def _is_admin(user_id: str) -> bool:
    """
    Determines if a user has administrative privileges.
    [EDUCATIONAL NOTE] Separation of authorization from business logic.
    """
    # mock_user_123 is our admin in this lab
    return user_id == "mock_user_123"


# ==============================================================================
# MCP Tools
# ==============================================================================


@mcp.tool()
def search_directory(department: str | None = None, name: str | None = None) -> str:
    """
    Searches the corporate HR directory. You can search by department or partial name.
    Returns a formatted list of employee records.
    """
    with Session(engine) as session:
        statement = select(User)

        # EDUCATIONAL NOTE: LLM-generated tool arguments are unreliable about
        # casing ("engineering" vs "Engineering"), so matching must be
        # case-insensitive or the same question nondeterministically returns
        # "no employees found" depending on how the model phrased the call.
        if department:
            statement = statement.where(
                func.lower(User.department) == department.lower()
            )
        if name:
            statement = statement.where(col(User.name).icontains(name))

        results = session.exec(statement).all()

        if not results:
            return "No employees found matching the criteria."

        formatted = ["HR Directory Results:"]
        for user in results:
            formatted.append(
                f"- Name: {user.name}, Dept: {user.department}, Email: {user.email}"
            )

        return "\n".join(formatted)


@mcp.tool()
def delete_user(email: str, ctx: Context[ServerSession, None]) -> str:
    """
    Deletes an employee from the corporate HR directory by their email address.
    This is a highly sensitive operation requiring 'admin' privileges.
    """
    # 1. Identity Propagation
    identity = _get_identity_from_context(ctx)
    print(f"MCP HR Agent: Delete request for {email} from {identity.user_id}")

    # 2. Authorization Check
    if not _is_admin(identity.user_id):
        return f"PERMISSION DENIED: User '{identity.user_id}' is not authorized to perform deletions. Please contact an administrator."

    # 3. Business Logic (Execution)
    with Session(engine) as session:
        statement = select(User).where(User.email == email)
        results = session.exec(statement).all()
        if not results:
            return f"User with email {email} not found."

        for user in results:
            session.delete(user)
        session.commit()
        return f"Successfully deleted user {email}."


# RESOURCE DECORATOR: @mcp.resource() exposes static or semi-static data.
@mcp.resource("system://status")
def get_system_status() -> str:
    """
    A static resource representing the 'status' of this MCP server.
    """
    return "All systems operational. HR Directory Server is connected."


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=HOST, port=PORT)
