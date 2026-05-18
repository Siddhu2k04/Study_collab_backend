from flask_socketio import emit, join_room, leave_room
from models import Message, User
import datetime

room_states = {}
room_participants = {}

def register_events(socketio, db):
    @socketio.on('join_room')
    def handle_join_room(data):
        room = data.get('room_id')
        user_id = data.get('user_id')
        username = data.get('username')
        if room and username:
            join_room(room)
            
            if room not in room_participants:
                room_participants[room] = {}
            
            emit('user_joined', {'username': username, 'user_id': user_id}, room=room, include_self=False)
            
            room_participants[room][user_id] = username
            
            if room in room_states:
                state = room_states[room].copy()
                state['participants'] = [{'user_id': k, 'username': v} for k, v in room_participants[room].items()]
                emit('room_state_sync', state)
            else:
                room_states[room] = {}
                emit('room_state_sync', {'participants': [{'user_id': k, 'username': v} for k, v in room_participants[room].items()]})

    @socketio.on('leave_room')
    def handle_leave_room(data):
        room = data.get('room_id')
        username = data.get('username')
        if room and username:
            leave_room(room)
            
            if room in room_participants:
                to_delete = None
                for uid, uname in room_participants[room].items():
                    if uname == username:
                        to_delete = uid
                        break
                if to_delete:
                    del room_participants[room][to_delete]
                    
            emit('user_left', {'username': username}, room=room, include_self=False)

    @socketio.on('send_message')
    def handle_send_message(data):
        room = data.get('room_id')
        user_id = data.get('user_id')
        message_text = data.get('message')
        
        if room and user_id and message_text:
            user = db.session.get(User, user_id)
            if user:
                new_message = Message(room_id=room, sender_id=user.id, message=message_text)
                db.session.add(new_message)
                db.session.commit()
                
                emit('receive_message', {
                    'id': new_message.id,
                    'user_id': user.id,
                    'username': user.username,
                    'message': message_text,
                    'timestamp': new_message.timestamp.isoformat() + "Z"
                }, room=room)

    @socketio.on('typing_message')
    def handle_typing_message(data):
        room = data.get('room_id')
        username = data.get('username')
        is_typing = data.get('is_typing')
        if room and username:
            emit('user_typing', {'username': username, 'is_typing': is_typing}, room=room, include_self=False)

    @socketio.on('pdf_uploaded')
    def handle_pdf_uploaded(data):
        room = data.get('room_id')
        url = data.get('url')
        if room and url:
            if room not in room_states: room_states[room] = {}
            room_states[room]['pdf_url'] = url
            room_states[room]['pdf_page'] = 1
            emit('sync_pdf_url', {'url': url}, room=room, include_self=False)

    @socketio.on('page_change')
    def handle_page_change(data):
        room = data.get('room_id')
        page = data.get('page')
        if room and page is not None:
            if room not in room_states: room_states[room] = {}
            room_states[room]['pdf_page'] = page
            emit('sync_page', {'page': page}, room=room, include_self=False)

    @socketio.on('zoom_change')
    def handle_zoom_change(data):
        room = data.get('room_id')
        zoom = data.get('zoom')
        if room and zoom is not None:
            if room not in room_states: room_states[room] = {}
            room_states[room]['pdf_zoom'] = zoom
            emit('sync_zoom', {'zoom': zoom}, room=room, include_self=False)

    @socketio.on('note_update')
    def handle_note_update(data):
        room = data.get('room_id')
        content = data.get('content')
        if room and content is not None:
            if room not in room_states: room_states[room] = {}
            room_states[room]['note_content'] = content
            emit('sync_note', {'content': content}, room=room, include_self=False)

    @socketio.on('video_change')
    def handle_video_change(data):
        room = data.get('room_id')
        video_id = data.get('video_id')
        if room and video_id:
            if room not in room_states: room_states[room] = {}
            room_states[room]['video_id'] = video_id
            emit('sync_video_change', {'video_id': video_id}, room=room, include_self=False)

    @socketio.on('video_play')
    def handle_video_play(data):
        room = data.get('room_id')
        time = data.get('time')
        if room:
            if room not in room_states: room_states[room] = {}
            room_states[room]['video_playing'] = True
            room_states[room]['video_time'] = time
            emit('sync_video_play', {'time': time}, room=room, include_self=False)

    @socketio.on('video_pause')
    def handle_video_pause(data):
        room = data.get('room_id')
        time = data.get('time')
        if room:
            if room not in room_states: room_states[room] = {}
            room_states[room]['video_playing'] = False
            room_states[room]['video_time'] = time
            emit('sync_video_pause', {'time': time}, room=room, include_self=False)

    @socketio.on('video_seek')
    def handle_video_seek(data):
        room = data.get('room_id')
        time = data.get('time')
        if room:
            if room not in room_states: room_states[room] = {}
            room_states[room]['video_time'] = time
            emit('sync_video_seek', {'time': time}, room=room, include_self=False)

    @socketio.on('timer_start')
    def handle_timer_start(data):
        room = data.get('room_id')
        mode = data.get('mode') # focus or break
        duration = data.get('duration') # in seconds
        if room:
            if room not in room_states: room_states[room] = {}
            started_at = datetime.datetime.utcnow().isoformat() + "Z"
            room_states[room]['timer'] = {'mode': mode, 'duration': duration, 'started_at': started_at, 'running': True}
            emit('sync_timer_start', {'mode': mode, 'duration': duration, 'started_at': started_at}, room=room, include_self=False)

    @socketio.on('timer_pause')
    def handle_timer_pause(data):
        room = data.get('room_id')
        time_left = data.get('time_left')
        if room:
            if room not in room_states: room_states[room] = {}
            room_states[room]['timer'] = room_states[room].get('timer', {})
            room_states[room]['timer'].update({'time_left': time_left, 'running': False})
            emit('sync_timer_pause', {'time_left': time_left}, room=room, include_self=False)

    @socketio.on('timer_complete')
    def handle_timer_complete(data):
        room = data.get('room_id')
        user_id = data.get('user_id')
        duration = data.get('duration') # duration in seconds
        
        if room:
            if room in room_states and 'timer' in room_states[room]:
                room_states[room]['timer']['running'] = False
            emit('sync_timer_complete', {}, room=room, include_self=False)
            
        if user_id and duration:
            from models import Achievement, StudySession
            user = db.session.get(User, user_id)
            if user:
                # Add study session
                minutes = duration // 60
                session = StudySession(user_id=user.id, room_id=room, duration=minutes)
                db.session.add(session)
                
                # Update total study time
                user.total_study_time += minutes
                
                # Check for new achievements
                unlocked = []
                
                # Achievement: First Session
                if not Achievement.query.filter_by(user_id=user.id, achievement_name='First Focus').first():
                    new_ach = Achievement(user_id=user.id, achievement_name='First Focus')
                    db.session.add(new_ach)
                    unlocked.append({'name': 'First Focus', 'icon': 'Target'})
                    
                # Achievement: 100 Hours (6000 minutes)
                if user.total_study_time >= 6000 and not Achievement.query.filter_by(user_id=user.id, achievement_name='100 Hours Studied').first():
                    new_ach = Achievement(user_id=user.id, achievement_name='100 Hours Studied')
                    db.session.add(new_ach)
                    unlocked.append({'name': '100 Hours Studied', 'icon': 'Award'})
                    
                # Achievement: 7 Day Streak
                if user.study_streak >= 7 and not Achievement.query.filter_by(user_id=user.id, achievement_name='7 Day Streak').first():
                    new_ach = Achievement(user_id=user.id, achievement_name='7 Day Streak')
                    db.session.add(new_ach)
                    unlocked.append({'name': '7 Day Streak', 'icon': 'Flame'})
                    
                # Achievement: Night Owl (studying between 12 AM and 4 AM)
                current_hour = datetime.datetime.now().hour
                if current_hour >= 0 and current_hour < 4:
                    if not Achievement.query.filter_by(user_id=user.id, achievement_name='Night Owl').first():
                        new_ach = Achievement(user_id=user.id, achievement_name='Night Owl')
                        db.session.add(new_ach)
                        unlocked.append({'name': 'Night Owl', 'icon': 'Flame'})
                        
                # Achievement: Deep Focus Master (session longer than 120 minutes)
                if minutes >= 120:
                    if not Achievement.query.filter_by(user_id=user.id, achievement_name='Deep Focus Master').first():
                        new_ach = Achievement(user_id=user.id, achievement_name='Deep Focus Master')
                        db.session.add(new_ach)
                        unlocked.append({'name': 'Deep Focus Master', 'icon': 'Target'})
                
                db.session.commit()
                
                if unlocked:
                    emit('achievement_unlocked', {'achievements': unlocked})
