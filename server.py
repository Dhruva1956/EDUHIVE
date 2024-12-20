from flask import Flask, flash, render_template, request, redirect, url_for, session, Response, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room
from engineio.payload import Payload
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from pymongo.errors import DuplicateKeyError
from datetime import datetime
from flask_cors import CORS
from db import delete_room, remove_course, get_tutor_list2, get_subscription_room_id, remove_room_member, un_subscribe, get_all_students, get_all_subscriptions, subscribe, get_tutor_id, get_all_tutors, save_or_update_tutor, get_tutor, get_user, save_user, save_room, add_room_members, get_rooms_for_user, get_room, is_room_member, \
    get_room_members, is_room_admin, update_room, remove_room_members, save_message, get_messages, new_save_or_update_tutor, new_save_or_update_tutor_username
import cv2
import numpy as np
import copy
# Set the maximum number of packets to be decoded
Payload.max_decode_packets = 200

app = Flask(__name__)
app.config['SECRET_KEY'] = "thisismys3cr3tk3y"
CORS(app)
app.secret_key = "GoldenLetter"
socketio = SocketIO(app, cors_allowed_origins="*")
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)



# Dummy data for tutors and students
'''
tutors = [
    {'id': 1, 'name': 'John Doe', 'subject': 'Mathematics', 'cost': '$30/hour', 'username': 'johndoe', 'password': 'math123'},
    {'id': 2, 'name': 'Jane Smith', 'subject': 'English', 'cost': '$25/hour', 'username': 'janesmith', 'password': 'english123'},
    {'id': 3, 'name': 'Emma Brown', 'subject': 'Physics', 'cost': '$40/hour', 'username': 'emmabrown', 'password': 'physics123'}
]

students = [
    {'id': 101, 'name': 'Student One', 'username': 'student1', 'password': 'studentpass'},
    {'id': 102, 'name': 'Student Two', 'username': 'student2', 'password': 'studentpass'}
]
'''
_users_in_room = {}  # Stores users in each room
_room_of_sid = {}    # Maps socket IDs to rooms
_name_of_sid = {}    # Maps socket IDs to user display names

@app.route('/home')
def home():
    return "hello home"

@app.route('/landing')
@app.route("/", methods=["GET", "POST"])
def landing():
    return render_template('landing.html')

# Route to login page
@app.route('/login', methods=['GET', 'POST'])
#@app.route("/", methods=["GET", "POST"])
def login():
    rooms = []
    if current_user.is_authenticated:
        #print(current_user.username)
        return redirect(url_for('tutor_dashboard', tutor_id=current_user.id) if current_user.role == 'tutor' else url_for('student_dashboard', student_id=current_user.id))
    
    message = ''
    if request.method == 'POST':
        username = request.form.get('username')
        password_input = request.form.get('password')
        user = get_user(username)

        if user and user.check_password(password_input):
            login_user(user)
            #print(user.id)
            flash('Logged In successfully!', 'success')
            return redirect(url_for('tutor_dashboard', tutor_id=user.id) if user.role == 'tutor' else url_for('student_dashboard', student_id=user.id))
        else:
            message = 'Failed to Login!'
            flash('Failed to Login!')
    return render_template('login.html', message=message)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        flash('Authenticated!')
        return redirect(url_for('home'))
    message = ''
    if request.method == 'POST':
        all_tutors = get_all_tutors() # returned list of tutors_collection
        
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role')
        for tutor in all_tutors:
            if tutor['username'] == username:
                flash('Update Unsuccessful. The username already exists!')
                return render_template('signup.html')
            if tutor['email'] == email:
                flash('Update Unsuccessful. The email already exists!')
                return render_template('signup.html')
            
        try:
            save_user(username, email, password, role)
            flash('Signup successfull!')
            return redirect(url_for('login'))
        except DuplicateKeyError:
            message = "User Already Exists!!"
            flash('User Already Exists!')
    return render_template('signup.html', message=message)

# Tutor dashboard
@app.route('/tutor/dashboard/<string:tutor_id>')
def tutor_dashboard(tutor_id):
    #tutor = next((tutor for tutor in tutors if tutor['id'] == tutor_id), None)
    rooms = []
    if current_user.is_authenticated:
        rooms = get_rooms_for_user(current_user.username)
        return render_template('tutor_dashboard.html', rooms=rooms, tutor_id=current_user.id)
    else: 
        flash('Tutor not found!')
        return "Tutor not found"

# Student dashboard
@app.route('/student/dashboard/<string:student_id>')
def student_dashboard(student_id):
    #student = next((student for student in students if student['id'] == student_id), None)
    rooms = []
    if current_user.is_authenticated:
        rooms = get_rooms_for_user(current_user.username)
        #print(current_user.username)
        return render_template('student_dashboard.html', rooms=rooms, student_id=current_user.id) 
    else:
        return "Student not found"

# Route to add a new gig (course)
@app.route('/addgig/<string:tutor_id>', methods=['GET', 'POST'])
def add_gig(tutor_id):
    tutors = get_tutor(current_user.username)

    if request.method == 'POST':
        '''
        new_course = {
            'id': len(tutors) + 1,
            'name': request.form['name'],
            'subject': request.form['subject'],
            'cost': request.form['cost']
        }
        
        tutors.append(new_course)
        '''
        name= tutors.username
        email= tutors.email
        subject= request.form['subject']
        cost= request.form['cost']
        about= request.form['about']
        #print(about)
        
        new_save_or_update_tutor(name, email, subject, cost, about)
        #CREATE ROOM FOR NEW COURSE 
        flash('Added New Gig!')
        flash('New chat room created!')
        return redirect(url_for('explore', user_id=tutors.id))

    #tutor = next((tutor for tutor in tutors if tutor['id'] == tutor_id), None)
    return render_template('addgig.html', tutor=tutors)

@app.route("/explore/<string:user_id>", methods=["GET", "POST"])
def explore(user_id):
    all_tutors = get_all_tutors() # returned list of tutors_collection
    print(all_tutors)
    return render_template('explore.html', all_tutors=all_tutors, name=current_user.username)

# Route to show the subscribed classes
@app.route('/subscribed', methods=["GET", "POST"])
def subscribed():

    if current_user.role == 'tutor':
        flash('Subscription is unavailable for tutors. Please switch to a student profile!')
        return redirect(url_for("display_subscriptions", id=current_user.id))

    username = request.form.get('username')
    email = request.form.get('email')
    tutor_name = request.form.get('tutor_name')
    tuition_subject = request.form.get('tuition_subject')
    tutor_email = request.form.get('tutor_email')
    subscribe(username, email, tutor_name, tuition_subject, tutor_email)
    flash('Subscribed succesfully!')
    flash('Added into course room!')
    return redirect(url_for("display_subscriptions", id=current_user.id))

@app.route('/subscriptions/<string:id>')
def display_subscriptions(id):
    if current_user.role=="student":
        all_subscriptions = get_all_subscriptions(current_user.username)
    if current_user.role=="tutor":
        #all_subscriptions = get_all_subscriptions(current_user.username)
        all_subscriptions = get_all_students(current_user.username)
    #print(all_subscriptions)
    return render_template('subscribed.html', subscriptions=all_subscriptions)

@app.route('/unsubscribe', methods=['POST'])
def unsubscribe():
    subscription_username = request.form.get('subscription_username')
    subscription_name = request.form.get('subscription_name')
    subscription_subject = request.form.get('subscription_subject')
    #room_name= f"{subscription_name}_{subscription_subject}"
    subscription_id=get_subscription_room_id(subscription_name, subscription_subject)
    if subscription_id:
        #print("INITIATED UN SUBSCRIBE")
        # Code to remove subscription from database
        un_subscribe(subscription_id, subscription_username, subscription_name, subscription_subject)
    flash('unsubscribed succesfully!')
    return redirect(url_for('display_subscriptions', id=current_user.id))

# Dynamic route to show tutor profile based on ID
@app.route('/tutor/<string:tutor_id>')
def tutor_profile(tutor_id):
    tutors = get_tutor_id(tutor_id)
    print(tutors)
    return render_template('tutorprofile.html', tutors=tutors) 

# Route to edit tutor profile
@app.route('/tutor/edit/<string:tutor_id>', methods=['GET', 'POST'])
def edit_tutor(tutor_id):
    tutors = get_tutor_list2(current_user.username)
    
    #print(tutors)
    
    if request.method == 'POST':
        username= request.form['username']
        subject = request.form['subject']
        cost = request.form['cost']
        tutors= get_tutor(username)
        save_or_update_tutor(username, tutors.email, subject, cost)
        tutors = get_tutor_id(tutor_id)
        flash('Update Succesful!')
        return render_template('tutorprofile.html', tutors=tutors)
    
    return render_template('edit_tutor.html', tutor=tutors)

# Route to edit core tutor profile
@app.route('/tutor/edit/core/<string:tutor_id>', methods=['GET', 'POST'])
def edit_core_tutor(tutor_id):
    tutors = get_tutor_list2(current_user.username)
    all_tutors = get_all_tutors() # returned list of tutors_collection
    if request.method == 'POST':
        tutors = get_tutor_list2(current_user.username)
        all_tutors = get_all_tutors() # returned list of tutors_collection
   
        username = request.form['username']
        email = request.form['email']
        about = request.form['about']

        # Check if the data already exists in the tutors list
        for tutor in all_tutors:
            
            if tutor['about'] == about:
                flash('Update Unsuccessful. The data already exists!')
                return render_template('edit_tutor.html', tutor=tutors)

        # Proceed with saving or updating the tutor
        
        new_save_or_update_tutor_username(username, email, "","",about)
        #core_save_or_update_tutor(username, email, about)

        # Refresh tutor data
        tutors = get_tutor_id(tutor_id)
        get_tutor(username)
        flash('Update Successful!')
        return render_template('tutorprofile.html', tutors=tutors)
    
    return render_template('edit_tutor.html', tutor=tutors)


@app.route('/remove_subject/<username>/<subject>', methods=['POST'])
def remove_subject(username, subject):
    # Fetch tutor data based on username
    tutor_data = get_tutor_list2(username)  # Ensure this function fetches the correct tutor data format
    
    if tutor_data:
        # tutor_data is expected to be a tuple like (ObjectId, username, email, subjects)
        subjects = tutor_data[4]  # Access the subjects list
        
        # Filter out the subject to be removed
        updated_subjects = [sub for sub in subjects if sub['subject'] != subject]
        
        # Update the tutor's subjects in the database
        remove_course(username, updated_subjects)
        room_name= f"{username}_{subject}"
        delete_room(room_name)
        
        
        # Optionally, flash a message to inform the user
        flash(f'Subject "{subject}" removed successfully!')

    # Redirect back to the tutor's profile page
    return redirect(url_for('login'))

@app.route("/profile", methods=["GET", "POST"])
def profile():
    return render_template("profile.html")

@app.route("/videocall", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        room_id = request.form['room_id']
        #print(room_id)
        return redirect(url_for("entry_checkpoint", room_id=room_id))
    return render_template("home.html")

@app.route("/room/<string:room_id>/")
def enter_room(room_id):
    if room_id not in session:
        return redirect(url_for("entry_checkpoint", room_id=room_id))
    return render_template("chatroom.html", room_id=room_id, display_name=current_user.username, mute_audio=session[room_id]["mute_audio"], mute_video=session[room_id]["mute_video"])

@app.route("/room/<string:room_id>/checkpoint/", methods=["GET", "POST"])
def entry_checkpoint(room_id):
    if request.method == "POST":
        display_name = request.form['display_name']
        mute_audio = request.form['mute_audio']
        mute_video = request.form['mute_video']
        session[room_id] = {"name": display_name, "mute_audio": mute_audio, "mute_video": mute_video}
        return redirect(url_for("enter_room", room_id=room_id))

    return render_template("chatroom_checkpoint.html", room_id=room_id)

# SocketIO events
@socketio.on("connect")
def on_connect():
    print("New socket connected: ", request.sid)

@socketio.on("join-room")
def on_join_room(data):
    sid = request.sid
    room_id = data["room_id"]
    display_name = session[room_id]["name"]

    join_room(room_id)
    _room_of_sid[sid] = room_id
    _name_of_sid[sid] = display_name

    print(f"[{room_id}] New member joined: {display_name}< {sid}>")
    flash(f"[{room_id}] New member joined: {display_name}< {sid}>")
    
    emit("user-connect", {"sid": sid, "name": display_name}, broadcast=True, include_self=False, room=room_id)

    # Maintain user list on server
    if room_id not in _users_in_room:
        _users_in_room[room_id] = [sid]
        emit("user-list", {"my_id": sid})
    else:
        usrlist = {u_id: _name_of_sid[u_id] for u_id in _users_in_room[room_id]}
        emit("user-list", {"list": usrlist, "my_id": sid})
        _users_in_room[room_id].append(sid)

@socketio.on("disconnect")
def on_disconnect():
    sid = request.sid
    room_id = _room_of_sid[sid]
    display_name = _name_of_sid[sid]

    print(f"[{room_id}] Member left: {display_name}< {sid}>")
    flash(f"[{room_id}] Member left: {display_name}< {sid}>")
    emit("user-disconnect", {"sid": sid}, broadcast=True, include_self=False, room=room_id)

    _users_in_room[room_id].remove(sid)
    if len(_users_in_room[room_id]) == 0:
        _users_in_room.pop(room_id)

    _room_of_sid.pop(sid)
    _name_of_sid.pop(sid)

@socketio.on("data")
def on_data(data):
    sender_sid = data['sender_id']
    target_sid = data['target_id']

    if data["type"] != "new-ice-candidate":
        print('{} message from {} to {}'.format(data["type"], sender_sid, target_sid))

    socketio.emit("data", data, room=target_sid)

@app.route("/logout/")
@login_required
def logout():
    logout_user()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('login'))

#MESSAGES RELATED METHODS BELOW
@app.route('/create-room/', methods=['GET', 'POST'])
@login_required
def create_room():
    message = ''
    if request.method == 'POST':
        room_name = request.form.get('room_name')
        usernames = [username.strip() for username in request.form.get('members').split(',')]

        if len(room_name) and len(usernames):
            room_id = save_room(room_name, current_user.username)
            if current_user.username in usernames:
                usernames.remove(current_user.username)
            add_room_members(room_id, room_name, usernames, current_user.username)
            return redirect(url_for('view_room', room_id=room_id))
        else:
            message = "Failed to create room"
    return render_template('create_room.html', message=message)

@app.route('/rooms/<room_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_room(room_id):
    room = get_room(room_id)
    if room and is_room_admin(room_id, current_user.username):
        existing_room_members = [member['_id']['username'] for member in get_room_members(room_id)]
        room_members_str = ",".join(existing_room_members)
        message = ''
        if request.method == 'POST':
            room_name = request.form.get('room_name')
            room['name'] = room_name
            update_room(room_id, room_name)

            new_members = usernames = [username.strip() for username in request.form.get('members').split(',')]
            members_to_add = list(set(new_members) - set(existing_room_members))
            members_to_remove = list(set(existing_room_members) - set(new_members))

            if len(members_to_add):
                add_room_members(room_id, room_name, members_to_add, current_user.username)

            if len(members_to_remove):
                remove_room_members(room_id, members_to_remove)
            message = 'Room Edited Succesfully'
            room_members_str = ",".join(new_members)
        return render_template('edit_room.html', room=room, room_members_str=room_members_str, message=message)
    else:
        return "Room Not Found", 404

@app.route("/rooms/<room_id>/send_message", methods=['POST'])
@login_required
def send_message(room_id):
    room = get_room(room_id)
    if room and is_room_member(room_id, current_user.username):
        message = request.form.get('message')

        # Check if message is not empty
        if message:
            save_message(room_id, message, current_user.username)

        # Redirect back to the room after saving the message
        return redirect(url_for('view_room', room_id=room_id))
    else:
        return "Room Not Found", 404

@app.route("/inbox/<string:id>")
@login_required
def inbox(id):
    rooms = get_rooms_for_user(current_user.username)
    return render_template('inbox.html', rooms=rooms)

@app.route("/rooms/<room_id>/")
@login_required
def view_room(room_id):
    room = get_room(room_id)
    if room and is_room_member(room_id, current_user.username):
        room_members = get_room_members(room_id)
        messages = get_messages(room_id)
        return render_template('view_room.html', username=current_user.username, room=room, room_members=room_members, messages=messages)
    else:
        return "Room Not Found", 404

'''
@app.route("/rooms/<room_id>/")
@login_required
def view_room(room_id):
    print("Send message function activated")
    room = get_room(room_id)
    print(room)
    if room and is_room_member(room_id, current_user.username):
        room_members = get_room_members(room_id)
        messages = get_messages(room_id)
        print(messages)
        return render_template('view_room.html', username=current_user.username, room=room, room_members=room_members, messages=messages)
    else:
        return "Room Not Found", 404
'''

@socketio.on('send_message')
def handle_send_message_event(data):
    app.logger.info("{} has sent message to the room {}: {}".format(data['username'],
                                                                    data['room'],
                                                                    data['message']))
    data['created_at'] = datetime.now().strftime("%d %b, %H:%M")
    save_message(data['room'], data['message'], data['username'])
    socketio.emit('receive_message', data, room=data['room'])

'''
def test_save_message():
    data = {
        "room": "test_room_id",
        "message": "Test message",
        "username": "test_user"
    }
    try:
        save_message(data['room'], data['message'], data['username'])
        print("Message saved successfully")
    except Exception as e:
        print("Failed to save message:", e)

test_save_message()
'''

@socketio.on('join_room')
def handle_join_room_event(data):
    app.logger.info("{} has joined the room {}".format(data['username'], data['room']))
    join_room(data['room'])
    socketio.emit('join_room_announcement', data)

@login_manager.user_loader
def load_user(username):
    return get_user(username)

@socketio.on('connect')
def handle_connect():
    print("Client connected!")    

if __name__ == '__main__':
    #socketio.run(app, debug=True)
    socketio.run(app, host='0.0.0.0', debug=True, port=5000)