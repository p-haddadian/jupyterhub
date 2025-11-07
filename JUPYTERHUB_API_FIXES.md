# JupyterHub API Integration Fixes

## Summary
Fixed the JupyterHub API integration to enable proper communication between the portal backend and JupyterHub service. The integration now includes robust error handling, retry logic, and proper user/server management.

## Changes Made

### 1. JupyterHub Configuration (`jupyterhub/jupyterhub_config.py`)

**Fixed API Service Configuration:**
- Removed `admin: True` from service configuration (not needed with proper role scopes)
- Added comprehensive role scopes for the portal service:
  - `admin:users` - Full user management
  - `admin:servers` - Full server management
  - `list:users`, `read:users`, `read:servers` - Read operations
  - `read:users:activity` - Activity monitoring
  - `servers`, `users`, `access:servers` - Server and user access
- Added `c.JupyterHub.allow_named_servers = False` for simpler server management
- Added `c.JupyterHub.authenticate_prometheus = False` for API access

### 2. Portal Backend (`portal-backend/main.py`)

**Added Retry Helper Function:**
- Created `call_jupyterhub_api()` function with:
  - Automatic retry logic (3 attempts by default)
  - Exponential backoff (2^attempt seconds)
  - Support for GET, POST, PUT, DELETE methods
  - Configurable timeout
  - Better error logging

**Fixed User Registration:**
- Changed from `/users` to `/users/{username}` endpoint
- Added proper status code handling (200, 201, 409 for existing users)
- Improved error messages
- Uses new retry helper function

**Fixed Dashboard Endpoint:**
- Improved JupyterHub status checking
- Auto-creates users if they don't exist in JupyterHub
- Better error handling with meaningful status messages
- Returns detailed server information including `server_active` flag

**Fixed Jupyter Launch Endpoint:**
- Comprehensive server state checking (ready, pending, not started)
- Ensures user exists before attempting to start server
- Proper handling of already-running servers
- Better error messages in Persian for user feedback
- Handles edge cases like server already starting (400 status)

**Added Type Hints:**
- Imported `Optional`, `Dict`, `Any` from typing
- Imported `asyncio` for sleep functionality

### 3. Docker Compose Configuration (`docker-compose.yml`)

**Enhanced Service Dependencies:**
- Portal backend now waits for:
  - `postgres` (healthy condition)
  - `jupyterhub` (started condition)
  - `redis` (started condition)
- Added `restart: unless-stopped` policies to both services

**Added Health Checks:**
- Portal backend: checks `/health` endpoint every 30s
- JupyterHub: checks `/hub/api` endpoint every 30s
- Both have 60s start periods to allow proper initialization

**Added Volume for JupyterHub:**
- `jupyterhub_data:/srv/jupyterhub` for persistent JupyterHub data

## API Endpoints Fixed

### 1. User Creation: `POST /hub/api/users/{username}`
- Properly creates users with admin flag
- Handles 409 conflict (user already exists)

### 2. User Status: `GET /hub/api/users/{username}`
- Retrieves user information including active servers
- Returns 404 if user doesn't exist

### 3. Server Launch: `POST /hub/api/users/{username}/server`
- Starts user's Jupyter server
- Returns 201/202 for successful start
- Returns 400 if server is already starting

## Error Handling Improvements

1. **Connection Failures**: Retry up to 3 times with exponential backoff
2. **Timeout Errors**: Configurable timeouts (5-30 seconds)
3. **User Not Found**: Auto-create user before launching server
4. **Server States**: Properly detect running, starting, and stopped states
5. **HTTP Status Codes**: Handle all relevant status codes (200, 201, 202, 400, 404, 409, 500, 503)

## Testing Recommendations

1. **User Registration Flow:**
   ```bash
   # Register new user through portal
   # Check JupyterHub logs for user creation
   docker logs shaparak-jupyterhub | grep "user"
   ```

2. **Jupyter Launch Flow:**
   ```bash
   # Launch Jupyter through portal
   # Verify server starts successfully
   docker ps | grep jupyter
   ```

3. **API Connectivity:**
   ```bash
   # Test JupyterHub API directly
   curl -H "Authorization: token demo-token-shaparak-2025" \
        http://localhost:8000/hub/api/users
   ```

4. **Health Checks:**
   ```bash
   # Verify services are healthy
   docker-compose ps
   ```

## Configuration Verification

Ensure these environment variables match across services:

**In `docker-compose.yml`:**
- `portal-backend.JUPYTERHUB_API_TOKEN` = `jupyterhub.JUPYTERHUB_API_TOKEN`
- `portal-backend.JUPYTERHUB_API_URL` = `http://jupyterhub:8000/hub/api`

**In `jupyterhub_config.py`:**
- `API_TOKEN` matches the environment variable

## Troubleshooting

### Issue: "خطا در اتصال به JupyterHub"
**Solution:** Check if JupyterHub service is running and accessible
```bash
docker logs shaparak-jupyterhub
curl http://localhost:8000/hub/api
```

### Issue: "خطا در ایجاد کاربر JupyterHub"
**Solution:** Verify API token is configured correctly
```bash
# Check token in JupyterHub config
docker exec shaparak-jupyterhub cat /srv/jupyterhub/jupyterhub_config.py | grep API_TOKEN
```

### Issue: Server won't start
**Solution:** Check Docker socket permissions and spawner logs
```bash
# Check JupyterHub logs
docker logs shaparak-jupyterhub --tail 100

# Check for user containers
docker ps -a | grep jupyter
```

### Issue: 403 Forbidden on API calls
**Solution:** Verify service roles and scopes in jupyterhub_config.py
```bash
# Restart JupyterHub after config changes
docker-compose restart jupyterhub
```

## Migration Notes

If upgrading from previous version:

1. **Rebuild containers** to apply new configurations:
   ```bash
   docker-compose down
   docker-compose build --no-cache portal-backend jupyterhub
   docker-compose up -d
   ```

2. **Verify API token** is set in both services

3. **Test with existing user** to ensure backward compatibility

4. **Monitor logs** during first launches:
   ```bash
   docker-compose logs -f portal-backend jupyterhub
   ```

## Security Considerations

1. **API Token**: Change default token in production
2. **Scopes**: Current setup gives portal full admin access - restrict if needed
3. **Network**: Services communicate within Docker network only
4. **Timeouts**: Configured to prevent hanging requests
5. **Retries**: Limited to 3 to prevent DOS situations

## Performance Improvements

1. **Connection Pooling**: httpx.AsyncClient handles connection reuse
2. **Async Operations**: All API calls are non-blocking
3. **Exponential Backoff**: Reduces server load during retry attempts
4. **Health Checks**: Ensures services are ready before accepting traffic
5. **Proper Dependencies**: Services start in correct order

## Future Enhancements

1. Add circuit breaker pattern for sustained failures
2. Implement API response caching for user status
3. Add metrics collection for API call success rates
4. Create admin dashboard for monitoring JupyterHub integration
5. Add webhook support for real-time server status updates

