import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SECRET_KEY = os.environ.get('SECRET_KEY', 'elder-care-dev-key-change-in-prod')
DATABASE = os.environ.get('DATABASE', os.path.join(BASE_DIR, 'elder_care.db'))
