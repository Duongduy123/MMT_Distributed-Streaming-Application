"""User authentication (rubric Step 3). Status: SCAFFOLD.

Credential storage, hashing scheme and account source are decided in Phase 3. Passwords must
never be logged or stored in plain text.
"""

from __future__ import annotations


class Authenticator:
    """Validates user credentials."""

    def verify(self, username: str, password: str) -> bool:
        raise NotImplementedError("TODO(Phase 3): credential verification")
