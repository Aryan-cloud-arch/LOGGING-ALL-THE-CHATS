import os
from dotenv import load_dotenv

load_dotenv()

class Environment:
    value = "production"

class Settings:
    def __init__(self):
        self.api_id = int(os.getenv("API_ID"))
        self.api_hash = os.getenv("API_HASH")
        self.your_bot_token = os.getenv("YOUR_BOT_TOKEN")
        self.your_bot_name = os.getenv("YOUR_BOT_NAME", "YourBot")
        self.her_bot_token = os.getenv("HER_BOT_TOKEN")
        self.her_bot_name = os.getenv("HER_BOT_NAME", "HerBot")
        self.your_phone = os.getenv("YOUR_PHONE")
        self.your_name = os.getenv("YOUR_NAME", "You")
        self.her_user_id = int(os.getenv("HER_USER_ID"))
        self.her_name = os.getenv("HER_NAME", "Her")
        self.group_id = int(os.getenv("GROUP_ID"))
        self.mongo_uri = os.getenv("MONGO_URI")
        self.mongodb_database = os.getenv("MONGODB_DATABASE", "telegram_mirror")
        self.debug = os.getenv("DEBUG", "false").lower() == "true"
        self.logging_level = os.getenv("LOGGING_LEVEL", "INFO")
        self.environment = Environment()

        self.API_ID = self.api_id
        self.API_HASH = self.api_hash
        self.YOUR_BOT_TOKEN = self.your_bot_token
        self.YOUR_BOT_NAME = self.your_bot_name
        self.HER_BOT_TOKEN = self.her_bot_token
        self.HER_BOT_NAME = self.her_bot_name
        self.YOUR_PHONE = self.your_phone
        self.YOUR_NAME = self.your_name
        self.HER_USER_ID = self.her_user_id
        self.HER_NAME = self.her_name
        self.GROUP_ID = self.group_id
        self.MONGO_URI = self.mongo_uri

        self.telegram = type('obj', (object,), {
            'api_id': self.api_id,
            'api_hash': self.api_hash,
            'your_bot_token': self.your_bot_token,
            'your_bot_name': self.your_bot_name,
            'her_bot_token': self.her_bot_token,
            'her_bot_name': self.her_bot_name,
            'your_phone': self.your_phone,
            'your_name': self.your_name,
            'her_user_id': self.her_user_id,
            'her_name': self.her_name,
            'group_id': self.group_id
        })()

        self.mongodb = type('obj', (object,), {
            'connection_uri': self.mongo_uri,
            'database': self.mongodb_database
        })()

        self.logging = type('obj', (object,), {
            'level': self.logging_level,
            'log_dir': 'logs',
            'log_file': 'bot.log',
            'use_colors': True,
            'use_json': False
        })()

        self.monitoring = type('obj', (object,), {
            'enable_stats': True,
            'memory_threshold_mb': 400
        })()

    def validate_all(self):
        return True

def load_settings(env=None):
    return Settings()

def init_config():
    return Settings()

def get_config():
    return Settings()

def get_settings():
    return Settings()
