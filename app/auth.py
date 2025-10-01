import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class AuthSystem:
    def __init__(self, app=None):
        self.codes = {}

    def initiate_admin_login(self, username):
        code = "123456"  # For demo only
        self.codes[username] = {"code": code, "expires": datetime.utcnow() + timedelta(minutes=5)}
        logger.info(f"Generated code for {username}: {code}")
        return code

    def verify_admin_code(self, username, code):
        if username not in self.codes:
            return False
        rec = self.codes[username]
        if rec["code"] == code and rec["expires"] > datetime.utcnow():
            return True
        return False
