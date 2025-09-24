# config.py - application configuration
import os

class Config:
    # default super users (lowercase)
    SUPER_USERS = [u.lower() for u in os.environ.get('SUPER_USERS', 'k.skachilov').split(',')]

    APP_SECRET_DEFAULT = os.environ.get('APP_SECRET', 'please_set_a_real_secret_in_env')

    @staticmethod
    def is_super_user(username: str) -> bool:
        if not username:
            return False
        return username.lower() in Config.SUPER_USERS
