from flask import Blueprint, request, jsonify
from models import User
from database import db
from passlib.hash import pbkdf2_sha256
import jwt
from datetime import datetime, timedelta
from config import Config
from functools import wraps

auth_bp = Blueprint('auth', __name__)

def generate_token(user_id):
    payload = {
        'exp': datetime.utcnow() + Config.JWT_ACCESS_TOKEN_EXPIRES,
        'iat': datetime.utcnow(),
        'sub': str(user_id)
    }
    return jwt.encode(payload, Config.JWT_SECRET_KEY, algorithm='HS256')

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if request.method == 'OPTIONS':
            return jsonify({}), 200
            
        token = None
        # Debug: print incoming Authorization header for troubleshooting
        try:
            print('Incoming Authorization header:', request.headers.get('Authorization'))
        except Exception:
            pass
        if 'Authorization' in request.headers:
            parts = request.headers['Authorization'].split()
            if len(parts) == 2 and parts[0] == 'Bearer':
                token = parts[1]
        
        if not token:
            print('No token found in request')
            return jsonify({'message': 'Token is missing!'}), 401

        try:
            data = jwt.decode(token, Config.JWT_SECRET_KEY, algorithms=['HS256'])
            current_user = User.query.get(int(data['sub']))
            if not current_user:
                raise Exception("User not found")
        except Exception as e:
            # Debug: print exception to server logs for easier diagnosis
            try:
                print('Token validation error:', str(e))
                print('Token value:', token)
            except Exception:
                pass
            return jsonify({'message': f'Token is invalid! Error: {str(e)}'}), 401
            
        return f(current_user, *args, **kwargs)
    return decorated

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data or not data.get('username') or not data.get('email') or not data.get('password'):
        return jsonify({'message': 'Missing fields!'}), 400
        
    if User.query.filter_by(email=data['email']).first() or User.query.filter_by(username=data['username']).first():
        return jsonify({'message': 'User already exists!'}), 400
        
    hashed_password = pbkdf2_sha256.hash(data['password'])
    new_user = User(
        username=data['username'],
        email=data['email'],
        password_hash=hashed_password
    )
    
    db.session.add(new_user)
    db.session.commit()
    
    token = generate_token(new_user.id)
    return jsonify({
        'message': 'User registered successfully',
        'token': token,
        'user': {
            'id': new_user.id,
            'username': new_user.username,
            'email': new_user.email
        }
    }), 201

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'message': 'Missing fields!'}), 400
        
    user = User.query.filter_by(email=data['email']).first()
    
    if not user or not pbkdf2_sha256.verify(data['password'], user.password_hash):
        return jsonify({'message': 'Invalid credentials!'}), 401
        
    token = generate_token(user.id)
    return jsonify({
        'message': 'Logged in successfully',
        'token': token,
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'avatar': user.avatar,
            'study_streak': user.study_streak,
            'total_study_time': user.total_study_time
        }
    }), 200

@auth_bp.route('/me', methods=['GET'])
@token_required
def get_me(current_user):
    return jsonify({
        'user': {
            'id': current_user.id,
            'username': current_user.username,
            'email': current_user.email,
            'avatar': current_user.avatar,
            'study_streak': current_user.study_streak,
            'total_study_time': current_user.total_study_time,
            'created_at': current_user.created_at.isoformat()
        }
    }), 200
