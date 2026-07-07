"""
OAuth state management service.
Handles ephemeral state storage with TTL expiration.

NOTE: In-memory implementation for v0.1. Replace with Redis for production.
"""
import secrets
import time
from typing import Optional

from ..core.oauth_config import STATE_TTL_SECONDS


class OAuthStateManager:
    """
    Manages OAuth state tokens with automatic expiration.
    Thread-safe for single-process deployments.
    """
    
    def __init__(self, ttl_seconds: int = STATE_TTL_SECONDS):
        self._states: dict[str, dict] = {}
        self._ttl_seconds = ttl_seconds
    
    def create_state(
        self, 
        client_nonce: Optional[str] = None,
        nonce: Optional[str] = None
    ) -> tuple[str, dict]:
        """
        Create a new state token with associated data.
        
        Args:
            client_nonce: Optional opaque value from client to bind session
            nonce: Optional nonce for OIDC (generated if not provided)
            
        Returns:
            Tuple of (state_token, state_data)
        """
        self._prune_expired()
        
        state = secrets.token_urlsafe(24)
        nonce = nonce or secrets.token_urlsafe(24)
        now = time.time()
        
        state_data = {
            "nonce": nonce,
            "created": now,
            "exp": now + self._ttl_seconds,
            "client_nonce": client_nonce,
        }
        
        self._states[state] = state_data
        return state, state_data
    
    def verify_and_consume(self, state: str) -> Optional[dict]:
        """
        Verify state exists and consume it (one-time use).
        
        Args:
            state: The state token to verify
            
        Returns:
            State data if valid, None if invalid/expired
        """
        self._prune_expired()
        return self._states.pop(state, None)
    
    def _prune_expired(self) -> None:
        """Remove expired state tokens."""
        now = time.time()
        expired = [k for k, v in self._states.items() if v["exp"] < now]
        for k in expired:
            self._states.pop(k, None)


# Global singleton instance
_state_manager = OAuthStateManager()


def get_state_manager() -> OAuthStateManager:
    """Get the global OAuth state manager instance."""
    return _state_manager
