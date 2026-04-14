import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SECRET_KEY = os.environ.get('SECRET_KEY', 'elder-care-dev-key-change-in-prod')
DATABASE = os.environ.get('DATABASE', os.path.join(BASE_DIR, 'elder_care.db'))

# Set SILICONFLOW_API_KEY in your environment before using the AI Agent.
SILICONFLOW_API_KEY = os.environ.get('SILICONFLOW_API_KEY', 'sk-wsvpjdsmrszihwngzxnfbqjldturhtwqsgcabcmgolijvhic')
SILICONFLOW_BASE_URL = os.environ.get('SILICONFLOW_BASE_URL', 'https://api.siliconflow.cn/v1')
SILICONFLOW_MODEL = os.environ.get('SILICONFLOW_MODEL', 'Pro/zai-org/GLM-5.1')
SILICONFLOW_TIMEOUT = int(os.environ.get('SILICONFLOW_TIMEOUT', '120'))
AGENT_ROW_LIMIT = int(os.environ.get('AGENT_ROW_LIMIT', '200'))
