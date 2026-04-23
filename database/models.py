"""
FestVote Database Models
Production-ready with relationships, constraints, and indexes
"""

from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID
import uuid

db = SQLAlchemy()


# ============ User Model ============
class User(db.Model):
    """
    User model for authentication and authorization
    
    Roles: admin, faculty, coordinator, student
    """
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Basic info
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    
    # Role-based access (admin, faculty, coordinator, student)
    role = db.Column(
        db.String(50),
        default='student',
        nullable=False,
        index=True,
        # Add check constraint in migration:
        # CHECK (role IN ('admin', 'faculty', 'coordinator', 'student'))
    )
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    added_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    # Security
    last_login = db.Column(db.DateTime, nullable=True)
    password_changed_at = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    
    # Relationships
    votes = db.relationship(
        'Vote',
        backref='voter',
        lazy='select',
        cascade='all, delete-orphan',
        foreign_keys='Vote.user_id'
    )
    
    events_created = db.relationship(
        'Event',
        backref='creator',
        lazy='select',
        foreign_keys='Event.created_by'
    )
    
    added_members = db.relationship(
        'User',
        backref='added_by_user',
        remote_side=[id],
        lazy='select',
        foreign_keys=[added_by]
    )
    
    # ============ Methods ============
    def set_password(self, password):
        """Hash and set password"""
        self.password_hash = generate_password_hash(password)
        self.password_changed_at = datetime.utcnow()
    
    def check_password(self, password):
        """Check if provided password matches hash"""
        return check_password_hash(self.password_hash, password)
    
    def update_last_login(self):
        """Update last login timestamp"""
        self.last_login = datetime.utcnow()
        db.session.commit()
    
    def is_admin(self):
        """Check if user is admin"""
        return self.role.lower() == 'admin'
    
    def is_faculty_or_admin(self):
        """Check if user is faculty or admin"""
        return self.role.lower() in ['admin', 'faculty']
    
    def to_dict(self, include_email=False, include_password=False):
        """Convert user to dictionary"""
        data = {
            'id': self.id,
            'name': self.name,
            'role': self.role,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_email:
            data['email'] = self.email
        if include_password:
            data['password_hash'] = self.password_hash
        return data
    
    def __repr__(self):
        return f'<User id={self.id} email={self.email} role={self.role}>'


# ============ Event Model ============
class Event(db.Model):
    """
    Event model for voting events
    """
    __tablename__ = 'events'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Event info
    name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    description = db.Column(db.Text, nullable=False)
    
    # Voting
    votes = db.Column(db.Integer, default=0, nullable=False)
    
    # Metadata
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    
    # Relationships
    votes_received = db.relationship(
        'Vote',
        backref='event',
        lazy='select',
        cascade='all, delete-orphan',
        foreign_keys='Vote.event_id'
    )
    
    # ============ Methods ============
    def recalculate_votes(self):
        """
        Recalculate votes from Vote table (for data integrity)
        Use this if vote counter gets out of sync
        """
        from sqlalchemy import func
        
        vote_count = db.session.query(func.count(Vote.id)).filter(
            Vote.event_id == self.id
        ).scalar() or 0
        
        self.votes = vote_count
        db.session.commit()
    
    def to_dict(self):
        """Convert event to dictionary"""
        creator = User.query.get(self.created_by)
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'votes': self.votes,
            'created_by': self.created_by,
            'created_by_name': creator.name if creator else 'Unknown',
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_active': self.is_active
        }
    
    def __repr__(self):
        return f'<Event id={self.id} name={self.name} votes={self.votes}>'


# ============ Vote Model ============
class Vote(db.Model):
    """
    Vote model for tracking votes
    
    Constraint: One vote per user (unique user_id)
    """
    __tablename__ = 'votes'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Foreign keys (with indexes for fast lookups)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='CASCADE'),
        unique=True,  # Ensures one vote per user
        nullable=False,
        index=True
    )
    
    event_id = db.Column(
        db.Integer,
        db.ForeignKey('events.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    
    # Metadata
    voted_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    ip_address = db.Column(db.String(45), nullable=True)  # IPv4 or IPv6
    
    # ============ Constraints ============
    __table_args__ = (
        # Composite index for performance
        db.Index('ix_votes_event_user', 'event_id', 'user_id'),
    )
    
    # ============ Methods ============
    def to_dict(self):
        """Convert vote to dictionary"""
        voter = User.query.get(self.user_id)
        event = Event.query.get(self.event_id)
        
        return {
            'id': self.id,
            'user_id': self.user_id,
            'user_name': voter.name if voter else 'Unknown',
            'event_id': self.event_id,
            'event_name': event.name if event else 'Unknown',
            'voted_at': self.voted_at.isoformat() if self.voted_at else None,
        }
    
    def __repr__(self):
        return f'<Vote id={self.id} user={self.user_id} event={self.event_id}>'


# ============ AdminSetting Model ============
class AdminSetting(db.Model):
    """
    Admin settings stored in database (not in-memory)
    Persists across server restarts
    """
    __tablename__ = 'admin_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Setting key (unique)
    key = db.Column(db.String(100), unique=True, nullable=False, index=True)
    
    # Setting value (can be any type, stored as string for flexibility)
    value = db.Column(db.Text, nullable=False)
    
    # Metadata
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    description = db.Column(db.String(255), nullable=True)
    
    # ============ Methods ============
    @staticmethod
    def get(key, default=None):
        """Get setting by key"""
        setting = AdminSetting.query.filter_by(key=key).first()
        if setting:
            # Try to parse as boolean
            if setting.value.lower() in ['true', 'false']:
                return setting.value.lower() == 'true'
            # Try to parse as number
            try:
                return int(setting.value)
            except ValueError:
                pass
            return setting.value
        return default
    
    @staticmethod
    def set(key, value, updated_by=None, description=None):
        """Set setting by key"""
        setting = AdminSetting.query.filter_by(key=key).first()
        if not setting:
            setting = AdminSetting(key=key)
        
        setting.value = str(value)
        setting.updated_by = updated_by
        setting.description = description
        
        db.session.add(setting)
        db.session.commit()
    
    @staticmethod
    def get_all():
        """Get all settings as dictionary"""
        settings = AdminSetting.query.all()
        result = {}
        for setting in settings:
            result[setting.key] = setting.get(setting.key)
        return result
    
    def __repr__(self):
        return f'<AdminSetting {self.key}={self.value}>'


# ============ AuditLog Model (Optional - for compliance) ============
class AuditLog(db.Model):
    """
    Audit log for tracking all sensitive operations
    Helps with compliance and forensics
    """
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # User who performed action
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    # Action details
    action_type = db.Column(db.String(50), nullable=False, index=True)  # e.g., 'VOTE_CAST', 'LOGIN', 'DELETE_USER'
    entity_type = db.Column(db.String(50), nullable=False)  # e.g., 'Vote', 'User', 'Event'
    entity_id = db.Column(db.Integer, nullable=True)
    
    # Change details
    old_value = db.Column(db.Text, nullable=True)
    new_value = db.Column(db.Text, nullable=True)
    
    # Request context
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)
    
    # Timestamp
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Metadata
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='success', nullable=False)  # success, failure
    error_message = db.Column(db.Text, nullable=True)
    
    def __repr__(self):
        return f'<AuditLog {self.action_type} entity={self.entity_type} id={self.entity_id}>'