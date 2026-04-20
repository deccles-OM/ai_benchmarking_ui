"""
Flask application factory for AI Benchmarking UI.
"""
import os
from flask import Flask
from flask_cors import CORS
from app.utils import kill_stuck_processes


def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__, template_folder='../templates', static_folder='../static')
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # Enable CORS
    CORS(app)
    
    # Kill any stuck processes from previous runs
    try:
        print("[INFO] Cleaning up stuck processes from previous runs...")
        kill_stuck_processes()
        print("[INFO] Process cleanup complete.")
    except Exception as cleanup_error:
        print(f"[WARNING] Process cleanup failed: {cleanup_error}")
        import traceback
        traceback.print_exc()
    
    # Register blueprints
    from app.routes import bp
    app.register_blueprint(bp)
    
    # Register root route for main UI (outside blueprint)
    @app.route('/')
    def index():
        """Render main UI at root path."""
        from flask import render_template
        return render_template('index.html')
    
    return app
