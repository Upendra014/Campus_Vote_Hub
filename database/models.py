'''from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# ================= USER TABLE =================
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)

    role = db.Column(db.String(50), nullable=False)

# ================= EVENT TABLE =================
class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.String(500))

    votes = db.Column(db.Integer, default=0)

# ================= VOTE TABLE =================
class Vote(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, nullable=False)
    event_id = db.Column(db.Integer, nullable=False)
'''
"""
FestVote Database Models
All models with proper relationships and fields
"""

from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()


class User(db.Model):
    """User model for authentication and authorization"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password = db.Column(db.String(255), nullable=False)  # Hashed password
    role = db.Column(db.String(50), default='student', nullable=False)
    # Roles: admin, faculty, coordinator, student
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    added_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    # Relationships
    votes = db.relationship('Vote', backref='voter', lazy=True, cascade='all, delete-orphan')
    events_created = db.relationship('Event', backref='creator', lazy=True, foreign_keys='Event.created_by')
    added_members = db.relationship('User', backref='added_by_user', remote_side=[id], lazy=True)
    
    def set_password(self, password):
        """Hash and set password"""
        self.password = generate_password_hash(password)
    
    def check_password(self, password):
        """Check if provided password matches hash"""
        return check_password_hash(self.password, password)
    
    def to_dict(self, include_email=False):
        """Convert user to dictionary"""
        data = {
            'id': self.id,
            'name': self.name,
            'role': self.role,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
        if include_email:
            data['email'] = self.email
        return data
    
    def __repr__(self):
        return f'<User {self.email}>'


class Event(db.Model):
    """Event model for voting events"""
    __tablename__ = 'events'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    description = db.Column(db.Text, nullable=False)
    votes = db.Column(db.Integer, default=0)
    
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    votes_received = db.relationship('Vote', backref='event', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        """Convert event to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'votes': self.votes,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
    
    def __repr__(self):
        return f'<Event {self.name}>'


class Vote(db.Model):
    """Vote model for tracking votes"""
    __tablename__ = 'votes'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True, index=True)
    # unique=True ensures one vote per user
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=False, index=True)
    
    voted_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        """Convert vote to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'user_name': self.voter.name if self.voter else 'Unknown',
            'event_id': self.event_id,
            'event_name': self.event.name if self.event else 'Unknown',
            'voted_at': self.voted_at.isoformat() if self.voted_at else None,
        }
    
    def __repr__(self):
        return f'<Vote user={self.user_id} event={self.event_id}>'