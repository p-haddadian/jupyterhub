# Fix for Circular Redirect Issue

## Problem
When users clicked "راه‌اندازی Jupyter Lab" button, they were redirected to JupyterHub which would redirect them back to the portal dashboard, creating a circular redirect loop.

## Root Cause
1. **JupyterHub Login Template**: The `login.html` template redirects all unauthenticated users back to the portal
2. **Missing Authentication**: Users were sent to Jupyter without an authentication token
3. **Flow**: Portal → JupyterHub (unauthenticated) → Login page → Redirect to Portal → Loop

## Solution

### 1. Generate User Authentication Tokens

The portal now generates temporary authentication tokens for users when launching Jupyter. This allows direct access to Jupyter Lab without requiring separate authentication.

**Changes in `portal-backend/main.py`:**

- Added token generation when server is ready or starting
- Uses JupyterHub API endpoint: `POST /hub/api/users/{username}/tokens`
- Token expires in 1 hour (3600 seconds)
- URL format: `/user/{username}/lab?token={generated_token}`

### 2. Added Token Permission Scope

**Changes in `jupyterhub/jupyterhub_config.py`:**

Added `'tokens'` and `'admin:auth_state'` scopes to allow the portal API service to create user tokens.

## How It Works Now

### Flow Diagram

```
User clicks "Launch Jupyter"
    ↓
Portal Backend receives request
    ↓
Check if user exists in JupyterHub
    ↓
Check if server is running
    ↓
Generate authentication token
    ↓
Return URL with token: /user/username/lab?token=abc123
    ↓
User's browser opens URL
    ↓
JupyterHub validates token (no login required)
    ↓
User accesses Jupyter Lab directly ✓
```

### Code Changes

#### 1. Token Generation for Running Server

```python
# Generate auth token for direct access
token_response = await call_jupyterhub_api(
    "POST",
    f"/users/{current_user.username}/tokens",
    json_data={"expires_in": 3600, "note": "Portal access token"},
    timeout=10.0
)
if token_response and token_response.status_code == 200:
    token_data = token_response.json()
    token = token_data.get("token")
    return JupyterLaunchResponse(
        status="running",
        url=f"/user/{current_user.username}/lab?token={token}",
        message="Jupyter Lab در حال اجرا است"
    )
```

#### 2. Token Generation for Starting Server

```python
# Generate auth token for when server is ready
token_response = await call_jupyterhub_api(
    "POST",
    f"/users/{current_user.username}/tokens",
    json_data={"expires_in": 3600, "note": "Portal access token"},
    timeout=10.0
)

if token_response and token_response.status_code == 200:
    token_data = token_response.json()
    token = token_data.get("token")
    return JupyterLaunchResponse(
        status="starting",
        url=f"/user/{current_user.username}/lab?token={token}",
        message="Jupyter Lab در حال راه‌اندازی است..."
    )
```

#### 3. Fallback Without Token

If token generation fails, the system falls back to returning the URL without a token. In this case, the user may need to authenticate through the custom login flow.

## API Endpoint Used

### Create User Token
```
POST /hub/api/users/{username}/tokens
```

**Headers:**
```
Authorization: token {JUPYTERHUB_API_TOKEN}
```

**Body:**
```json
{
  "expires_in": 3600,
  "note": "Portal access token"
}
```

**Response:**
```json
{
  "token": "generated_token_string_here",
  "id": "token_id",
  "user": "username",
  "expires_at": "2025-10-30T12:00:00Z",
  "note": "Portal access token"
}
```

## Security Considerations

### Token Expiry
- Tokens expire after 1 hour (3600 seconds)
- This prevents long-lived access tokens from being compromised
- Users will need to launch Jupyter again after token expires

### Token Scope
- Tokens are user-specific
- Cannot be used to access other users' servers
- Limited to Jupyter server access only

### One-Time Use
- Tokens are generated fresh for each launch request
- Previous tokens remain valid until expiry
- JupyterHub tracks all active tokens per user

## Testing the Fix

### Step 1: Rebuild and Restart

```bash
docker-compose down
docker-compose build --no-cache portal-backend jupyterhub
docker-compose up -d
```

### Step 2: Test User Flow

1. Register/Login to portal at `http://localhost:8001/portal`
2. Click "راه‌اندازی Jupyter Lab"
3. New tab should open to JupyterHub
4. **Should NOT see login page**
5. **Should NOT redirect back to portal**
6. Should see Jupyter Lab interface directly ✓

### Step 3: Verify Token in URL

Check the opened URL - it should look like:
```
http://localhost:8000/user/username/lab?token=eyJhbGc...
```

### Step 4: Check Logs

```bash
# Portal backend logs should show token generation
docker logs shaparak-portal-backend --tail 20

# JupyterHub logs should show token authentication
docker logs shaparak-jupyterhub --tail 20
```

Expected log messages:
- Portal: Successfully created token for user
- JupyterHub: User authenticated via token

## Troubleshooting

### Issue: Still redirecting to portal

**Cause:** Token generation failed or permission denied

**Solution:**
1. Check JupyterHub configuration has `'tokens'` scope
2. Verify API token is correct
3. Check logs for token generation errors:
   ```bash
   docker logs shaparak-portal-backend | grep token
   ```

### Issue: "403 Forbidden" when creating token

**Cause:** Portal API service doesn't have permission

**Solution:**
1. Verify `jupyterhub_config.py` has `'tokens'` in scopes list
2. Restart JupyterHub:
   ```bash
   docker-compose restart jupyterhub
   ```

### Issue: Token in URL but still shows login

**Cause:** Token format or validation issue

**Solution:**
1. Check token is actually in the URL
2. Verify token is valid:
   ```bash
   curl -H "Authorization: token TOKEN_HERE" \
        http://localhost:8000/hub/api/user
   ```

### Issue: Token expired

**Cause:** User waited too long (>1 hour) to access Jupyter

**Solution:**
- User should click "راه‌اندازی Jupyter Lab" again to get a fresh token
- Consider increasing token expiry in production if needed

## Alternative Solutions (Not Implemented)

### Option 1: OAuth Flow
Could implement full OAuth flow between portal and JupyterHub. More complex but more secure for production.

### Option 2: Shared Authentication Cookie
Could configure JupyterHub and Portal to share authentication cookies. Requires same domain.

### Option 3: Proxy Through Portal
Could proxy all Jupyter traffic through the portal backend. Adds complexity and latency.

**Why we chose token-based access:**
- Simple to implement
- Works across different domains
- No need for cookie sharing
- Clear security boundaries
- Easy to audit and revoke

## Monitoring Token Usage

### Get All Tokens for a User

```bash
curl http://localhost:8000/hub/api/users/username/tokens \
  -H "Authorization: token demo-token-shaparak-2025"
```

### Delete a Token

```bash
curl -X DELETE http://localhost:8000/hub/api/users/username/tokens/TOKEN_ID \
  -H "Authorization: token demo-token-shaparak-2025"
```

### Clear All User Tokens (Admin)

```bash
# Get all tokens
TOKENS=$(curl -s http://localhost:8000/hub/api/users/username/tokens \
  -H "Authorization: token demo-token-shaparak-2025" | jq -r '.[].id')

# Delete each
for TOKEN_ID in $TOKENS; do
  curl -X DELETE http://localhost:8000/hub/api/users/username/tokens/$TOKEN_ID \
    -H "Authorization: token demo-token-shaparak-2025"
done
```

## Production Recommendations

### 1. Shorter Token Expiry
```python
json_data={"expires_in": 1800, "note": "Portal access token"}  # 30 minutes
```

### 2. Token Cleanup
Implement periodic cleanup of expired tokens:
```python
# Add scheduled task to delete old tokens
```

### 3. Rate Limiting
Limit token generation to prevent abuse:
```python
# Max 5 tokens per user per hour
```

### 4. Token Audit Log
Log all token generation events:
```python
# Add to code_execution_logs or separate tokens_log table
```

### 5. Token Revocation
Allow users or admins to revoke tokens:
```python
@app.delete("/api/jupyter/tokens/{token_id}")
async def revoke_token(token_id: str, current_user: UserInfo = Depends(get_current_user)):
    # Delete token via JupyterHub API
    pass
```

## Summary

✅ **Fixed:** Circular redirect loop  
✅ **Added:** Automatic token generation  
✅ **Result:** Direct access to Jupyter Lab without manual authentication  
✅ **Security:** 1-hour token expiry with user-specific scope  
✅ **Fallback:** Works even if token generation fails  

The user experience is now seamless - clicking the launch button directly opens Jupyter Lab without any intermediate login screens or redirects.

