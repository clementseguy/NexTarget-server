"""
OAuth provider configuration and constants.
Centralizes all OAuth-related endpoints and scopes.
"""
from typing import Final

# Google OAuth Configuration
GOOGLE_AUTH_ENDPOINT: Final[str] = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_ENDPOINT: Final[str] = "https://oauth2.googleapis.com/token"
GOOGLE_SCOPES: Final[list[str]] = ["openid", "email", "profile"]

# Facebook OAuth Configuration
FACEBOOK_AUTH_ENDPOINT: Final[str] = "https://www.facebook.com/v18.0/dialog/oauth"
FACEBOOK_TOKEN_ENDPOINT: Final[str] = "https://graph.facebook.com/v18.0/oauth/access_token"
FACEBOOK_USERINFO_ENDPOINT: Final[str] = "https://graph.facebook.com/me"
FACEBOOK_SCOPES: Final[list[str]] = ["email"]

# OAuth State Management
STATE_TTL_SECONDS: Final[int] = 600  # 10 minutes
OAUTH_TIMEOUT_SECONDS: Final[int] = 15  # HTTP request timeout
