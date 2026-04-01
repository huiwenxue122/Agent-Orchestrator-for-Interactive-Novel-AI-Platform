"""
Routing constants for Story Flow graph — avoid magic strings scattered across nodes.
"""
from __future__ import annotations

from typing import Literal

# context_verify → conditional targets
VerifyRoute = Literal["ok", "retry", "fail"]
VERIFY_ROUTE_OK: VerifyRoute = "ok"
VERIFY_ROUTE_RETRY: VerifyRoute = "retry"
VERIFY_ROUTE_FAIL: VerifyRoute = "fail"

# retry_guard → conditional targets
RetryGuardRoute = Literal["retry_allowed", "retry_exhausted"]
RETRY_GUARD_ALLOWED: RetryGuardRoute = "retry_allowed"
RETRY_GUARD_EXHAUSTED: RetryGuardRoute = "retry_exhausted"

# Default cap for RAG+LLM retries after recoverable verify failures
DEFAULT_MAX_RETRIES = 2
