"""
FestVote Authentication Routes
Login, Register, Token Management with Security
"""

from flask import Blueprint, request, jsonify, current_app
from database.models import db, User
from utils.decorators import (
    require_auth, rate_limit_auth, rate_limit_general, handle_errors
)
from utils.validators import (
    validate_email_format, validate_password_strength, validate_name,
    ValidationError, validate_user_registration
)
from utils.logging import AuditLogger, get_logger
import jwt
from datetime import datetime, timedelta

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')
logger = get_logger(__name__)


def generate_token(user):
    """
    Generate JWT token for user
    
    Args:
        user: User instance
    
    Returns:
        JWT token string
    """
    try:
        token = jwt.encode(
            {
                'user_id': user.id,
                'email': user.email,
                'role': user.role,
                'exp': datetime.utcnow() + current_app.config['JWT_ACCESS_TOKEN_EXPIRES'],
                'iat': datetime.utcnow()
            },
            current_app.config['JWT_SECRET_KEY'],
            algorithm='HS256'
        )
        return token
    except Exception as e:
        logger.error(f"Token generation failed: {str(e)}")
        return None


# ============ REGISTER USER ============
@auth_bp.route('/register', methods=['POST'])
@rate_limit_auth("5/minute")
@handle_errors
def register():
    """
    Register a new user
    
    Request body:
    {
        "name": "John Doe",
        "email": "john@example.com",
        "password": "SecurePass123!",
        "role": "student"
    }
    
    Response:
    {
        "success": true,
        "message": "User registered successfully",
        "user": { ... }
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided',
                'code': 'MISSING_DATA'
            }), 400
        
        # Validate all fields
        is_valid, errors, clean_data = validate_user_registration(data)
        
        if not is_valid:
            return jsonify({
                'success': False,
                'error': 'Validation failed',
                'code': 'VALIDATION_ERROR',
                'errors': errors
            }), 400
        
        email = clean_data['email']
        
        # Check email already exists
        if User.query.filter_by(email=email).first():
            logger.warning(f"Registration attempt with existing email: {email}")
            return jsonify({
                'success': False,
                'error': 'Email already registered',
                'code': 'EMAIL_EXISTS'
            }), 409
        
        # Prevent creating additional admins
        role = clean_data['role']
        if role == 'admin':
            existing_admin = User.query.filter_by(role='admin').first()
            if existing_admin:
                logger.warning(f"Attempted to create additional admin from {request.remote_addr}")
                return jsonify({
                    'success': False,
                    'error': 'Admin account already exists. Only one admin allowed.',
                    'code': 'ADMIN_EXISTS'
                }), 403
        
        # Create new user
        new_user = User(
            name=clean_data['name'],
            email=email,
            role=role,
            created_at=datetime.utcnow()
        )
        new_user.set_password(clean_data['password'])
        
        db.session.add(new_user)
        db.session.commit()
        
        logger.info(f"User registered: {email} (role: {role})")
        
        # Audit log
        AuditLogger.log_auth_attempt(
            email=email,
            success=True,
            reason='Registration',
            ip=request.remote_addr
        )
        
        return jsonify({
            'success': True,
            'message': f'User {clean_data["name"]} registered successfully',
            'user': new_user.to_dict(include_email=True)
        }), 201
    
    except ValidationError as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'code': 'VALIDATION_ERROR'
        }), 400
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Registration error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Registration failed',
            'code': 'REGISTRATION_ERROR'
        }), 500


# ============ LOGIN USER ============
@auth_bp.route('/login', methods=['POST'])
@rate_limit_auth("5/minute")
@handle_errors
def login():
    """
    Login user and return JWT token
    
    Request body:
    {
        "email": "john@example.com",
        "password": "SecurePass123!"
    }
    
    Response:
    {
        "success": true,
        "message": "Login successful",
        "token": "eyJhbGc...",
        "user": { ... }
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided',
                'code': 'MISSING_DATA'
            }), 400
        
        email = data.get('email', '').strip().lower()
        password = data.get('password', '').strip()
        
        # Validation
        if not email or not password:
            return jsonify({
                'success': False,
                'error': 'Email and password are required',
                'code': 'MISSING_CREDENTIALS'
            }), 400
        
        # Find user
        user = User.query.filter_by(email=email).first()
        
        # Check user exists and password is correct
        if not user or not user.check_password(password):
            logger.warning(f"Failed login attempt for {email} from {request.remote_addr}")
            
            # Audit log
            AuditLogger.log_auth_attempt(
                email=email,
                success=False,
                reason='Invalid credentials',
                ip=request.remote_addr
            )
            
            return jsonify({
                'success': False,
                'error': 'Invalid email or password',
                'code': 'INVALID_CREDENTIALS'
            }), 401
        
        # Check if user is active
        if not user.is_active:
            logger.warning(f"Login attempt for inactive user: {email}")
            return jsonify({
                'success': False,
                'error': 'Account is inactive',
                'code': 'ACCOUNT_INACTIVE'
            }), 403
        
        # Generate token
        token = generate_token(user)
        if not token:
            return jsonify({
                'success': False,
                'error': 'Failed to generate authentication token',
                'code': 'TOKEN_ERROR'
            }), 500
        
        # Update last login
        user.update_last_login()
        
        logger.info(f"User logged in: {email}")
        
        # Audit log
        AuditLogger.log_auth_attempt(
            email=email,
            success=True,
            reason='Login successful',
            ip=request.remote_addr
        )
        
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
        logger.error(f"Login error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Login failed',
            'code': 'LOGIN_ERROR'
        }), 500


# ============ VERIFY TOKEN ============
@auth_bp.route('/verify', methods=['POST'])
@require_auth()
def verify_token():
    """
    Verify that token is valid
    
    Headers:
    Authorization: Bearer <token>
    
    Response:
    {
        "success": true,
        "message": "Token is valid",
        "user": { ... }
    }
    """
    return jsonify({
        'success': True,
        'message': 'Token is valid',
        'user': request.current_user.to_dict(include_email=True)
    }), 200


# ============ GET CURRENT USER ============
@auth_bp.route('/me', methods=['GET'])
@require_auth()
def get_current_user():
    """
    Get current logged-in user details
    
    Headers:
    Authorization: Bearer <token>
    
    Response:
    {
        "success": true,
        "user": { ... }
    }
    """
    return jsonify({
        'success': True,
        'user': request.current_user.to_dict(include_email=True)
    }), 200


# ============ LOGOUT ============
@auth_bp.route('/logout', methods=['POST'])
@require_auth()
def logout():
    """
    Logout user (client should delete token)
    
    Headers:
    Authorization: Bearer <token>
    
    Response:
    {
        "success": true,
        "message": "Logged out successfully"
    }
    """
    logger.info(f"User logged out: {request.current_user.email}")
    
    return jsonify({
        'success': True,
        'message': 'Logged out successfully. Please delete token from client.'
    }), 200


# ============ REFRESH TOKEN ============
@auth_bp.route('/refresh', methods=['POST'])
@require_auth()
@rate_limit_general("20/hour")
def refresh_token():
    """
    Refresh JWT token
    
    Headers:
    Authorization: Bearer <token>
    
    Response:
    {
        "success": true,
        "message": "Token refreshed successfully",
        "token": "eyJhbGc..."
    }
    """
    try:
        # Generate new token
        new_token = generate_token(request.current_user)
        if not new_token:
            return jsonify({
                'success': False,
                'error': 'Failed to generate new token',
                'code': 'TOKEN_ERROR'
            }), 500
        
        logger.info(f"Token refreshed for user: {request.current_user.email}")
        
        return jsonify({
            'success': True,
            'message': 'Token refreshed successfully',
            'token': new_token
        }), 200
    
    except Exception as e:
        logger.error(f"Token refresh error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Token refresh failed',
            'code': 'REFRESH_ERROR'
        }), 500


# ============ CHANGE PASSWORD ============
@auth_bp.route('/change-password', methods=['POST'])
@require_auth()
@rate_limit_auth("3/hour")
@handle_errors
def change_password():
    """
    Change user password
    
    Headers:
    Authorization: Bearer <token>
    
    Request body:
    {
        "current_password": "OldPass123!",
        "new_password": "NewPass456!"
    }
    
    Response:
    {
        "success": true,
        "message": "Password changed successfully"
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided',
                'code': 'MISSING_DATA'
            }), 400
        
        current_password = data.get('current_password', '').strip()
        new_password = data.get('new_password', '').strip()
        
        # Validate inputs
        if not current_password or not new_password:
            return jsonify({
                'success': False,
                'error': 'Both current and new passwords are required',
                'code': 'MISSING_PASSWORD'
            }), 400
        
        # Verify current password
        if not request.current_user.check_password(current_password):
            logger.warning(f"Failed password change: incorrect current password for {request.current_user.email}")
            return jsonify({
                'success': False,
                'error': 'Current password is incorrect',
                'code': 'INVALID_PASSWORD'
            }), 401
        
        # Validate new password strength
        try:
            validate_password_strength(new_password)
        except ValidationError as e:
            return jsonify({
                'success': False,
                'error': str(e),
                'code': 'WEAK_PASSWORD'
            }), 400
        
        # Check if new password is same as current
        if current_password == new_password:
            return jsonify({
                'success': False,
                'error': 'New password must be different from current password',
                'code': 'SAME_PASSWORD'
            }), 400
        
        # Update password
        request.current_user.set_password(new_password)
        db.session.commit()
        
        logger.info(f"Password changed for user: {request.current_user.email}")
        
        # Audit log
        AuditLogger.log_data_change(
            user_id=request.current_user.id,
            entity_type='User',
            entity_id=request.current_user.id,
            action='PASSWORD_CHANGE',
            old_value=None,
            new_value=None
        )
        
        return jsonify({
            'success': True,
            'message': 'Password changed successfully'
        }), 200
    
    except Exception as e:
        logger.error(f"Password change error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Password change failed',
            'code': 'PASSWORD_CHANGE_ERROR'
        }), 500
    
