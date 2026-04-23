import os

class Config:
    # Basic Flask Settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-fallback-secret-key'
    DEBUG = os.environ.get('FLASK_DEBUG', 'True').lower() in ['true', '1']
    FLASK_ENV = os.environ.get('FLASK_ENV', 'development')
    
    # Server Binding
    HOST = os.environ.get('HOST', '0.0.0.0')
    PORT = int(os.environ.get('PORT', 5001)) # Default 5001 to avoid clashing with node backend
    
    # Database Settings
    basedir = os.path.abspath(os.path.dirname(__file__))
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'instance', 'festvote.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # JWT Settings
    from datetime import timedelta
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'your-jwt-secret-key'
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    
    # CORS Settings
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', 'http://localhost:3000').split(',')
    CORS_ALLOW_HEADERS = ['Content-Type', 'Authorization']
    CORS_METHODS = ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS']
    
    # Admin details
    ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL') or 'admin@festvote.com'

config = Config()
