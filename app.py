from flask import Flask, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO
from config import Config
from database import db
from models import User, Room, Message, Note, StudySession, Achievement
import os

socketio = SocketIO(cors_allowed_origins="*", async_mode="eventlet")

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    CORS(app, resources={r"/*": {"origins": "*", "allow_headers": ["Authorization", "Content-Type"]}}, supports_credentials=True)
    db.init_app(app)
    socketio.init_app(app)
    
    with app.app_context():
        db.create_all()
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        
    from routes.auth import auth_bp
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    
    from routes.rooms import rooms_bp
    app.register_blueprint(rooms_bp, url_prefix='/api/rooms')
    
    from routes.upload import upload_bp
    app.register_blueprint(upload_bp, url_prefix='/api/upload')
    
    @app.route('/uploads/<path:filename>')
    def serve_upload(filename):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    
    from sockets.events import register_events
    register_events(socketio, db)
    
    @app.route('/api/health')
    def health_check():
        return {'status': 'ok'}
        
    return app

app = create_app()

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=10000)
