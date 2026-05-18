from flask import Blueprint, request, jsonify
from models import Room
from database import db
from routes.auth import token_required
import string
import random

rooms_bp = Blueprint('rooms', __name__)

def generate_room_code():
    while True:
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        if not Room.query.filter_by(room_code=code).first():
            return code

@rooms_bp.route('/create', methods=['POST', 'OPTIONS'])
@token_required
def create_room(current_user):
    if request.method == 'OPTIONS':
        return jsonify({}), 200
        
    room_code = generate_room_code()
    new_room = Room(room_code=room_code, created_by=current_user.id)
    
    db.session.add(new_room)
    db.session.commit()
    
    return jsonify({
        'message': 'Room created successfully',
        'room': {
            'id': new_room.id,
            'room_code': new_room.room_code
        }
    }), 201

@rooms_bp.route('/join', methods=['POST', 'OPTIONS'])
@token_required
def join_room(current_user):
    data = request.get_json()
    room_code = data.get('room_code')
    
    if not room_code:
        return jsonify({'message': 'Room code is required!'}), 400
        
    room = Room.query.filter_by(room_code=room_code).first()
    
    if not room:
        return jsonify({'message': 'Room not found!'}), 404
        
    return jsonify({
        'message': 'Joined room successfully',
        'room': {
            'id': room.id,
            'room_code': room.room_code
        }
    }), 200
