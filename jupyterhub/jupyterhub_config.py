import sys
sys.path.insert(0, "/srv/jupyterhub")

import os
from custom_authenticator import ShaparakAuthenticator

# Basic config
c.JupyterHub.ip = '0.0.0.0'
c.JupyterHub.port = 8000
c.JupyterHub.hub_ip = '0.0.0.0'

# Database - Use SQLite for JupyterHub internal db
c.JupyterHub.db_url = 'sqlite:///jupyterhub.sqlite'

# Authentication
c.JupyterHub.authenticator_class = ShaparakAuthenticator
c.ShaparakAuthenticator.admin_users = {'admin'}

# Session expiration (8 hours)
c.JupyterHub.cookie_max_age_days = 0.333
c.JupyterHub.oauth_token_expires_in = 28800

# Spawner configuration
c.JupyterHub.spawner_class = 'dockerspawner.DockerSpawner'
c.DockerSpawner.image = 'shaparak-jupyter-user:latest'
c.DockerSpawner.network_name = os.environ['DOCKER_NETWORK_NAME']
c.DockerSpawner.remove = True
c.DockerSpawner.debug = True

c.DockerSpawner.extra_create_kwargs = {
    'user': 'jovyan',
}

# Set environment variables - don't include JUPYTERHUB_USER, let JupyterHub set it
c.DockerSpawner.environment = {
    'GRANT_SUDO': 'no',
    'JUPYTER_ENABLE_LAB': 'yes',
    'AUDIT_DB_CONNECTION': f"postgresql://jupyter_readonly:jupyter_read_2025@{os.environ['POSTGRES_HOST']}:5432/{os.environ['POSTGRES_DB']}",
    'DATA_DB_CONNECTION': f"postgresql://jupyter_readonly:jupyter_read_2025@{os.environ['POSTGRES_HOST']}:5432/{os.environ['POSTGRES_DB']}"
}

# Override get_env to add the actual username
c.DockerSpawner.get_env = lambda spawner: {**spawner.environment, 'JUPYTERHUB_USER': spawner.user.name}

c.DockerSpawner.mem_limit = '2G'
c.DockerSpawner.cpu_limit = 1.0

c.JupyterHub.template_paths = ['/srv/jupyterhub/templates']
c.JupyterHub.logo_file = '/srv/jupyterhub/templates/shaparak-logo.png'
c.JupyterHub.admin_access = True

# ===== IMPORTANT: API SERVICE CONFIGURATION =====
# This is the key part for portal integration

# Define the API token - must match docker-compose.yml
API_TOKEN = os.environ.get('JUPYTERHUB_API_TOKEN', 'demo-token-shaparak-2025')

# Create service with full permissions
c.JupyterHub.services = [
    {
        'name': 'portal-api',
        'api_token': API_TOKEN,
    }
]

# Grant full access to the service
c.JupyterHub.load_roles = [
    {
        'name': 'portal-service',
        'scopes': [
            'admin:users',          # Full user management
            'admin:servers',        # Full server management
            'list:users',
            'read:users',
            'read:servers',
            'read:users:activity',
            'servers',
            'users',
            'access:servers',
            'tokens',               # Token management
            'admin:auth_state',     # Authentication state
        ],
        'services': ['portal-api']
    }
]

# Allow named servers (optional, but good for flexibility)
c.JupyterHub.allow_named_servers = False

# API access
c.JupyterHub.authenticate_prometheus = False