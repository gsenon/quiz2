import os

class Config:
    APP_SECRET_DEFAULT = "super-secret-key"

    @staticmethod
    def is_super_user(username):
        return username in os.environ.get("SUPER_ADMINS", "").split(",")
