import logging
from flask import request

def get_logger(name):
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger

class AuditLogger:
    @staticmethod
    def log(action_type, entity_type, entity_id=None, details=None):
        logger = get_logger("audit")
        logger.info(f"AUDIT - {action_type} on {entity_type} {entity_id}: {details}")

    @staticmethod
    def log_auth_attempt(email, success, reason, ip):
        logger = get_logger("audit")
        logger.info(f"AUTH - {email} - Success: {success} - {reason} - IP: {ip}")

    @staticmethod
    def log_data_change(user_id, entity_type, entity_id, action, old_value, new_value):
        logger = get_logger("audit")
        logger.info(f"DATA - {user_id} - {action} on {entity_type} {entity_id}")

def setup_logging(app):
    app.logger.setLevel(logging.INFO)

def log_request_response(app):
    @app.before_request
    def log_request():
        app.logger.info(f"Request: {request.method} {request.url}")
        
    @app.after_request
    def log_response(response):
        app.logger.info(f"Response: {response.status}")
        return response
