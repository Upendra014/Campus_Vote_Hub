"""
FestVote - College Fest Voting System
Production-ready Flask Application Entry Point
"""

import os
from flask import Flask, jsonify, request, g
from flask_cors import CORS
from flask_talisman import Talisman
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv
from datetime import datetime
import uuid

# Load environment variables
load_dotenv()

# Import configuration
from config import config

# Import models and database
from database.models import db, User, AdminSetting

# Import utilities
from utils.logging import setup_logging, log_request_response, AuditLogger, get_logger
from utils.decorators import limiter

# Import route blueprints
from routes.auth_routes import auth_bp
from routes.member_routes import member_bp
from routes.event_routes import event_bp
from routes.voting_routes import voting_bp
from routes.admin_routes import admin_bp

logger = get_logger(__name__)


def create_app(config_obj=None):
    """
    Application factory function
    
    Args:
        config_obj: Configuration object (defaults to environment-based config)
    
    Returns:
        Flask app instance
    """
    
    # Initialize Flask app
    app = Flask(__name__, static_folder='static', template_folder='templates')
    
    # ============ CONFIGURATION ============
    if config_obj is None:
        config_obj = config
    
    app.config.from_object(config_obj)
    
    # ============ LOGGING SETUP ============
    setup_logging(app)
    log_request_response(app)
    
    logger.info("=" * 60)
    logger.info("FestVote Application Starting")
    logger.info(f"Environment: {app.config['FLASK_ENV']}")
    logger.info(f"Debug: {app.config['DEBUG']}")
    logger.info("=" * 60)
    
    # ============ CORS CONFIGURATION ============
    cors_config = {
        'origins': app.config['CORS_ORIGINS'],
        'allow_headers': app.config['CORS_ALLOW_HEADERS'],
        'methods': app.config['CORS_METHODS'],
        'supports_credentials': True,
        'max_age': 3600
    }
    
    CORS(app, resources={r"/api/*": cors_config})
    logger.info(f"CORS enabled for origins: {cors_config['origins']}")
    
    # ============ SECURITY HEADERS ============
    # Using Flask-Talisman to add security headers (equivalent to Helmet.js)
    Talisman(
        app,
        force_https=not app.config['DEBUG'],
        strict_transport_security=True,
        strict_transport_security_max_age=31536000,
        content_security_policy={
            'default-src': "'self'",
            'script-src': "'self' 'unsafe-inline'",
            'style-src': "'self' 'unsafe-inline'",
            'img-src': "'self' data: https:",
            'font-src': "'self'",
            'connect-src': "'self'",
        }
    )
    
    # ============ RATE LIMITING ============
    limiter.init_app(app)
    
    # ============ DATABASE ============
    db.init_app(app)
    
    logger.info(f"Database: {app.config['SQLALCHEMY_DATABASE_URI'][:50]}...")
    
    # ============ REQUEST CONTEXT ============
    @app.before_request
    def before_request():
        """Add request context before each request"""
        # Generate request ID for tracing
        g.request_id = request.headers.get('X-Request-ID', str(uuid.uuid4()))
        g.start_time = datetime.utcnow()
        
        # Extract user ID if authenticated
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            try:
                import jwt
                token = auth_header.replace('Bearer ', '').strip()
                payload = jwt.decode(
                    token,
                    app.config['JWT_SECRET_KEY'],
                    algorithms=['HS256']
                )
                g.user_id = payload.get('user_id')
            except:
                g.user_id = None
        else:
            g.user_id = None
    
    @app.after_request
    def after_request(response):
        """Add response headers after each request"""
        # Add request ID to response
        if hasattr(g, 'request_id'):
            response.headers['X-Request-ID'] = g.request_id
        
        # Add security headers
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        
        return response
    
    # ============ DATABASE INITIALIZATION ============
    with app.app_context():
        try:
            # Create all tables
            db.create_all()
            logger.info("Database tables created/verified")
            
            # Create default admin if doesn't exist
            admin = User.query.filter_by(role='admin').first()
            if not admin:
                admin_user = User(
                    name='Admin User',
                    email=app.config['ADMIN_EMAIL'],
                    role='admin'
                )
                admin_user.set_password('TempPassword123!')
                
                db.session.add(admin_user)
                db.session.commit()
                
                logger.warning("⚠️  Default admin created with temporary password!")
                logger.warning(f"Email: {app.config['ADMIN_EMAIL']}")
                logger.warning(f"Password: TempPassword123! (CHANGE IMMEDIATELY)")
            
            # Initialize admin settings in database
            AdminSetting.set('allowVoting', True, description='Allow users to vote')
            AdminSetting.set('allowAddingEvents', True, description='Allow adding new events')
            AdminSetting.set('isLocked', False, description='System is locked')
            AdminSetting.set('maxEvents', 20, description='Maximum number of events allowed')
            AdminSetting.set('finalizedRank', None, description='Number of events to finalize')
            
            logger.info("Admin settings initialized in database")
        
        except Exception as e:
            logger.error(f"Database initialization error: {str(e)}")
            raise
    
    # ============ HEALTH CHECK ENDPOINT ============
    @app.route('/health')
    @limiter.exempt
    def health():
        """Health check endpoint"""
        try:
            # Test database connection
            db.session.execute('SELECT 1')
            db_status = 'healthy'
        except Exception as e:
            db_status = f'unhealthy: {str(e)}'
        
        return jsonify({
            'status': 'healthy',
            'message': 'FestVote API is running',
            'version': '2.0.0',
            'timestamp': datetime.utcnow().isoformat(),
            'database': db_status
        }), 200
    
    # ============ ROOT ENDPOINT ============
    @app.route('/')
    @limiter.exempt
    def index():
        """Serve the main application"""
        try:
            from flask import render_template
            return render_template('index.html')
        except Exception:
            return jsonify({
                'message': 'FestVote API',
                'version': '2.0.0',
                'docs': '/api/docs'
            }), 200
    
    # ============ API DOCUMENTATION ============
    try:
        from flasgger import Swagger
        Swagger(app, template={
            'swagger': '2.0',
            'info': {
                'title': 'FestVote API',
                'version': '2.0.0',
                'description': 'College Fest Voting System API',
                'contact': {
                    'name': 'FestVote Support'
                }
            },
            'basePath': '/api',
            'schemes': ['http', 'https'],
            'securityDefinitions': {
                'Bearer': {
                    'type': 'apiKey',
                    'name': 'Authorization',
                    'in': 'header',
                    'description': 'JWT Authorization header using Bearer scheme'
                }
            }
        })
        logger.info("API documentation enabled at /apidocs")
    except Exception as e:
        logger.warning(f"Could not load API documentation: {str(e)}")
    
    # ============ ERROR HANDLERS ============
    @app.errorhandler(400)
    def bad_request(error):
        """Handle 400 errors"""
        logger.warning(f"Bad request: {str(error)}")
        return jsonify({
            'success': False,
            'error': 'Bad request',
            'code': 'BAD_REQUEST',
            'status': 400
        }), 400
    
    @app.errorhandler(401)
    def unauthorized(error):
        """Handle 401 errors"""
        return jsonify({
            'success': False,
            'error': 'Unauthorized',
            'code': 'UNAUTHORIZED',
            'status': 401
        }), 401
    
    @app.errorhandler(403)
    def forbidden(error):
        """Handle 403 errors"""
        logger.warning(f"Forbidden access: {request.path}")
        return jsonify({
            'success': False,
            'error': 'Forbidden',
            'code': 'FORBIDDEN',
            'status': 403
        }), 403
    
    @app.errorhandler(404)
    def not_found(error):
        """Handle 404 errors"""
        return jsonify({
            'success': False,
            'error': 'Endpoint not found',
            'code': 'NOT_FOUND',
            'status': 404
        }), 404
    
    @app.errorhandler(405)
    def method_not_allowed(error):
        """Handle 405 errors"""
        return jsonify({
            'success': False,
            'error': 'Method not allowed',
            'code': 'METHOD_NOT_ALLOWED',
            'status': 405
        }), 405
    
    @app.errorhandler(429)
    def ratelimit_handler(e):
        """Handle rate limit errors"""
        logger.warning(f"Rate limit exceeded from {get_remote_address()}")
        return jsonify({
            'success': False,
            'error': 'Too many requests. Please try again later.',
            'code': 'RATE_LIMIT_EXCEEDED',
            'status': 429
        }), 429
    
    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 errors"""
        logger.error(f"Internal server error: {str(error)}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'code': 'INTERNAL_ERROR',
            'status': 500
        }), 500
    
    # ============ REGISTER BLUEPRINTS ============
    app.register_blueprint(auth_bp)
    app.register_blueprint(member_bp)
    app.register_blueprint(event_bp)
    app.register_blueprint(voting_bp)
    app.register_blueprint(admin_bp)
    
    logger.info("All route blueprints registered")
    logger.info("=" * 60)
    
    return app


# ============ CREATE APP INSTANCE ============
app = create_app()


# ============ RUN SERVER ============
if __name__ == '__main__':
    """
    Run development server
    
    Production: Use Gunicorn instead:
        gunicorn -w 4 -b 0.0.0.0:5000 --timeout 120 --access-logfile logs/access.log app:app
    """
    port = app.config['PORT']
    host = app.config['HOST']
    debug = app.config['DEBUG']
    
    print(f"""
------------------------------------------------------------
           FestVote - Voting System v2.0.0                  
------------------------------------------------------------

 App              : http://{host}:{port}
 API              : http://{host}:{port}/api
 Documentation    : http://{host}:{port}/apidocs
 Health Check     : http://{host}:{port}/health

 Admin Email      : {app.config['ADMIN_EMAIL']}
 Admin Password   : Check logs (first run only!)

 Environment      : {app.config['FLASK_ENV']}
 Debug            : {debug}

 IMPORTANT:
- Change default admin password immediately
- Update SECRET_KEY in production
- Use PostgreSQL instead of SQLite
- Enable HTTPS in production

Press CTRL + C to stop
------------------------------------------------------------
""")
    
    app.run(
        host=host,
        port=port,
        debug=debug,
        use_reloader=debug
    )