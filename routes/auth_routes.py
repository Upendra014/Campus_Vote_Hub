"""
FestVote Authentication Routes
Login, Register, Token Verification
"""

from flask import Blueprint, request, jsonify
from database.models import db, User
import jwt
import os
from datetime import datetime, timedelta
from functools import wraps

auth_bp = Blueprint('auth', __name__)

# Secret key from environment
SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-CHANGE-IN-PRODUCTION')


def generate_token(user):
    """Generate JWT token for user"""
    try:
        token = jwt.encode(
            {
                'user_id': user.id,
                'email': user.email,
                'role': user.role,
                'exp': datetime.utcnow() + timedelta(days=7),
                'iat': datetime.utcnow()
            },
            SECRET_KEY,
            algorithm='HS256'
        )
        return token
    except Exception as e:
        return None


def require_auth(f):
    """Decorator to verify JWT token"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        
        if not token:
            return jsonify({
                'success': False,
                'error': 'Authorization token required'
            }), 401
        
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
            request.user_id = payload['user_id']
            request.user_email = payload['email']
            request.user_role = payload['role']
            
            # Verify user still exists
            user = User.query.get(payload['user_id'])
            if not user:
                return jsonify({
                    'success': False,
                    'error': 'User not found'
                }), 404
            
            request.current_user = user
            return f(*args, **kwargs)
        
        except jwt.ExpiredSignatureError:
            return jsonify({
                'success': False,
                'error': 'Token has expired'
            }), 401
        
        except jwt.InvalidTokenError:
            return jsonify({
                'success': False,
                'error': 'Invalid token'
            }), 401
        
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'Token verification failed: {str(e)}'
            }), 401
    
    return decorated_function


# ================= REGISTER USER =================
@auth_bp.route('/api/auth/register', methods=['POST'])
def register():
    """Register a new user"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        # Extract fields
        name = data.get('name', '').strip()
        email = data.get('email', '').strip().lower()
        password = data.get('password', '').strip()
        role = data.get('role', 'student').strip().lower()
        
        # Validation
        if not name or not email or not password or not role:
            return jsonify({
                'success': False,
                'error': 'Missing required fields: name, email, password, role'
            }), 400
        
        if len(name) > 100:
            return jsonify({
                'success': False,
                'error': 'Name must be less than 100 characters'
            }), 400
        
        if len(password) < 6:
            return jsonify({
                'success': False,
                'error': 'Password must be at least 6 characters'
            }), 400
        
        if '@' not in email:
            return jsonify({
                'success': False,
                'error': 'Invalid email format'
            }), 400
        
        if role not in ['admin', 'faculty', 'coordinator', 'student']:
            return jsonify({
                'success': False,
                'error': 'Invalid role. Must be: admin, faculty, coordinator, or student'
            }), 400
        
        # Check email already exists
        if User.query.filter_by(email=email).first():
            return jsonify({
                'success': False,
                'error': 'Email already registered'
            }), 409
        
        # Prevent creating additional admins
        if role == 'admin':
            existing_admin = User.query.filter_by(role='admin').first()
            if existing_admin:
                return jsonify({
                    'success': False,
                    'error': 'Admin account already exists. Only one admin allowed'
                }), 403
        
        # Create new user
        new_user = User(
            name=name,
            email=email,
            role=role,
            created_at=datetime.utcnow()
        )
        new_user.set_password(password)  # Hash password
        
        db.session.add(new_user)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'User {name} registered successfully',
            'user': new_user.to_dict(include_email=True)
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Registration failed: {str(e)}'
        }), 500


# ================= LOGIN USER =================
@auth_bp.route('/api/auth/login', methods=['POST'])
def login():
    """Login user and return JWT token"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        email = data.get('email', '').strip().lower()
        password = data.get('password', '').strip()
        
        # Validation
        if not email or not password:
            return jsonify({
                'success': False,
                'error': 'Email and password are required'
            }), 400
        
        # Find user
        user = User.query.filter_by(email=email).first()
        
        # Check user exists and password is correct
        if not user or not user.check_password(password):
            return jsonify({
                'success': False,
                'error': 'Invalid email or password'
            }), 401
        
        # Generate token
        token = generate_token(user)
        if not token:
            return jsonify({
                'success': False,
                'error': 'Failed to generate authentication token'
            }), 500
        
        return jsonify({
            'success': True,
            'message': f'Login successful. Welcome {user.name}!',
            'token': token,
            'user': {
                'id': user.id,
                'name': user.name,
                'email': user.email,
                'role': user.role
            }
        }), 200
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Login failed: {str(e)}'
        }), 500


# ================= VERIFY TOKEN =================
@auth_bp.route('/api/auth/verify', methods=['POST'])
@require_auth
def verify_token():
    """Verify that token is valid"""
    return jsonify({
        'success': True,
        'message': 'Token is valid',
        'user': {
            'id': request.current_user.id,
            'name': request.current_user.name,
            'email': request.current_user.email,
            'role': request.current_user.role
        }
    }), 200


# ================= GET CURRENT USER =================
@auth_bp.route('/api/auth/me', methods=['GET'])
@require_auth
def get_current_user():
    """Get current logged-in user details"""
    return jsonify({
        'success': True,
        'user': {
            'id': request.current_user.id,
            'name': request.current_user.name,
            'email': request.current_user.email,
            'role': request.current_user.role,
            'created_at': request.current_user.created_at.isoformat() if request.current_user.created_at else None
        }
    }), 200


# ================= LOGOUT =================
@auth_bp.route('/api/auth/logout', methods=['POST'])
@require_auth
def logout():
    """Logout user (client should delete token)"""
    return jsonify({
        'success': True,
        'message': 'Logged out successfully. Please delete token from client.'
    }), 200


# ================= REFRESH TOKEN =================
@auth_bp.route('/api/auth/refresh', methods=['POST'])
@require_auth
def refresh_token():
    """Refresh JWT token"""
    try:
        # Generate new token
        new_token = generate_token(request.current_user)
        if not new_token:
            return jsonify({
                'success': False,
                'error': 'Failed to generate new token'
            }), 500
        
        return jsonify({
            'success': True,
            'message': 'Token refreshed successfully',
            'token': new_token
        }), 200
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Token refresh failed: {str(e)}'
        }), 500