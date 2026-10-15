"""Security utilities: key masking, audit logging, secret loading."""

import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


def mask_key(key: Optional[str]) -> str:
    """Never print the full key."""
    if not key:
        return "<MISSING>"
    if len(key) < 8:
        return "***"
    return f"{key[:4]}***{key[-4:]}"


def get_secret(name: str) -> str:
    """Load a secret from environment (.env / platform secrets).

    Returns an empty string if missing; callers must stop and report
    per protocol S3 (never auto-skip).
    """
    value = os.getenv(name, "")
    print(f"[security] {name} = {mask_key(value)}")
    return value


def audit_log(service: str, key: Optional[str], status: str, detail: str = "") -> None:
    """Append one line to artifacts/logs/api_access.log (protocol S10)."""
    log_dir = Path("artifacts/logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    key_masked = mask_key(key) if key else "NO_KEY"
    line = f"[{ts}] [{service}] [{key_masked}] [{status}]"
    if detail:
        line += f" [{detail}]"
    with open(log_dir / "api_access.log", "a", encoding="utf-8") as f:
        f.write(line + "\n")


def error_log(phase: str, error_type: str, message: str, context: str = "") -> None:
    """Append one entry to artifacts/logs/errors.log (protocol section 7)."""
    log_dir = Path("artifacts/logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(log_dir / "errors.log", "a", encoding="utf-8") as f:
        f.write(f"[{ts}] [{phase}] [{error_type}]: {message}\n")
        if context:
            f.write(f"Context: {context}\n")
