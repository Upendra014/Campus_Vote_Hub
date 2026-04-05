"""
FestVote Member Management Routes
Add, view, update, delete members
"""

from flask import Blueprint, request, jsonify
from database.models import db, User, Vote
from functools import wraps
import jwt
import os
from datetime import datetime

member_bp = Blueprint('members', __name__)

SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-CHANGE-IN-PRODUCTION')


def require_auth(allowed_roles=None):
    """Decorator to verify JWT token and check role"""
    def decorator(f):
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
                request.user_role = payload['role']
                
                # Check if user has required role
                if allowed_roles and request.user_role not in allowed_roles:
                    return jsonify({
                        'success': False,
                        'error': f'Insufficient permissions. Required roles: {", ".join(allowed_roles)}'
                    }), 403
                
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
                    'error': f'Authentication failed: {str(e)}'
                }), 401
        
        return decorated_function
    return decorator


# ================= ADD MEMBER =================
@member_bp.route('/api/members', methods=['POST'])
@require_auth(allowed_roles=['admin', 'faculty'])
def add_member():
    """Add a new member (admin/faculty only)"""
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
                'error': 'Missing fields: name, email, password, role'
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
        
        if role not in ['admin', 'faculty', 'coordinator', 'student']:
            return jsonify({
                'success': False,
                'error': 'Invalid role'
            }), 400
        
        # Faculty cannot create admins
        if role == 'admin' and request.user_role == 'faculty':
            return jsonify({
                'success': False,
                'error': 'Faculty cannot create admin accounts'
            }), 403
        
        # Check email not already registered
        if User.query.filter_by(email=email).first():
            return jsonify({
                'success': False,
                'error': 'Email already registered'
            }), 409
        
        # Only one admin allowed
        if role == 'admin':
            existing_admin = User.query.filter_by(role='admin').first()
            if existing_admin:
                return jsonify({
                    'success': False,
                    'error': 'Admin already exists. Only one admin allowed'
                }), 403
        
        # Create member
        new_user = User(
            name=name,
            email=email,
            role=role,
            created_at=datetime.utcnow(),
            added_by=request.user_id
        )
        new_user.set_password(password)
        
        db.session.add(new_user)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Member {name} added successfully',
            'user': new_user.to_dict(include_email=True)
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Failed to add member: {str(e)}'
        }), 500


# ================= GET ALL MEMBERS =================
@member_bp.route('/api/members', methods=['GET'])
def get_members():
    """Get all members (optional role filter)"""
    try:
        role_filter = request.args.get('role')
        
        if role_filter:
            members = User.query.filter_by(role=role_filter).all()
        else:
            members = User.query.all()
        
        return jsonify({
            'success': True,
            'count': len(members),
            'members': [member.to_dict(include_email=True) for member in members]
        }), 200
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to fetch members: {str(e)}'
        }), 500


# ================= GET SINGLE MEMBER =================
@member_bp.route('/api/members/<int:user_id>', methods=['GET'])
def get_member(user_id):
    """Get details of a specific member"""
    try:
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({
                'success': False,
                'error': 'Member not found'
            }), 404
        
        return jsonify({
            'success': True,
            'user': user.to_dict(include_email=True)
        }), 200
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to fetch member: {str(e)}'
        }), 500


# ================= UPDATE MEMBER =================
@member_bp.route('/api/members/<int:user_id>', methods=['PUT'])
@require_auth(allowed_roles=['admin', 'faculty'])
def update_member(user_id):
    """Update member details"""
    try:
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({
                'success': False,
                'error': 'Member not found'
            }), 404
        
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        # Update name
        if 'name' in data:
            name = data['name'].strip()
            if not name:
                return jsonify({
                    'success': False,
                    'error': 'Name cannot be empty'
                }), 400
            user.name = name
        
        # Update role (admin only)
        if 'role' in data:
            if request.user_role != 'admin':
                return jsonify({
                    'success': False,
                    'error': 'Only admin can update roles'
                }), 403
            
            role = data['role'].strip().lower()
            if role not in ['admin', 'faculty', 'coordinator', 'student']:
                return jsonify({
                    'success': False,
                    'error': 'Invalid role'
                }), 400
            user.role = role
        
        user.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Member updated successfully',
            'user': user.to_dict(include_email=True)
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Failed to update member: {str(e)}'
        }), 500


# ================= DELETE MEMBER =================
@member_bp.route('/api/members/<int:user_id>', methods=['DELETE'])
@require_auth(allowed_roles=['admin'])
def delete_member(user_id):
    """Delete a member (admin only)"""
    try:
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({
                'success': False,
                'error': 'Member not found'
            }), 404
        
        # Cannot delete self
        if user.id == request.user_id:
            return jsonify({
                'success': False,
                'error': 'Cannot delete your own account'
            }), 400
        
        # Cannot delete admin
        if user.role == 'admin':
            return jsonify({
                'success': False,
                'error': 'Cannot delete admin account'
            }), 403
        
        # Delete member (cascade delete their votes)
        db.session.delete(user)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Member deleted successfully'
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Failed to delete member: {str(e)}'
        }), 500


# ================= MEMBER STATISTICS =================
@member_bp.route('/api/members/stats/summary', methods=['GET'])
def get_members_stats():
    """Get member statistics"""
    try:
        total = User.query.count()
        by_role = {}
        
        for role in ['admin', 'faculty', 'coordinator', 'student']:
            by_role[role] = User.query.filter_by(role=role).count()
        
        return jsonify({
            'success': True,
            'total_members': total,
            'by_role': by_role
        }), 200
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to fetch stats: {str(e)}'
        }), 500