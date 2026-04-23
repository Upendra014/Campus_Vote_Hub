from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from functools import wraps
from flask import jsonify, request, g
import jwt
from flask import current_app

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["1000 per day", "100 per hour"]
)

def require_auth():
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def rate_limit_auth(limit_str):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def rate_limit_general(limit_str):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def handle_errors(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    return decorated_function

def require_admin(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        return f(*args, **kwargs)
    return decorated_function

def rate_limit_voting(limit_str):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def paginate(template=None, limit=10):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def paginate_query(query, page, per_page):
    # Dummy mock for now
    class PaginationMock:
        def __init__(self):
            self.items = query.all() if hasattr(query, 'all') else []
            self.page = page
            self.pages = 1
            self.total = len(self.items)
            self.has_next = False
            self.has_prev = False
    return PaginationMock()
