'''
from flask import Flask, render_template
from flask_cors import CORS

from database.models import db, User

# Import Routes
from routes.auth_routes import auth_bp
from routes.member_routes import member_bp
from routes.event_routes import event_bp
from routes.voting_routes import voting_bp
from routes.admin_routes import admin_bp

app = Flask(__name__)
CORS(app)

import os

# ================= DATABASE CONFIG =================
# use an absolute path to avoid relative-directory issues
base_dir = os.path.abspath(os.path.dirname(__file__))
db_file = os.path.join(base_dir, "database", "db.sqlite3")
# make sure database directory exists before SQLAlchemy tries to open the file
os.makedirs(os.path.dirname(db_file), exist_ok=True)

app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_file}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

# ================= CREATE TABLES + DEFAULT ADMIN =================
with app.app_context():
    db.create_all()

    # Ensure Only ONE Admin Exists
    admin = User.query.filter_by(role="Admin").first()
    if not admin:
        default_admin = User(
            name="Admin",
            email="admin@fest.com",
            role="Admin"
        )
        db.session.add(default_admin)
        db.session.commit()

# ================= FRONTEND ROUTE =================
@app.route("/")
def home():
    return render_template("index.html")

# ================= REGISTER BLUEPRINT ROUTES =================
app.register_blueprint(auth_bp)
app.register_blueprint(member_bp)
app.register_blueprint(event_bp)
app.register_blueprint(voting_bp)
app.register_blueprint(admin_bp)

# ================= RUN SERVER =================
if __name__ == "__main__":
    app.run(debug=True)
'''

"""
FestVote - College Fest Voting System
Main Flask Application Entry Point
"""

import os
from flask import Flask, render_template, jsonify
from flask_cors import CORS
from datetime import timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import models and database
from database.models import db, User
from werkzeug.security import generate_password_hash

# Import Blueprints (routes)
from routes.auth_routes import auth_bp
from routes.member_routes import member_bp
from routes.event_routes import event_bp
from routes.voting_routes import voting_bp
from routes.admin_routes import admin_bp


def create_app():
    """Application factory function"""
    
    # Initialize Flask app
    app = Flask(__name__)
    
    # ================= CORS SETUP =================
    CORS(app)
    
    # ================= CONFIGURATION =================
    # Secret key for JWT and sessions
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-CHANGE-IN-PRODUCTION')
    app.config['JWT_SECRET_KEY'] = app.config['SECRET_KEY']
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(days=7)
    
    # ================= DATABASE CONFIGURATION =================
    base_dir = os.path.abspath(os.path.dirname(__file__))
    database_dir = os.path.join(base_dir, 'database')
    os.makedirs(database_dir, exist_ok=True)
    
    db_file = os.path.join(database_dir, 'db.sqlite3')
    
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_file}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize database
    db.init_app(app)
    
    # ================= CREATE TABLES & SEED DEFAULT DATA =================
    with app.app_context():
        # Create all tables
        db.create_all()
        
        # Create default admin if it doesn't exist
        admin = User.query.filter_by(role='admin').first()
        if not admin:
            admin_user = User(
                name='Admin User',
                email='admin@fest.com',
                role='admin'
            )
            admin_user.set_password('admin123')
            
            db.session.add(admin_user)
            db.session.commit()
            print("✅ Default admin created: admin@fest.com / admin123")
    
    # ================= FRONTEND ROUTES =================
    @app.route('/')
    def index():
        """Serve the main application"""
        return render_template('index.html')
    
    @app.route('/health')
    def health():
        """Health check endpoint"""
        return jsonify({
            'status': 'healthy',
            'message': 'FestVote API is running',
            'version': '1.0.0'
        }), 200
    
    # ================= ERROR HANDLERS =================
    @app.errorhandler(404)
    def not_found(error):
        """Handle 404 errors"""
        return jsonify({
            'success': False,
            'error': 'Endpoint not found',
            'status': 404
        }), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 errors"""
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'status': 500
        }), 500
    
    @app.errorhandler(405)
    def method_not_allowed(error):
        """Handle 405 errors"""
        return jsonify({
            'success': False,
            'error': 'Method not allowed',
            'status': 405
        }), 405
    
    # ================= REGISTER BLUEPRINTS =================
    app.register_blueprint(auth_bp)
    app.register_blueprint(member_bp)
    app.register_blueprint(event_bp)
    app.register_blueprint(voting_bp)
    app.register_blueprint(admin_bp)
    
    return app


# ================= CREATE APP INSTANCE =================
app = create_app()


# ================= RUN SERVER =================
if __name__ == '__main__':
    """
    Run development server
    
    Production: Use Gunicorn instead
    gunicorn -w 4 -b 0.0.0.0:5000 app:app
    """
    PORT = int(os.getenv('PORT', 5000))
    DEBUG = os.getenv('FLASK_ENV') == 'development'
    
    print(f"""
    ╔════════════════════════════════════════╗
    ║     FestVote - Voting System Started   ║
    ║                                        ║
    ║  🌐 http://localhost:{PORT}                 ║
    ║  🔌 API: http://localhost:{PORT}/api      ║
    ║  ❤️  Health: http://localhost:{PORT}/health ║
    ║                                        ║
    ║  📝 Admin: admin@fest.com / admin123  ║
    ║                                        ║
    ║  Press CTRL+C to stop                 ║
    ╚════════════════════════════════════════╝
    """)
    
    app.run(
        host='0.0.0.0',
        port=PORT,
        debug=DEBUG,
        use_reloader=DEBUG
    )