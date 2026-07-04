from typing import Dict, Optional

# EDUCATIONAL NOTE: Identity Propagation (Mock JWT)
# This module provides a standardized way to extract user identity from
# incoming requests and propagate it to downstream agents. In a real system,
# this would include JWT validation and scope checking.

class IdentityContext:
    """
    Standardized context for handling user identity across the Nexus ecosystem.
    """
    def __init__(self, auth_header: Optional[str] = None):
        self.raw_token = None
        self.user_id = "anonymous"
        
        if auth_header and auth_header.startswith("Bearer "):
            self.raw_token = auth_header.split(" ")[1]
            # MOCK JWT PARSING: In this lab, we just split the string to get the 'mock_user_123' part
            if "." in self.raw_token:
                try:
                    payload = self.raw_token.split(".")[1]
                    self.user_id = payload
                except Exception:
                    self.user_id = "invalid_token"
            else:
                self.user_id = self.raw_token

    def get_auth_header(self) -> Dict[str, str]:
        """Returns the standard Authorization header for downstream propagation."""
        if self.raw_token:
            return {"Authorization": f"Bearer {self.raw_token}"}
        return {}

    def __repr__(self) -> str:
        return f"IdentityContext(user_id={self.user_id})"

def verify_token(token: str) -> bool:
    """
    Verifies the structure of our mock JWT.
    In a real system, this would use a library like 'PyJWT' and a secret key.
    """
    # EDUCATIONAL NOTE: Mock JWT Validation
    # We simulate validation by checking for exactly two dots (three parts)
    # and ensuring the header starts with 'eyJ' (mock for a common header).
    if token.count('.') == 2 and token.startswith("eyJ"):
        return True
    return False
