from flask_login import UserMixin


# User Class for flask-session
class User(UserMixin):
    def __init__(self, id, username, access):
        self.id = id
        self.username = username
        self.access = access
