"""
FestVote Event Management Routes
Add, view, update, delete events
"""

from flask import Blueprint, request, jsonify
from database.models import db, Event, Vote
from functools import wraps
import jwt
import os
from datetime import datetime

event_bp = Blueprint('events', __name__)

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
                
                # Check role
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


# ================= ADD EVENT =================
@event_bp.route('/api/events', methods=['POST'])
@require_auth(allowed_roles=['admin', 'faculty'])
def add_event():
    """Add a new event (admin/faculty only)"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        # Extract fields
        name = data.get('name', '').strip()
        description = data.get('description', '').strip()
        
        # Validation
        if not name or not description:
            return jsonify({
                'success': False,
                'error': 'Event name and description are required'
            }), 400
        
        if len(name) > 100:
            return jsonify({
                'success': False,
                'error': 'Event name must be less than 100 characters'
            }), 400
        
        if len(description) > 500:
            return jsonify({
                'success': False,
                'error': 'Description must be less than 500 characters'
            }), 400
        
        # Check duplicate name
        if Event.query.filter_by(name=name).first():
            return jsonify({
                'success': False,
                'error': f'Event "{name}" already exists'
            }), 409
        
        # Create event
        new_event = Event(
            name=name,
            description=description,
            created_by=request.user_id,
            created_at=datetime.utcnow()
        )
        
        db.session.add(new_event)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Event "{name}" added successfully',
            'event': new_event.to_dict()
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Failed to add event: {str(e)}'
        }), 500


# ================= GET ALL EVENTS =================
@event_bp.route('/api/events', methods=['GET'])
def get_events():
    """Get all events"""
    try:
        events = Event.query.order_by(Event.votes.desc()).all()
        
        return jsonify({
            'success': True,
            'count': len(events),
            'events': [event.to_dict() for event in events]
        }), 200
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to fetch events: {str(e)}'
        }), 500


# ================= GET SINGLE EVENT =================
@event_bp.route('/api/events/<int:event_id>', methods=['GET'])
def get_event(event_id):
    """Get details of a specific event"""
    try:
        event = Event.query.get(event_id)
        
        if not event:
            return jsonify({
                'success': False,
                'error': 'Event not found'
            }), 404
        
        return jsonify({
            'success': True,
            'event': event.to_dict()
        }), 200
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to fetch event: {str(e)}'
        }), 500


# ================= UPDATE EVENT =================
@event_bp.route('/api/events/<int:event_id>', methods=['PUT'])
@require_auth(allowed_roles=['admin', 'faculty'])
def update_event(event_id):
    """Update event details"""
    try:
        event = Event.query.get(event_id)
        
        if not event:
            return jsonify({
                'success': False,
                'error': 'Event not found'
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
                    'error': 'Event name cannot be empty'
                }), 400
            if len(name) > 100:
                return jsonify({
                    'success': False,
                    'error': 'Event name must be less than 100 characters'
                }), 400
            
            # Check duplicate name (excluding self)
            dup = Event.query.filter_by(name=name).filter(Event.id != event_id).first()
            if dup:
                return jsonify({
                    'success': False,
                    'error': f'Event "{name}" already exists'
                }), 409
            
            event.name = name
        
        # Update description
        if 'description' in data:
            description = data['description'].strip()
            if not description:
                return jsonify({
                    'success': False,
                    'error': 'Description cannot be empty'
                }), 400
            if len(description) > 500:
                return jsonify({
                    'success': False,
                    'error': 'Description must be less than 500 characters'
                }), 400
            event.description = description
        
        event.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Event updated successfully',
            'event': event.to_dict()
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Failed to update event: {str(e)}'
        }), 500


# ================= DELETE EVENT =================
@event_bp.route('/api/events/<int:event_id>', methods=['DELETE'])
@require_auth(allowed_roles=['admin'])
def delete_event(event_id):
    """Delete an event (admin only)"""
    try:
        event = Event.query.get(event_id)
        
        if not event:
            return jsonify({
                'success': False,
                'error': 'Event not found'
            }), 404
        
        event_name = event.name
        
        # Delete event (cascade delete votes)
        db.session.delete(event)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Event "{event_name}" deleted successfully'
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Failed to delete event: {str(e)}'
        }), 500


# ================= EVENT STATISTICS =================
@event_bp.route('/api/events/stats/summary', methods=['GET'])
def get_events_stats():
    """Get event statistics"""
    try:
        total = Event.query.count()
        total_votes = db.session.query(db.func.sum(Event.votes)).scalar() or 0
        
        return jsonify({
            'success': True,
            'total_events': total,
            'total_votes_cast': total_votes
        }), 200
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to fetch stats: {str(e)}'
        }), 500