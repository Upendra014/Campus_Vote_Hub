"""
FestVote Voting Routes
Cast votes, view results, manage voting
"""

from flask import Blueprint, request, jsonify
from database.models import db, Vote, Event, User
from functools import wraps
import jwt
import os
from datetime import datetime

voting_bp = Blueprint('voting', __name__)

SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-CHANGE-IN-PRODUCTION')


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
            request.user_role = payload['role']
            
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


# ================= CAST VOTE =================
@voting_bp.route('/api/vote', methods=['POST'])
@require_auth
def cast_vote():
    """Cast a vote for an event"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        event_id = data.get('event_id')
        
        # Validation
        if not event_id:
            return jsonify({
                'success': False,
                'error': 'event_id is required'
            }), 400
        
        # Check event exists
        event = Event.query.get(event_id)
        if not event:
            return jsonify({
                'success': False,
                'error': 'Event not found'
            }), 404
        
        # Check user hasn't already voted
        existing_vote = Vote.query.filter_by(user_id=request.user_id).first()
        if existing_vote:
            existing_event = Event.query.get(existing_vote.event_id)
            return jsonify({
                'success': False,
                'error': f'You have already voted for "{existing_event.name}"',
                'voted_for_event_id': existing_event.id,
                'voted_for_event_name': existing_event.name
            }), 409
        
        # Create vote
        vote = Vote(
            user_id=request.user_id,
            event_id=event_id,
            voted_at=datetime.utcnow()
        )
        
        # Increment event vote count
        event.votes += 1
        
        db.session.add(vote)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'You voted for "{event.name}"',
            'vote': vote.to_dict()
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Failed to cast vote: {str(e)}'
        }), 500


# ================= GET VOTE STATUS =================
@voting_bp.route('/api/vote/status', methods=['GET'])
@require_auth
def get_vote_status():
    """Check if user has voted and which event"""
    try:
        vote = Vote.query.filter_by(user_id=request.user_id).first()
        
        if not vote:
            return jsonify({
                'success': True,
                'has_voted': False,
                'vote': None
            }), 200
        
        event = Event.query.get(vote.event_id)
        
        return jsonify({
            'success': True,
            'has_voted': True,
            'vote': {
                'id': vote.id,
                'event_id': vote.event_id,
                'event_name': event.name if event else 'Unknown',
                'voted_at': vote.voted_at.isoformat() if vote.voted_at else None
            }
        }), 200
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to fetch vote status: {str(e)}'
        }), 500


# ================= GET ALL VOTES =================
@voting_bp.route('/api/votes', methods=['GET'])
def get_all_votes():
    """Get all votes (for leaderboard/analytics)"""
    try:
        votes = Vote.query.all()
        
        vote_data = []
        for v in votes:
            user = User.query.get(v.user_id)
            event = Event.query.get(v.event_id)
            
            vote_data.append({
                'id': v.id,
                'user_id': v.user_id,
                'user_name': user.name if user else 'Unknown',
                'event_id': v.event_id,
                'event_name': event.name if event else 'Unknown',
                'voted_at': v.voted_at.isoformat() if v.voted_at else None
            })
        
        return jsonify({
            'success': True,
            'total_votes': len(votes),
            'votes': vote_data
        }), 200
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to fetch votes: {str(e)}'
        }), 500


# ================= GET RESULTS / LEADERBOARD =================
@voting_bp.route('/api/results', methods=['GET'])
def get_results():
    """Get voting results ranked by votes"""
    try:
        events = Event.query.order_by(Event.votes.desc()).all()
        
        total_votes = sum(e.votes for e in events)
        
        results = []
        for idx, event in enumerate(events):
            percentage = (event.votes / total_votes * 100) if total_votes > 0 else 0
            
            results.append({
                'rank': idx + 1,
                'event_id': event.id,
                'event_name': event.name,
                'description': event.description,
                'votes': event.votes,
                'percentage': round(percentage, 2),
                'medal': '🥇' if idx == 0 else '🥈' if idx == 1 else '🥉' if idx == 2 else None
            })
        
        return jsonify({
            'success': True,
            'total_votes': total_votes,
            'total_events': len(events),
            'results': results
        }), 200
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to fetch results: {str(e)}'
        }), 500


# ================= UNDO/DELETE VOTE =================
@voting_bp.route('/api/vote/<int:vote_id>', methods=['DELETE'])
def delete_vote(vote_id):
    """Delete a vote (admin/debugging)"""
    try:
        vote = Vote.query.get(vote_id)
        
        if not vote:
            return jsonify({
                'success': False,
                'error': 'Vote not found'
            }), 404
        
        # Decrement event votes
        event = Event.query.get(vote.event_id)
        if event and event.votes > 0:
            event.votes -= 1
        
        db.session.delete(vote)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Vote deleted successfully'
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Failed to delete vote: {str(e)}'
        }), 500


# ================= VOTING STATISTICS =================
@voting_bp.route('/api/voting/stats', methods=['GET'])
def get_voting_stats():
    """Get voting statistics"""
    try:
        total_votes = Vote.query.count()
        total_users = User.query.count()
        total_events = Event.query.count()
        voted_users = Vote.query.with_entities(Vote.user_id).distinct().count()
        
        return jsonify({
            'success': True,
            'total_votes_cast': total_votes,
            'total_users': total_users,
            'users_who_voted': voted_users,
            'users_not_voted': total_users - voted_users,
            'total_events': total_events,
            'voting_percentage': round((voted_users / total_users * 100) if total_users > 0 else 0, 2)
        }), 200
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to fetch stats: {str(e)}'
        }), 500