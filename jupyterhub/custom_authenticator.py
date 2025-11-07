from jupyterhub.auth import Authenticator
from traitlets import Unicode
import bcrypt
import sqlalchemy
from sqlalchemy import create_engine, text
import os
import urllib.parse

class ShaparakAuthenticator(Authenticator):
    """Custom authenticator that validates against PostgreSQL portal_users table"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        db_url = f"postgresql://{os.environ['POSTGRES_USER']}:{os.environ['POSTGRES_PASSWORD']}@{os.environ['POSTGRES_HOST']}:5432/{os.environ['POSTGRES_DB']}"
        self.engine = create_engine(db_url)
    
    async def authenticate(self, handler, data):
        username = data.get('username', '')
        password = data.get('password', '')
        
        # Check if this is an OAuth flow from portal (auto-authenticate existing users)
        # When username is "auto", it means this is from the auto-submit form
        if username == 'auto' and password == 'auto':
            self.log.info("AUTO-AUTH: Detected auto/auto credentials")
            # Try to extract username from the 'next' URL parameter
            next_url = handler.get_argument('next', '')
            self.log.info(f"AUTO-AUTH: next_url = {next_url}")
            if next_url and 'oauth2/authorize' in next_url:
                self.log.info("AUTO-AUTH: OAuth flow detected")
                # Extract username from client_id (format: jupyterhub-user-{username})
                try:
                    parsed = urllib.parse.parse_qs(urllib.parse.urlparse(next_url).query)
                    client_id = parsed.get('client_id', [''])[0]
                    self.log.info(f"AUTO-AUTH: client_id = {client_id}")
                    if client_id.startswith('jupyterhub-user-'):
                        extracted_username = client_id.replace('jupyterhub-user-', '', 1)
                        self.log.info(f"AUTO-AUTH: Extracted username = {extracted_username}")
                        
                        # Verify this user exists and is active in our database
                        with self.engine.connect() as conn:
                            result = conn.execute(
                                text("SELECT username, is_active FROM portal_users WHERE username = :username"),
                                {"username": extracted_username}
                            )
                            user = result.fetchone()
                        
                        if user and user[1]:  # user exists and is active
                            self.log.info(f"AUTO-AUTH: SUCCESS - Auto-authenticating user {extracted_username}")
                            return extracted_username
                        else:
                            self.log.warning(f"AUTO-AUTH: FAILED - User {extracted_username} not found or inactive")
                    else:
                        self.log.warning(f"AUTO-AUTH: client_id doesn't start with jupyterhub-user-")
                except Exception as e:
                    self.log.error(f"AUTO-AUTH: Exception - {e}")
                    import traceback
                    self.log.error(traceback.format_exc())
            else:
                self.log.warning("AUTO-AUTH: No OAuth flow detected in next_url")
            
            self.log.info("AUTO-AUTH: Returning None (authentication failed)")
            return None
        
        if not username or not password:
            return None
        
        # Normal authentication with username/password
        # Query portal_users table
        with self.engine.connect() as conn:
            result = conn.execute(
                text("SELECT username, hashed_password, is_active FROM portal_users WHERE username = :username"),
                {"username": username}
            )
            user = result.fetchone()
        
        if user is None:
            self.log.warning(f"User {username} not found in database")
            return None
        
        if not user[2]:  # is_active
            self.log.warning(f"User {username} is not active")
            return None
        
        # Verify password
        if bcrypt.checkpw(password.encode('utf-8'), user[1].encode('utf-8')):
            self.log.info(f"User {username} authenticated successfully")
            
            # Update last_login
            with self.engine.connect() as conn:
                conn.execute(
                    text("UPDATE portal_users SET last_login = CURRENT_TIMESTAMP WHERE username = :username"),
                    {"username": username}
                )
                conn.commit()
            
            return username
        
        self.log.warning(f"Invalid password for user {username}")
        return None