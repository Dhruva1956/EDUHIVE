from flask import Flask, render_template, request, redirect, url_for, session
from flask_socketio import SocketIO, emit, join_room, leave_room
from engineio.payload import Payload

# Set the maximum number of packets to be decoded
Payload.max_decode_packets = 200

app = Flask(__name__)
app.config['SECRET_KEY'] = "thisismys3cr3tk3y"

# Initialize SocketIO
socketio = SocketIO(app)

# Dummy data for tutors and students
tutors = [
    {'id': 1, 'name': 'John Doe', 'subject': 'Mathematics', 'cost': '$30/hour', 'username': 'johndoe', 'password': 'math123'},
    {'id': 2, 'name': 'Jane Smith', 'subject': 'English', 'cost': '$25/hour', 'username': 'janesmith', 'password': 'english123'},
    {'id': 3, 'name': 'Emma Brown', 'subject': 'Physics', 'cost': '$40/hour', 'username': 'emmabrown', 'password': 'physics123'}
]

students = [
    {'id': 101, 'name': 'Student One', 'username': 'student1', 'password': 'studentpass'},
    {'id': 102, 'name': 'Student Two', 'username': 'student2', 'password': 'studentpass'}
]

_users_in_room = {}  # Stores users in each room
_room_of_sid = {}    # Maps socket IDs to rooms
_name_of_sid = {}    # Maps socket IDs to user display names

# Route to login page
@app.route('/login', methods=['GET', 'POST'])
@app.route("/", methods=["GET", "POST"])
def login():
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

    return render_template('login.html')

# Tutor dashboard
@app.route('/tutor/dashboard/<int:tutor_id>')
def tutor_dashboard(tutor_id):
    tutor = next((tutor for tutor in tutors if tutor['id'] == tutor_id), None)
    return render_template('tutor_dashboard.html', tutor=tutor, tutor_id=tutor_id) if tutor else "Tutor not found", 404

# Student dashboard
@app.route('/student/dashboard/<int:student_id>')
def student_dashboard(student_id):
    student = next((student for student in students if student['id'] == student_id), None)
    return render_template('student_dashboard.html', student=student, student_id=student_id) if student else "Student not found", 404

# Route to add a new gig (course)
@app.route('/addgig/<int:tutor_id>', methods=['GET', 'POST'])
def add_gig(tutor_id):
    if request.method == 'POST':
        new_course = {
            'id': len(tutors) + 1,
            'name': request.form['name'],
            'subject': request.form['subject'],
            'cost': request.form['cost']
        }
        tutors.append(new_course)
        return redirect(url_for('explore', user_id=tutor_id))

    tutor = next((tutor for tutor in tutors if tutor['id'] == tutor_id), None)
    return render_template('addgig.html', tutor=tutor, tutor_id=tutor_id) if tutor else "Tutor not found", 404

@app.route("/explore/<int:user_id>", methods=["GET", "POST"])
def explore(user_id):
    return render_template('explore.html', tutors=tutors, user_id=user_id, name=session['username'])

# Route to show the subscribed classes
@app.route('/subscribed')
def subscribed():
    if 'subscribed_classes' not in session:
        session['subscribed_classes'] = []

    subscribed_tutors = [tutor for tutor in tutors if tutor['id'] in session['subscribed_classes']]
    return render_template('subscribed.html', tutors=subscribed_tutors)

# Dynamic route to show tutor profile based on ID
@app.route('/tutor/<int:tutor_id>')
def tutor_profile(tutor_id):
    tutor = next((tutor for tutor in tutors if tutor['id'] == tutor_id), None)
    return render_template('tutorprofile.html', tutor=tutor) if tutor else "Tutor not found", 404

# Route to edit tutor profile
@app.route('/tutor/edit/<int:tutor_id>', methods=['GET', 'POST'])
def edit_tutor(tutor_id):
    tutor = next((tutor for tutor in tutors if tutor['id'] == tutor_id), None)
    if not tutor:
        return "Tutor not found", 404

    if request.method == 'POST':
        tutor['name'] = request.form['name']
        tutor['subject'] = request.form['subject']
        tutor['cost'] = request.form['cost']
        return redirect(url_for('tutor_profile', tutor_id=tutor_id))

    return render_template('edit_tutor.html', tutor=tutor)

@app.route("/profile", methods=["GET", "POST"])
def profile():
    return render_template("profile.html")

@app.route("/videocall", methods=["GET", "POST"])
def index():
    if session.get('role'):
        if request.method == "POST":
            room_id = request.form['room_id']
            return redirect(url_for("entry_checkpoint", room_id=room_id))
        return render_template("home.html")
    return render_template("home.html")

@app.route("/room/<string:room_id>/")
def enter_room(room_id):
    if room_id not in session:
        return redirect(url_for("entry_checkpoint", room_id=room_id))
    return render_template("chatroom.html", room_id=room_id, display_name=session[room_id]["name"], mute_audio=session[room_id]["mute_audio"], mute_video=session[room_id]["mute_video"])

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

# Route to logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    socketio.run(app, debug=True)
