"""
JWT Token Authentication and Authorization Middleware
Provides token-based authentication for API endpoints
"""

import jwt
import time
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from functools import wraps

from fastapi import HTTPException, Depends, Security, status
from fastapi.security import HTTPBearer, HTTPAuthCredentials
import logging

from config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Security scheme
security = HTTPBearer()


class JWTHandler:
    """Handles JWT token generation and validation"""
    
    def __init__(self, secret_key: str, algorithm: str = "HS256", expiration_hours: int = 24):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.expiration_hours = expiration_hours
    
    def generate_token(self, payload: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """
        Generate a JWT token
        
        Args:
            payload: Data to encode in token
            expires_delta: Custom expiration time
            
        Returns:
            Encoded JWT token
        """
        to_encode = payload.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(hours=self.expiration_hours)
        
        to_encode.update({"exp": expire})
        
        try:
            encoded_jwt = jwt.encode(
                to_encode, 
                self.secret_key, 
                algorithm=self.algorithm
            )
            logger.debug(f"Generated token for user: {payload.get('sub')}")
            return encoded_jwt
        except Exception as e:
            logger.error(f"Failed to generate token: {str(e)}")
            raise
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """
        Verify and decode JWT token
        
        Args:
            token: JWT token to verify
            
        Returns:
            Decoded token payload
            
        Raises:
            HTTPException: If token is invalid or expired
        """
        try:
            payload = jwt.decode(
                token, 
                self.secret_key, 
                algorithms=[self.algorithm]
            )
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("Token expired")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except jwt.InvalidTokenError:
            logger.warning("Invalid token")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )


# Initialize JWT handler
jwt_handler = JWTHandler(
    secret_key=settings.JWT_SECRET_KEY,
    algorithm=getattr(settings, 'JWT_ALGORITHM', 'HS256'),
    expiration_hours=getattr(settings, 'JWT_EXPIRATION_HOURS', 24)
)


class TokenData:
    """Container for decoded token data"""
    
    def __init__(self, user_id: str, username: str, email: str, roles: list = None):
        self.user_id = user_id
        self.username = username
        self.email = email
        self.roles = roles or []


async def verify_bearer_token(credentials: HTTPAuthCredentials = Depends(security)) -> TokenData:
    """
    Verify Bearer token from request header
    
    Args:
        credentials: HTTP credentials from request
        
    Returns:
        TokenData with decoded information
        
    Raises:
        HTTPException: If token is invalid
    """
    token = credentials.credentials
    
    try:
        payload = jwt_handler.verify_token(token)
        
        user_id: str = payload.get("sub")
        username: str = payload.get("username")
        email: str = payload.get("email")
        roles: list = payload.get("roles", [])
        
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token - missing user ID",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return TokenData(user_id=user_id, username=username, email=email, roles=roles)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token verification failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(token_data: TokenData = Depends(verify_bearer_token)) -> TokenData:
    """Get current authenticated user from token"""
    return token_data


async def require_role(*required_roles: str):
    """
    Dependency to require specific roles
    
    Args:
        required_roles: Roles required to access resource
        
    Returns:
        Function that validates user has required role
    """
    async def check_role(current_user: TokenData = Depends(get_current_user)) -> TokenData:
        if not any(role in current_user.roles for role in required_roles):
            logger.warning(f"Access denied - user {current_user.user_id} lacks required roles")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User does not have required roles: {', '.join(required_roles)}"
            )
        return current_user
    
    return check_role


# API Key validation
class APIKeyHandler:
    """Handles API key validation for service-to-service authentication"""
    
    def __init__(self, api_keys: Dict[str, str]):
        """
        Args:
            api_keys: Mapping of API key to service name
        """
        self.api_keys = api_keys
    
    def validate_key(self, key: str) -> str:
        """
        Validate API key
        
        Args:
            key: API key to validate
            
        Returns:
            Service name associated with key
            
        Raises:
            HTTPException: If key is invalid
        """
        if key not in self.api_keys:
            logger.warning(f"Invalid API key attempted: {key[:10]}...")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key"
            )
        return self.api_keys[key]


# Initialize API key handler
api_key_handler = APIKeyHandler({
    getattr(settings, 'ADMIN_API_KEY', 'admin_key'): "admin",
    getattr(settings, 'SERVICE_API_KEY', 'service_key'): "service"
})


async def verify_api_key(x_api_key: str = Security(lambda: None)) -> str:
    """Verify API key from header"""
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key missing"
        )
    
    service = api_key_handler.validate_key(x_api_key)
    logger.debug(f"API key validated for service: {service}")
    return service
