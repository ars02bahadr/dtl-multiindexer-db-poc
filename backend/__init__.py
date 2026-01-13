"""
Backend package initialization.
"""
from backend.app import create_app
from backend.extensions import db, jwt

__version__ = '1.0.0'
__all__ = ['create_app', 'db', 'jwt']
