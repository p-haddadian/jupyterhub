# Quick Verification Guide for JupyterHub API Fixes

## Step 1: Rebuild and Restart Services

```bash
# Stop all services
docker-compose down

# Rebuild the modified services
docker-compose build --no-cache portal-backend jupyterhub

# Start all services
docker-compose up -d

# Check all services are running
docker-compose ps
```

Expected output: All services should show "Up" or "Up (healthy)"

## Step 2: Verify JupyterHub API is Accessible

```bash
# Test API connectivity
curl -H "Authorization: token demo-token-shaparak-2025" \
     http://localhost:8000/hub/api/users

# You should get a JSON response with user list (likely empty initially)
```

Expected output: `[]` or a list of users

## Step 3: Check Portal Backend Health

```bash
# Test portal backend health endpoint
curl http://localhost:8001/health
```

Expected output:
```json
{
  "status": "healthy",
  "database": "connected",
  "timestamp": "2025-10-30T..."
}
```

## Step 4: Test User Registration Flow

1. Open browser to `http://localhost:8001/portal`
2. Click "ثبت‌نام" (Register)
3. Fill in the form:
   - Username: `testuser` (lowercase, no spaces)
   - Email: `test@example.com`
   - Full Name: `Test User`
   - Organization: `Test Org` (optional)
   - Password: `testpass123` (min 8 chars)
4. Click "ثبت‌نام" (Register)

Expected result: Success message "ثبت‌نام با موفقیت انجام شد"

**Verify in logs:**
```bash
docker logs shaparak-portal-backend | grep "testuser"
```

Should show: "Successfully created JupyterHub user: testuser"

## Step 5: Test Login Flow

1. On login page, enter:
   - Username: `testuser`
   - Password: `testpass123`
2. Click "ورود" (Login)

Expected result: Dashboard loads with user information and stats

## Step 6: Test Jupyter Launch (CRITICAL - Tests Circular Redirect Fix)

1. From dashboard, click "راه‌اندازی Jupyter Lab" (Launch Jupyter Lab)
2. Wait for message "Jupyter Lab در حال راه‌اندازی است..."
3. New tab should open with JupyterHub

**Expected URL (with authentication token):** 
```
http://localhost:8000/user/testuser/lab?token=eyJhbGciOiJIUzI1NiIsInR5...
```

**IMPORTANT - Verify NO Circular Redirect:**
- ❌ Should NOT redirect back to portal
- ❌ Should NOT show JupyterHub login page
- ✅ Should directly load Jupyter Lab interface
- ✅ URL should contain `?token=` parameter

**Verify server is running:**
```bash
# Check for spawned container
docker ps | grep jupyter-testuser
```

Should show a container named something like `jupyter-testuser`

**If you see a redirect loop:**
```bash
# Check if token was generated
docker logs shaparak-portal-backend | grep "token"

# Check JupyterHub permissions
docker exec shaparak-jupyterhub cat /srv/jupyterhub/jupyterhub_config.py | grep tokens
```

## Step 7: Verify API Integration in Logs

```bash
# Check portal backend logs for successful API calls
docker logs shaparak-portal-backend --tail 50

# Check JupyterHub logs for API requests
docker logs shaparak-jupyterhub --tail 50
```

Look for:
- ✅ No "Connection refused" errors
- ✅ No "401 Unauthorized" errors
- ✅ Successful user creation messages
- ✅ Successful server start messages

## Step 8: Test With Demo User

If demo user exists (`ali.rezaei / shaparak123`):

1. Login with demo credentials
2. Launch Jupyter
3. Verify it opens correctly

## Common Issues and Quick Fixes

### Issue: Services won't start
```bash
# Check logs for errors
docker-compose logs

# Common fix: Remove volumes and restart
docker-compose down -v
docker-compose up -d
```

### Issue: API token mismatch
```bash
# Verify tokens match
docker exec shaparak-portal-backend env | grep JUPYTERHUB_API_TOKEN
docker exec shaparak-jupyterhub env | grep JUPYTERHUB_API_TOKEN

# Should both show: demo-token-shaparak-2025
```

### Issue: Network connectivity
```bash
# Test network connectivity between services
docker exec shaparak-portal-backend ping -c 3 jupyterhub
docker exec shaparak-portal-backend curl http://jupyterhub:8000/hub/api
```

### Issue: Permission denied on Docker socket
```bash
# Check Docker socket permissions (if on Linux)
ls -l /var/run/docker.sock

# May need to add user to docker group or run with sudo
```

### Issue: Port already in use
```bash
# Check what's using the ports
netstat -tulpn | grep ':8000\|:8001'

# Change ports in docker-compose.yml if needed
```

## Success Criteria Checklist

- [ ] All services start successfully
- [ ] Portal backend health check returns "healthy"
- [ ] JupyterHub API responds to token authentication
- [ ] Can register new user through portal
- [ ] User is created in JupyterHub (check logs)
- [ ] Can login with registered user
- [ ] Dashboard displays correctly with stats
- [ ] Can launch Jupyter from dashboard
- [ ] Jupyter Lab opens in new tab **with token in URL**
- [ ] **NO circular redirect to portal (CRITICAL)**
- [ ] **Jupyter Lab interface loads directly**
- [ ] Spawned container appears in `docker ps`
- [ ] No error messages in portal backend logs
- [ ] No error messages in JupyterHub logs

## Monitoring Commands

Keep these running in separate terminals for real-time monitoring:

```bash
# Terminal 1: Portal backend logs
docker logs -f shaparak-portal-backend

# Terminal 2: JupyterHub logs
docker logs -f shaparak-jupyterhub

# Terminal 3: All containers status
watch -n 2 'docker-compose ps'
```

## API Testing with curl

### Create User
```bash
curl -X POST http://localhost:8000/hub/api/users/newuser \
  -H "Authorization: token demo-token-shaparak-2025" \
  -H "Content-Type: application/json" \
  -d '{"admin": false}'
```

### Get User Info
```bash
curl http://localhost:8000/hub/api/users/newuser \
  -H "Authorization: token demo-token-shaparak-2025"
```

### Start Server
```bash
curl -X POST http://localhost:8000/hub/api/users/newuser/server \
  -H "Authorization: token demo-token-shaparak-2025"
```

### Check Server Status
```bash
curl http://localhost:8000/hub/api/users/newuser \
  -H "Authorization: token demo-token-shaparak-2025" | jq '.servers'
```

## Clean Reset (If needed)

```bash
# Complete reset of the environment
docker-compose down -v
docker system prune -a --volumes -f
docker-compose up -d --build
```

⚠️ **Warning:** This will delete all data including database!

## Next Steps After Verification

1. Change default API token in production
2. Set up proper SSL/TLS certificates
3. Configure backup strategy for jupyterhub_data volume
4. Set up log aggregation
5. Configure monitoring and alerts
6. Review and adjust resource limits (CPU/memory)

