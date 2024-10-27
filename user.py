from werkzeug.security import check_password_hash

class User:

    def __init__(self, id, username, email, password, role):
        #print("SELF DATA")
        self.id = id
        #print(self.id)
        self.username = username
        #print(self.username)
        self.email = email
        #print(self.email)
        self.password = password
        #print(self.password)
        self.role = role
        #print(self.role)
    
    @staticmethod
    def is_authenticated(self):
        return True
    
    @staticmethod
    def is_active(self):
        return True

    @staticmethod
    def is_anonymous(self):
        return False
    
    def get_id(self):
        return self.username
    
    def check_password(self, password_input):
        return check_password_hash(self.password, password_input)