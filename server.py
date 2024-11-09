from flask import Flask, flash, render_template, request, redirect, url_for, session, Response, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room
from engineio.payload import Payload
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from pymongo.errors import DuplicateKeyError
from datetime import datetime
from flask_cors import CORS
from db import delete_room, remove_course, get_tutor_list2, get_subscription_room_id, remove_room_member, un_subscribe, get_all_students, get_all_subscriptions, subscribe, get_tutor_id, get_all_tutors, save_or_update_tutor, get_tutor, get_user, save_user, save_room, add_room_members, get_rooms_for_user, get_room, is_room_member, \
    get_room_members, is_room_admin, update_room, remove_room_members, save_message, get_messages
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

# Route to login page
@app.route('/login', methods=['GET', 'POST'])
@app.route("/", methods=["GET", "POST"])
def login():
    '''
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = next((user for user in tutors + students if user['username'] == username and user['password'] == password), None)

        if user:
            session['username'] = user['username']
            session['role'] = 'tutor' if user in tutors else 'student'
            session['id'] = user['id']

            return redirect(url_for('tutor_dashboard', tutor_id=user['id']) if session['role'] == 'tutor' else url_for('student_dashboard', student_id=user['id']))
        else:
            return "Invalid username or password", 401
    '''
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
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role')
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
        save_or_update_tutor(name, email, subject, cost)
        #CREATE ROOM FOR NEW COURSE 
        flash('Added New Gig!')
        flash('New chat room created!')
        return redirect(url_for('explore', user_id=tutors.id))

    #tutor = next((tutor for tutor in tutors if tutor['id'] == tutor_id), None)
    return render_template('addgig.html', tutor=tutors)

@app.route("/explore/<string:user_id>", methods=["GET", "POST"])
def explore(user_id):
    all_tutors = get_all_tutors() # returned list of tutors_collection
    #print(all_tutors)
    return render_template('explore.html', all_tutors=all_tutors, name=current_user.username)

# Route to show the subscribed classes
@app.route('/subscribed', methods=["GET", "POST"])
def subscribed():
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
    #print("qwertty")
    #print(all_subscriptions)
    return render_template('subscribed.html', subscriptions=all_subscriptions)

@app.route('/unsubscribe', methods=['POST'])
def unsubscribe():
    subscription_username = request.form.get('subscription_username')
    subscription_name = request.form.get('subscription_name')
    subscription_subject = request.form.get('subscription_subject')
    #room_name= f"{subscription_name}_{subscription_subject}"
    subscription_id=get_subscription_room_id(subscription_name, subscription_subject)
    #print("retrieved SUB ID")
    #print(subscription_id)
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
    return render_template('tutorprofile.html', tutors=tutors) 

# Route to edit tutor profile
@app.route('/tutor/edit/<string:tutor_id>', methods=['GET', 'POST'])
def edit_tutor(tutor_id):
    #tutor = next((tutor for tutor in tutors if tutor['id'] == tutor_id), None)
    #if not tutor:
     #   return "Tutor not found", 404
    #print(current_user.username)
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

@app.route('/remove_subject/<username>/<subject>', methods=['POST'])
def remove_subject(username, subject):
    # Fetch tutor data based on username
    tutor_data = get_tutor_list2(username)  # Ensure this function fetches the correct tutor data format
    
    if tutor_data:
        # tutor_data is expected to be a tuple like (ObjectId, username, email, subjects)
        subjects = tutor_data[3]  # Access the subjects list
        
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
'''
# Route to logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))
'''
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
    #print("hello boss: AT THE FUNCTION")
    app.logger.info("{} has sent message to the room {}: {}".format(data['username'],
                                                                    data['room'],
                                                                    data['message']))
    #print("hello boss: "+data['message'])
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


# Initialize variables for drawing, erasing, and color
img = np.zeros((1024, 1024, 3), np.uint8)
draw = True
erase = True
red = True
thickness = 10  # Thickness of the drawing
flag = 0

# Function to generate frames
def generate_frame():
    # Open Camera
    #camera = cv2.VideoCapture(0)
    camera =  cv2.VideoCapture(0,cv2.CAP_DSHOW)
    
    global img, draw, erase, red, thickness, flag

    while True:
        if flag == 0:  # TOGGLES DRAW AND ERASE FOR FIRST TIME AFTER THAT DEPENDS ON USER
            flag = 1
            draw = not draw
            erase = not erase
            red = not red

        ret, frame = camera.read()
        if not ret:
            break  # Exit if the camera feed is not retrieved

        frame = cv2.resize(frame, (1024, 1024))
        frame = cv2.bilateralFilter(frame, 5, 50, 100)  # Smoothing
        frame = cv2.flip(frame, 1)  # Horizontal Flip

        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        lower = np.array([0, 48, 80], dtype="uint8")
        upper = np.array([20, 255, 255], dtype="uint8")
        skinMask = cv2.inRange(hsv, lower, upper)

        # Getting the contours and convex hull
        skinMask1 = copy.deepcopy(skinMask)
        contours, _ = cv2.findContours(skinMask1, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        if contours:  # If contours are found
            maxArea = -1
            ci = 0
            for i in range(len(contours)):
                area = cv2.contourArea(contours[i])
                if area > maxArea:
                    maxArea = area
                    ci = i

            res = contours[ci]
            hull = cv2.convexHull(res)

            # Moments for centroid calculation
            M = cv2.moments(res)
            cX = int(M["m10"] / M["m00"]) if M["m00"] != 0 else 0
            cY = int(M["m01"] / M["m00"]) if M["m00"] != 0 else 0

            # Getting extreme points
            extLeft = tuple(res[res[:, :, 0].argmin()][0])
            extRight = tuple(res[res[:, :, 0].argmax()][0])
            extTop = tuple(res[res[:, :, 1].argmin()][0])
            extBot = tuple(res[res[:, :, 1].argmax()][0])

            # Draw contours and points
            cv2.drawContours(frame, [res], -1, (0, 255, 0), 2)
            cv2.drawContours(frame, [hull], -1, (0, 0, 255), 3)
            cv2.circle(frame, extLeft, 8, (0, 0, 255), -1)
            cv2.circle(frame, extRight, 8, (0, 255, 0), -1)
            cv2.circle(frame, extTop, 8, (100, 55, 100), -1)
            cv2.circle(frame, extBot, 8, (255, 255, 0), -1)
            cv2.circle(frame, (cX, cY), 7, (255, 255, 255), -1)
            cv2.putText(frame, "center", (cX - 20, cY - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

            # Draw on the image if drawing is enabled
            if draw:
                cv2.circle(img, extTop, thickness, (255, 255, 255), -1)  # Draw circle at fingertip position
            if erase:
                cv2.circle(img, extTop, thickness, (0, 0, 0), 7)  # Erase circle at fingertip position
            if red:
                cv2.circle(img, extTop, thickness, (0, 0, 255), -1)  # Draw red circle at fingertip position

        # Combine the canvas with the frame
        combined_frame = cv2.addWeighted(frame, 0.7, img, 0.3, 0)

        # Convert to JPEG format for streaming
        ret, jpeg = cv2.imencode('.jpg', combined_frame)
        if not ret:
            continue
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n\r\n')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frame(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/toggle_draw', methods=['POST'])
def toggle_draw():
    global draw
    draw = not draw
    return 'OK'

@app.route('/toggle_erase', methods=['POST'])
def toggle_erase():
    global erase
    erase = not erase
    return 'OK'

@app.route('/toggle_red', methods=['POST'])
def toggle_red():
    global red
    red = not red
    return 'OK'

# Route to reset the canvas
@app.route('/toggle_canvas', methods=['POST'])
def toggle_canvas():
    global img
    # Reset the canvas to a blank image
    img = np.zeros((1024, 1024, 3), np.uint8)
    return '', 204  # Return a 'No Content' response to indicate success

@app.route('/virutal_canvas')
def virutal_canvas():
    if current_user.is_authenticated:
        return render_template('virutal_canvas.html')
    else:
        flash('User not logged in!')
        return render_template('login.html')
    

if __name__ == '__main__':
    #socketio.run(app, debug=True)
    socketio.run(app, host='0.0.0.0', debug=True, port=5000)