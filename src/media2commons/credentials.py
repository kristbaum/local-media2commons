"""Commons credentials, resolved the same way by every step that needs them.

Credentials come from the environment or an interactive prompt only. They are
never written to a file, a log or a CSV.
"""

from __future__ import annotations

import getpass
import os

USERNAME_ENV = "COMMONS_USERNAME"
PASSWORD_ENV = "COMMONS_PASSWORD"


def get_credentials(username: str | None = None) -> tuple[str, str]:
    """Resolve credentials from CLI args, the environment, or a prompt."""
    username = (
        username
        or os.environ.get(USERNAME_ENV)
        or input("Commons username: ").strip()
    )
    password = os.environ.get(PASSWORD_ENV) or getpass.getpass("Commons bot password: ")
    if not username or not password:
        raise SystemExit("Username and password are required.")
    return username, password
