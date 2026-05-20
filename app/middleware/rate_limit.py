"""Rate limiting utilities."""

from slowapi import Limiter
from slowapi.util import get_remote_address

# Initialize global rate limiter
limiter = Limiter(key_func=get_remote_address)

# Common rate limits for different endpoints
RATE_LIMITS = {
    "auth": "5/minute",  # Login attempts
    "upload": "10/hour",  # File uploads
    "process": "20/hour",  # Claim processing
    "default": "100/minute",  # Default for other endpoints
}
