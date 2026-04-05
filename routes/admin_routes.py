"""
FestVote Admin Routes
System settings, configuration, finalization
"""

from flask import Blueprint, request, jsonify
from database.models import db, Vote, Event, User
from functools import wraps
import jwt
import os
from datetime import datetime

admin_bp = Blueprint('admin', __name__)

SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-CHANGE-IN-PRODUCTION')


def require_admin(f):
    """Decorator to verify JWT token and admin role"""
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
            
            # Check if admin
            if request.user_role != 'admin':
                return jsonify({
                    'success': False,
                    'error': 'Admin access required'
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


# In-memory settings (in production, use database)
settings = {
    'allowVoting': True,
    'allowAddingEvents': True,
    'maxEvents': 20,
    'isLocked': False,
    'finalizedRank': None,
}


# ================= GET SETTINGS =================
@admin_bp.route('/api/admin/settings', methods=['GET'])
def get_settings():
    """Get system settings"""
    try:
        return jsonify({
            'success': True,
            'settings': settings
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to fetch settings: {str(e)}'
        }), 500


# ================= UPDATE SETTINGS =================
@admin_bp.route('/api/admin/settings', methods=['PUT'])
@require_admin
def update_settings():
    """Update system settings (admin only)"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        # Update allowVoting
        if 'allowVoting' in data:
            settings['allowVoting'] = bool(data['allowVoting'])
        
        # Update allowAddingEvents
        if 'allowAddingEvents' in data:
            settings['allowAddingEvents'] = bool(data['allowAddingEvents'])
        
        # Update maxEvents
        if 'maxEvents' in data:
            max_events = int(data['maxEvents'])
            if max_events < 1:
                return jsonify({
                    'success': False,
                    'error': 'Max events must be at least 1'
                }), 400
            settings['maxEvents'] = max_events
        
        return jsonify({
            'success': True,
            'message': 'Settings updated successfully',
            'settings': settings
        }), 200
    
    except ValueError:
        return jsonify({
            'success': False,
            'error': 'Invalid data type'
        }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to update settings: {str(e)}'
        }), 500


# ================= TOGGLE VOTING =================
@admin_bp.route('/api/admin/voting/<action>', methods=['POST'])
@require_admin
def toggle_voting(action):
    """Toggle voting on/off"""
    try:
        action = action.lower()
        
        if action == 'on':
            settings['allowVoting'] = True
        elif action == 'off':
            settings['allowVoting'] = False
        else:
            return jsonify({
                'success': False,
                'error': 'Action must be "on" or "off"'
            }), 400
        
        return jsonify({
            'success': True,
            'message': f'Voting turned {action}',
            'allowVoting': settings['allowVoting']
        }), 200
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to toggle voting: {str(e)}'
        }), 500


# ================= TOGGLE EVENT ADDING =================
@admin_bp.route('/api/admin/events/<action>', methods=['POST'])
@require_admin
def toggle_events(action):
    """Toggle event adding on/off"""
    try:
        action = action.lower()
        
        if action == 'on':
            settings['allowAddingEvents'] = True
        elif action == 'off':
            settings['allowAddingEvents'] = False
        else:
            return jsonify({
                'success': False,
                'error': 'Action must be "on" or "off"'
            }), 400
        
        return jsonify({
            'success': True,
            'message': f'Event adding turned {action}',
            'allowAddingEvents': settings['allowAddingEvents']
        }), 200
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to toggle events: {str(e)}'
        }), 500


# ================= LOCK/FINALIZE SYSTEM =================
@admin_bp.route('/api/admin/finalize/<int:top_n>', methods=['POST'])
@require_admin
def finalize_events(top_n):
    """Finalize voting and lock system (admin only)"""
    try:
        if top_n < 1:
            return jsonify({
                'success': False,
                'error': 'top_n must be at least 1'
            }), 400
        
        events = Event.query.order_by(Event.votes.desc()).all()
        
        if not events:
            return jsonify({
                'success': False,
                'error': 'No events to finalize'
            }), 400
        
        if top_n > len(events):
            top_n = len(events)
        
        # Lock system
        settings['isLocked'] = True
        settings['allowVoting'] = False
        settings['allowAddingEvents'] = False
        settings['finalizedRank'] = top_n
        
        # Get top N events
        finalized = events[:top_n]
        finalized_data = [
            {
                'rank': idx + 1,
                'event_id': e.id,
                'event_name': e.name,
                'votes': e.votes,
                'medal': '🥇' if idx == 0 else '🥈' if idx == 1 else '🥉' if idx == 2 else None
            }
            for idx, e in enumerate(finalized)
        ]
        
        return jsonify({
            'success': True,
            'message': f'System locked. Top {top_n} events finalized',
            'finalized_events': finalized_data,
            'settings': settings
        }), 200
    
    except ValueError:
        return jsonify({
            'success': False,
            'error': 'Invalid top_n value'
        }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to finalize: {str(e)}'
        }), 500


# ================= UNLOCK SYSTEM =================
@admin_bp.route('/api/admin/unlock', methods=['POST'])
@require_admin
def unlock_system():
    """Unlock system to allow further changes"""
    try:
        settings['isLocked'] = False
        settings['allowVoting'] = True
        settings['allowAddingEvents'] = True
        settings['finalizedRank'] = None
        
        return jsonify({
            'success': True,
            'message': 'System unlocked',
            'settings': settings
        }), 200
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to unlock: {str(e)}'
        }), 500


# ================= DASHBOARD STATISTICS =================
@admin_bp.route('/api/admin/dashboard', methods=['GET'])
@require_admin
def get_dashboard():
    """Get admin dashboard statistics"""
    try:
        total_users = User.query.count()
        total_events = Event.query.count()
        total_votes = Vote.query.count()
        voted_users = Vote.query.with_entities(Vote.user_id).distinct().count()
        
        users_by_role = {}
        for role in ['admin', 'faculty', 'coordinator', 'student']:
            users_by_role[role] = User.query.filter_by(role=role).count()
        
        top_events = Event.query.order_by(Event.votes.desc()).limit(5).all()
        
        return jsonify({
            'success': True,
            'stats': {
                'total_users': total_users,
                'total_events': total_events,
                'total_votes': total_votes,
                'voted_users': voted_users,
                'pending_votes': total_users - voted_users,
                'voting_percentage': round((voted_users / total_users * 100) if total_users > 0 else 0, 2),
                'users_by_role': users_by_role,
                'top_events': [
                    {
                        'rank': idx + 1,
                        'name': e.name,
                        'votes': e.votes
                    }
                    for idx, e in enumerate(top_events)
                ]
            },
            'settings': settings
        }), 200
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to fetch dashboard: {str(e)}'
        }), 500


# ================= RESET SYSTEM =================
@admin_bp.route('/api/admin/reset', methods=['POST'])
@require_admin
def reset_system():
    """DANGER: Reset all votes (keep users and events)"""
    try:
        # Confirm with password or token
        data = request.get_json()
        
        if not data or not data.get('confirm'):
            return jsonify({
                'success': False,
                'error': 'Confirm action by sending {"confirm": true}'
            }), 400
        
        # Delete all votes
        Vote.query.delete()
        
        # Reset all event vote counts
        events = Event.query.all()
        for event in events:
            event.votes = 0
        
        # Reset settings
        settings['isLocked'] = False
        settings['allowVoting'] = True
        settings['finalizedRank'] = None
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'System reset! All votes cleared.'
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Failed to reset: {str(e)}'
        }), 500