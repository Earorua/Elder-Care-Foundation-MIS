import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SECRET_KEY = os.environ.get('SECRET_KEY', 'elder-care-dev-key-change-in-prod')
DATABASE = os.environ.get('DATABASE', os.path.join(BASE_DIR, 'elder_care.db'))

# Set OPENROUTER_API_KEY in your environment or paste it here before using the AI Agent.
OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY', '')
OPENROUTER_BASE_URL = os.environ.get('OPENROUTER_BASE_URL', 'https://openrouter.ai/api/v1')
OPENROUTER_MODEL = os.environ.get('OPENROUTER_MODEL', 'anthropic/claude-sonnet-4.6')
OPENROUTER_TIMEOUT = int(os.environ.get('OPENROUTER_TIMEOUT', '120'))
OPENROUTER_MAX_RETRIES = int(os.environ.get('OPENROUTER_MAX_RETRIES', '2'))
OPENROUTER_DISABLE_ENV_PROXY = os.environ.get('OPENROUTER_DISABLE_ENV_PROXY', '1').lower() not in ('0', 'false', 'no')

# Backward-compatible aliases for any local code that still reads the previous names.
SILICONFLOW_API_KEY = OPENROUTER_API_KEY
SILICONFLOW_BASE_URL = OPENROUTER_BASE_URL
SILICONFLOW_MODEL = OPENROUTER_MODEL
SILICONFLOW_TIMEOUT = OPENROUTER_TIMEOUT
SILICONFLOW_MAX_RETRIES = OPENROUTER_MAX_RETRIES
SILICONFLOW_DISABLE_ENV_PROXY = OPENROUTER_DISABLE_ENV_PROXY
AGENT_ROW_LIMIT = int(os.environ.get('AGENT_ROW_LIMIT', '200'))
