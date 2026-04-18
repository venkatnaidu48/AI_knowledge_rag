#!/usr/bin/env python
"""Generate JWT token for testing"""
import jwt
from datetime import datetime, timedelta

secret = 'your-secret-key-change-in-production'
payload = {
    'sub': 'test-user',
    'exp': datetime.utcnow() + timedelta(hours=24),
    'iat': datetime.utcnow()
}
token = jwt.encode(payload, secret, algorithm='HS256')
print('Authorization Token:')
print(token)
