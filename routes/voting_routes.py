"""
FestVote Voting Routes
Cast votes, view results, manage voting with proper constraints
"""

from flask import Blueprint, request, jsonify, current_app
from database.models import db, Vote, Event, User
from utils.decorators import (
    require_auth, require_admin, rate_limit_voting, handle_errors, paginate, paginate_query
)
from utils.logging import AuditLogger, get_logger
from datetime import datetime
from sqlalchemy import func, desc

voting_bp = Blueprint('voting', __name__, url_prefix='/api')
logger = get_logger(__name__)


# ============ CAST VOTE ============
@voting_bp.route('/vote', methods=['POST'])
@require_auth()
@rate_limit_voting("1/hour")  # One vote per hour max
@handle_errors
def cast_vote():
    """
    Cast a vote for an event
    
    IMPORTANT: One vote per user (enforced at database level with unique constraint)
    
    Headers:
    Authorization: Bearer <token>
    
    Request body:
    {
        "event_id": 1
    }
    
    Response:
    {
        "success": true,
        "message": "You voted for...",
        "vote": { ... }
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
        
        event_id = data.get('event_id')
        
        # Validation
        if not event_id:
            return jsonify({
                'success': False,
                'error': 'event_id is required',
                'code': 'MISSING_EVENT_ID'
            }), 400
        
        if not isinstance(event_id, int) or event_id < 1:
            return jsonify({
                'success': False,
                'error': 'event_id must be a positive integer',
                'code': 'INVALID_EVENT_ID'
            }), 400
        
        # Check event exists and is active
        event = Event.query.get(event_id)
        if not event:
            return jsonify({
                'success': False,
                'error': 'Event not found',
                'code': 'EVENT_NOT_FOUND'
            }), 404
        
        if not event.is_active:
            return jsonify({
                'success': False,
                'error': 'Event is no longer active',
                'code': 'EVENT_INACTIVE'
            }), 410
        
        # ✅ CRITICAL FIX: Check if user has already voted (unique constraint)
        # This is enforced at database level with unique=True on user_id
        existing_vote = Vote.query.filter_by(user_id=request.user_id).first()
        if existing_vote:
            voted_event = Event.query.get(existing_vote.event_id)
            logger.warning(f"User {request.user_id} attempted to vote twice")
            return jsonify({
                'success': False,
                'error': f'You have already voted for "{voted_event.name if voted_event else "Unknown"}"',
                'code': 'ALREADY_VOTED',
                'voted_for_event_id': existing_vote.event_id,
                'voted_for_event_name': voted_event.name if voted_event else 'Unknown'
            }), 409
        
        # Check if voting is allowed
        from database.models import AdminSetting
        allow_voting = AdminSetting.get('allowVoting', True)
        if not allow_voting:
            return jsonify({
                'success': False,
                'error': 'Voting is currently disabled',
                'code': 'VOTING_DISABLED'
            }), 403
        
        # Create vote
        try:
            vote = Vote(
                user_id=request.user_id,
                event_id=event_id,
                voted_at=datetime.utcnow(),
                ip_address=request.remote_addr
            )
            
            # Increment event vote count
            event.votes += 1
            
            db.session.add(vote)
            db.session.commit()
            
            logger.info(f"Vote cast: user={request.user_id}, event={event_id}")
            
            # Audit log
            AuditLogger.log_vote_cast(
                user_id=request.user_id,
                event_id=event_id,
                ip=request.remote_addr
            )
            
            return jsonify({
                'success': True,
                'message': f'You voted for "{event.name}"',
                'vote': vote.to_dict()
            }), 201
        
        except Exception as e:
            db.session.rollback()
            logger.error(f"Vote creation failed: {str(e)}")
            return jsonify({
                'success': False,
                'error': 'Failed to cast vote',
                'code': 'VOTE_ERROR'
            }), 500
    
    except Exception as e:
        logger.error(f"Voting error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Voting failed',
            'code': 'VOTING_ERROR'
        }), 500


# ============ GET VOTE STATUS ============
@voting_bp.route('/vote/status', methods=['GET'])
@require_auth()
@handle_errors
def get_vote_status():
    """
    Check if user has voted and which event
    
    Headers:
    Authorization: Bearer <token>
    
    Response:
    {
        "success": true,
        "has_voted": true,
        "vote": { ... }
    }
    """
    try:
        vote = Vote.query.filter_by(user_id=request.user_id).first()
        
        if not vote:
            return jsonify({
                'success': True,
                'has_voted': False,
                'vote': None
            }), 200
        
        return jsonify({
            'success': True,
            'has_voted': True,
            'vote': vote.to_dict()
        }), 200
    
    except Exception as e:
        logger.error(f"Vote status error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to fetch vote status',
            'code': 'VOTE_STATUS_ERROR'
        }), 500


# ============ GET ALL VOTES (with optimized queries) ============
@voting_bp.route('/votes', methods=['GET'])
@paginate()
@handle_errors
def get_all_votes():
    """
    Get all votes with pagination (N+1 query optimization)
    
    Query params:
    - page: Page number (default: 1)
    - per_page: Items per page (default: 20, max: 100)
    
    Response:
    {
        "success": true,
        "total_votes": 100,
        "pagination": { ... },
        "votes": [ ... ]
    }
    """
    try:
        # ✅ OPTIMIZATION: Use join to prevent N+1 queries
        query = db.session.query(Vote).join(User).join(Event)
        
        # Get paginated results
        votes, pagination = paginate_query(query)
        
        vote_data = [vote.to_dict() for vote in votes]
        
        return jsonify({
            'success': True,
            'total_votes': pagination['total'],
            'pagination': {
                'page': pagination['page'],
                'per_page': pagination['per_page'],
                'total_pages': pagination['pages'],
                'has_next': pagination['has_next'],
                'has_prev': pagination['has_prev']
            },
            'votes': vote_data
        }), 200
    
    except Exception as e:
        logger.error(f"Get votes error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to fetch votes',
            'code': 'VOTES_ERROR'
        }), 500


# ============ GET RESULTS / LEADERBOARD ============
@voting_bp.route('/results', methods=['GET'])
@handle_errors
def get_results():
    """
    Get voting results ranked by votes
    
    Response:
    {
        "success": true,
        "total_votes": 100,
        "total_events": 5,
        "results": [
            {
                "rank": 1,
                "event_id": 1,
                "event_name": "Event A",
                "votes": 45,
                "percentage": 45.0,
                "medal": "🥇"
            },
            ...
        ]
    }
    """
    try:
        # Get all events ordered by votes
        events = Event.query.filter_by(is_active=True).order_by(
            desc(Event.votes)
        ).all()
        
        # Calculate total votes
        total_votes = sum(e.votes for e in events)
        
        results = []
        for idx, event in enumerate(events):
            percentage = (event.votes / total_votes * 100) if total_votes > 0 else 0
            
            medal = None
            if idx == 0:
                medal = '🥇'
            elif idx == 1:
                medal = '🥈'
            elif idx == 2:
                medal = '🥉'
            
            results.append({
                'rank': idx + 1,
                'event_id': event.id,
                'event_name': event.name,
                'description': event.description,
                'votes': event.votes,
                'percentage': round(percentage, 2),
                'medal': medal
            })
        
        return jsonify({
            'success': True,
            'total_votes': total_votes,
            'total_events': len(events),
            'results': results
        }), 200
    
    except Exception as e:
        logger.error(f"Results error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to fetch results',
            'code': 'RESULTS_ERROR'
        }), 500


# ============ DELETE VOTE (ADMIN ONLY) ============
@voting_bp.route('/vote/<int:vote_id>', methods=['DELETE'])
@require_admin  # ✅ SECURITY FIX: Added authentication
@handle_errors
def delete_vote(vote_id):
    """
    Delete a vote (admin only)
    
    SECURITY: Requires admin role
    
    Headers:
    Authorization: Bearer <admin_token>
    
    Response:
    {
        "success": true,
        "message": "Vote deleted successfully"
    }
    """
    try:
        vote = Vote.query.get(vote_id)
        
        if not vote:
            return jsonify({
                'success': False,
                'error': 'Vote not found',
                'code': 'VOTE_NOT_FOUND'
            }), 404
        
        # Get event for vote count update
        event = Event.query.get(vote.event_id)
        if event and event.votes > 0:
            event.votes -= 1
        
        user_id = vote.user_id
        event_id = vote.event_id
        
        db.session.delete(vote)
        db.session.commit()
        
        logger.info(f"Vote deleted by admin {request.user_id}: vote_id={vote_id}")
        
        # Audit log
        AuditLogger.log_data_change(
            user_id=request.user_id,
            entity_type='Vote',
            entity_id=vote_id,
            action='DELETE',
            old_value=f'user_id={user_id}, event_id={event_id}'
        )
        
        return jsonify({
            'success': True,
            'message': 'Vote deleted successfully'
        }), 200
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Vote deletion error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to delete vote',
            'code': 'DELETE_ERROR'
        }), 500


# ============ VOTING STATISTICS ============
@voting_bp.route('/voting/stats', methods=['GET'])
@handle_errors
def get_voting_stats():
    """
    Get voting statistics
    
    Response:
    {
        "success": true,
        "total_votes_cast": 50,
        "total_users": 100,
        "users_who_voted": 50,
        "users_not_voted": 50,
        "total_events": 5,
        "voting_percentage": 50.0
    }
    """
    try:
        # ✅ OPTIMIZATION: Use COUNT aggregation instead of loading all records
        total_votes = db.session.query(func.count(Vote.id)).scalar() or 0
        total_users = db.session.query(func.count(User.id)).scalar() or 0
        total_events = db.session.query(func.count(Event.id)).scalar() or 0
        voted_users = db.session.query(
            func.count(func.distinct(Vote.user_id))
        ).scalar() or 0
        
        voting_percentage = (voted_users / total_users * 100) if total_users > 0 else 0
        
        return jsonify({
            'success': True,
            'total_votes_cast': total_votes,
            'total_users': total_users,
            'users_who_voted': voted_users,
            'users_not_voted': max(0, total_users - voted_users),
            'total_events': total_events,
            'voting_percentage': round(voting_percentage, 2)
        }), 200
    
    except Exception as e:
        logger.error(f"Voting stats error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to fetch stats',
            'code': 'STATS_ERROR'
        }), 500


# ============ RESET USER VOTE (for testing/admin) ============
@voting_bp.route('/vote/user/<int:user_id>', methods=['DELETE'])
@require_admin
@handle_errors
def reset_user_vote(user_id):
    """
    Reset a user's vote (admin only)
    
    SECURITY: Requires admin role
    
    Headers:
    Authorization: Bearer <admin_token>
    
    Response:
    {
        "success": true,
        "message": "Vote reset successfully"
    }
    """
    try:
        # Check user exists
        user = User.query.get(user_id)
        if not user:
            return jsonify({
                'success': False,
                'error': 'User not found',
                'code': 'USER_NOT_FOUND'
            }), 404
        
        # Find vote
        vote = Vote.query.filter_by(user_id=user_id).first()
        if not vote:
            return jsonify({
                'success': False,
                'error': 'User has not voted',
                'code': 'NO_VOTE'
            }), 404
        
        # Decrement event votes
        event = Event.query.get(vote.event_id)
        if event and event.votes > 0:
            event.votes -= 1
        
        db.session.delete(vote)
        db.session.commit()
        
        logger.info(f"Vote reset by admin {request.user_id}: user_id={user_id}")
        
        # Audit log
        AuditLogger.log_data_change(
            user_id=request.user_id,
            entity_type='Vote',
            entity_id=vote.id,
            action='RESET',
            old_value=f'event_id={vote.event_id}'
        )
        
        return jsonify({
            'success': True,
            'message': f'Vote reset for user {user.name}'
        }), 200
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Vote reset error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to reset vote',
            'code': 'RESET_ERROR'
        }), 500