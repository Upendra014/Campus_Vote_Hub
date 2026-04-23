import re

class ValidationError(Exception):
    pass

def validate_email_format(email):
    pass

def validate_password_strength(password):
    pass

def validate_name(name):
    pass

def validate_user_registration(data):
    # Dummy implementation for now so the app runs smoothly
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')
    role = data.get('role', 'student')

    if not name or not email or not password:
        return False, ["Missing fields"], None

    return True, [], {'name': name, 'email': email, 'password': password, 'role': role}
