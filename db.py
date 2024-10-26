from pymongo import MongoClient # type: ignore
from werkzeug.security import generate_password_hash # type: ignore
from user import User
from tutor import Tutors
from bson import ObjectId
from datetime import datetime

client = MongoClient("mongodb+srv://snallapati:nsrk12@chat-feature.uw09x.mongodb.net/?retryWrites=true&w=majority&appName=Chat-Feature")

chat_db = client.get_database("ChatDB")
users_collection = chat_db.get_collection("user")
rooms_collection = chat_db.get_collection("rooms")
tutors_collection = chat_db.get_collection("tutors")
room_members_collection = chat_db.get_collection("room_members")
messages_collection = chat_db.get_collection("messages")
subscriptions_collection = chat_db.get_collection("subscriptions")

def save_user(username, email, password, role):
    password_hash = generate_password_hash(password)
    users_collection.insert_one({'username': username, 'email': email, 'password': password_hash, 'role':role})
    if role=="tutor":
        tutors_collection.insert_one({'username': username, 'email': email})

def get_user(username):
    user_data = users_collection.find_one({'username': username})
    print(user_data)
    return User(user_data['_id'], user_data['username'], user_data['email'], user_data['password'], user_data['role']) if user_data else None

def get_tutor_id(tutor_id):
    # Convert the string ID to ObjectId
    try:
        tutor = tutors_collection.find_one({'_id': ObjectId(tutor_id)})
        
        if tutor:
            # Extract the subjects list from the tutor document
            subjects = tutor.get('subjects', [])
            tutor_profiles = []
            
            if not subjects:  # No subjects at all
                tutor_profiles.append({
                    'username': tutor['username'],
                    'subject': tutor['subject'],  # Handle case with no subjects
                    'cost': tutor['cost'],                    # Handle case with no subjects
                    'id': str(tutor['_id']),      # Include the tutor's unique ID for profile linking
                    'email': str(tutor['email'])
                })
            else:  # There are subjects
                for subject_entry in subjects:
                    tutor_profiles.append({
                        'username': tutor['username'],
                        'subject': subject_entry['subject'],  # Subject name from the subject object
                        'cost': subject_entry['cost'],        # Cost from the subject object
                        'id': str(tutor['_id']),               # Include the tutor's unique ID for profile linking
                        'email': str(tutor['email'])
                    })

            print("HANUMAN!!!!!!!")
            print(tutor_profiles) 
            return tutor_profiles
        else:
            print(f"No tutor found with ID: {tutor_id}")
            return None

    except Exception as e:
        print(f"An error occurred: {e}")
        return None
   
def get_tutor(username):
    tutor_data = tutors_collection.find_one({'username': username})
    print("db.py tutors data")
    print(tutor_data)
    return Tutors(
        tutor_data['_id'],
        tutor_data['username'],
        tutor_data['email'],
        tutor_data.get('subject', ''),  # Default to an empty string if 'subject' is missing
        tutor_data.get('cost', 0)       # Default to 0 if 'cost' is missing
    ) if tutor_data else None
    #return Tutors(tutor_data['_id'], tutor_data['username'], tutor_data['email'], tutor_data['subject'], tutor_data['cost']) if tutor_data else None

def subscribe(username, email, tutor_name, tuition_subject, tutor_email):
    # Check if the student is already subscribed to this tutor and subject
    existing_subscription = subscriptions_collection.find_one({
        'username': username,
        'tutor_name': tutor_name,
        'tuition_subject': tuition_subject
    })
    
    # If no existing subscription, add a new one
    if not existing_subscription:
        subscriptions_collection.insert_one({
            'username': username,
            'email': email,
            'tutor_name': tutor_name,
            'tuition_subject': tuition_subject,
            'tutor_email': tutor_email
        })
        room_name= f"{tutor_name}_{tuition_subject}"
        room_id=get_room_id(room_name)
        add_room_member(room_id, room_name, username, "Admin")
                
    else:
        print("Student is already subscribed to this tutor and subject.")

def get_all_subscriptions(username):
    try:
        # Retrieve all subscription records from the collection
        subscriptions = list(subscriptions_collection.find({'username': username}))
        if not subscriptions:
            print("No subscriptions found in the database.")
        else:
            print("Subscriptions found:", subscriptions)

        # Format data to be sent to template
        subscription_list = [
            {
                'username': sub.get('username', 'N/A'),
                'email': sub.get('email', 'N/A'),
                'tutor_name': sub.get('tutor_name', 'N/A'),
                'tuition_subject': sub.get('tuition_subject', 'N/A'),
                'tutor_email': sub.get('tutor_email', 'N/A')
            }
            for sub in subscriptions
        ]
        return subscription_list

    except Exception as e:
        print("Error fetching subscriptions:", str(e))
        return []

def get_all_students(username):
    try:
        # Retrieve all subscription records from the collection
        subscriptions = list(subscriptions_collection.find({'tutor_name': username}))
        if not subscriptions:
            print("No subscriptions found in the database.")
        else:
            print("Subscriptions found:", subscriptions)

        # Format data to be sent to template
        subscription_list = [
            {
                'username': sub.get('username', 'N/A'),
                'email': sub.get('email', 'N/A'),
                'tutor_name': sub.get('tutor_name', 'N/A'),
                'tuition_subject': sub.get('tuition_subject', 'N/A'),
                'tutor_email': sub.get('tutor_email', 'N/A')
            }
            for sub in subscriptions
        ]
        return subscription_list

    except Exception as e:
        print("Error fetching subscriptions:", str(e))
        return []

def get_all_tutors():
    # Retrieve all tutors from the database
    tutors = tutors_collection.find()
    tutor_profiles = []
    
    for tutor in tutors:
        # Extract the subjects list from the tutor document
        subjects = tutor.get('subjects', [])
        
        if not subjects:  # No subjects at all
            tutor_profiles.append({
                'username': tutor['username'],
                'subject': tutor['subject'],
                'cost': tutor['cost'],
                'id': str(tutor['_id'])  # Include the tutor's unique ID for profile linking
            })
        else:  # There are subjects
            for subject_entry in subjects:
                tutor_profiles.append({
                    'username': tutor['username'],
                    'subject': subject_entry['subject'],  # Subject name from the subject object
                    'cost': subject_entry['cost'],        # Cost from the subject object
                    'id': str(tutor['_id'])  # Include the tutor's unique ID for profile linking
                })
    
    return tutor_profiles




def save_or_update_tutor(username, email=None, subject=None, cost=None):
    # Fetch tutor based on username
    tutor = tutors_collection.find_one({'username': username})

    if tutor:
        # Tutor exists, check if they already have the specified subject
        found_subject = False
        subjects = tutor.get('subjects', [])
        
        for subj in subjects:
            if subj['subject'] == subject:
                # Update the cost if the subject already exists
                subj['cost'] = cost
                found_subject = True
                
                break

        if not found_subject and subject and cost is not None:
            # Subject does not exist; add it to the subjects list
            subjects.append({'subject': subject, 'cost': cost})
            #ADD ROOM FOR EVERY SUBJECT
            room_name= f"{username}_{subject}"
            room_id = save_room(room_name, username)
            #add_room_member(room_id, room_name, username, username)

        # Update the subjects list in the tutor's profile
        tutors_collection.update_one(
            {'username': username},
            {'$set': {'subjects': subjects}}
        )
    else:
        # If the tutor does not exist, create a new profile
        if username and email and subject and cost is not None:
            tutor_data = {
                'username': username,
                'email': email,
                'subjects': [{'subject': subject, 'cost': cost}]
            }
            tutors_collection.insert_one(tutor_data)
        else:
            print("Insufficient data to create a new tutor profile. Provide all fields.")


def save_room(room_name, created_by):
    room_id = rooms_collection.insert_one(
        {'name': room_name, 'created_by': created_by, 'created_at': datetime.now()}).inserted_id
    add_room_member(room_id, room_name, created_by, created_by, is_room_admin=True)
    return room_id

def update_room(room_id, room_name):
    rooms_collection.update_one({'_id': ObjectId(room_id)}, {'$set': {'name': room_name}})
    room_members_collection.update_many({'_id.room_id': ObjectId(room_id)}, {'$set': {'room_name': room_name}})

def get_room(room_id):
    return rooms_collection.find_one({'_id': ObjectId(room_id)})

def get_room_id(room_name):
    room = rooms_collection.find_one({'name': room_name}, {'_id': 1})
    return room['_id'] if room else None

def add_room_member(room_id, room_name, username, added_by, is_room_admin=False):
    room_members_collection.insert_one(
        {'_id': {'room_id': ObjectId(room_id), 'username': username}, 'room_name': room_name, 'added_by': added_by,
         'added_at': datetime.now(), 'is_room_admin': is_room_admin})

def add_room_members(room_id, room_name, usernames, added_by):
    room_members_collection.insert_many(
        [{'_id': {'room_id': ObjectId(room_id), 'username': username}, 'room_name': room_name, 'added_by': added_by,
          'added_at': datetime.now(), 'is_room_admin': False} for username in usernames])

def remove_room_members(room_id, usernames):
    room_members_collection.delete_many(
        {'_id': {'$in': [{'room_id': ObjectId(room_id), 'username': username} for username in usernames]}})

def get_room_members(room_id):
    return list(room_members_collection.find({'_id.room_id': ObjectId(room_id)}))


def get_rooms_for_user(username):
    return list(room_members_collection.find({'_id.username': username}))

def is_room_member(room_id, username):
    return room_members_collection.count_documents({'_id': {'room_id': ObjectId(room_id), 'username': username}})

def is_room_admin(room_id, username):
    return room_members_collection.count_documents(
        {'_id': {'room_id': ObjectId(room_id), 'username': username}, 'is_room_admin': True})

def save_message(room_id, text, sender):
    messages_collection.insert_one({'room_id': room_id, 'text': text, 'sender': sender, 'created_at': datetime.now()})

def get_messages(room_id):
    messages = list(messages_collection.find({'room_id': room_id}))
    for message in messages:
        message[ 'created_at' ] = message[ 'created_at' ].strftime("%d %b, %H:%M")
    return messages