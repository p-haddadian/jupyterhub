# Session Expiration Behavior

## 🔐 How Authentication Works

There are **TWO separate authentication systems**:

### 1. Portal JWT Token (8 hours)
- **What**: Bearer token for portal API access
- **Lifetime**: 8 hours
- **Used for**: Portal dashboard, API endpoints
- **When it expires**: User cannot access portal or API, must re-login

### 2. JupyterHub OAuth Token
- **What**: JupyterHub session cookie
- **Lifetime**: Also 8 hours (configured in `jupyterhub_config.py`)
- **Used for**: Jupyter Lab access
- **When it expires**: User is redirected to JupyterHub login

## ⏰ What Happens When Tokens Expire?

### Scenario 1: Portal JWT Expires (User in Jupyter)
**Current Behavior:**
- User is working in Jupyter Lab
- Portal JWT expires after 8 hours
- **Jupyter Lab continues to work!** ✅
- User can keep coding without interruption
- But: Cannot access portal dashboard until re-login

**Why**: Jupyter Lab uses its own JupyterHub OAuth token, separate from portal JWT.

### Scenario 2: JupyterHub OAuth Expires (User in Jupyter)
**Current Behavior:**
```python
c.JupyterHub.cookie_max_age_days = 0.333  # ~8 hours
c.JupyterHub.oauth_token_expires_in = 28800  # 8 hours in seconds
```

When JupyterHub token expires:
1. Jupyter Lab refreshes a page request
2. JupyterHub sees expired token
3. User is redirected to `/hub/login`
4. Our custom `login.html` redirects to portal
5. User must login again
6. Can re-launch Jupyter

**Important**: Unsaved work in notebooks is **LOST** if kernel is shut down!

### Scenario 3: Both Expire Simultaneously
Since both are 8 hours, they typically expire around the same time:
1. User tries to interact with Jupyter
2. Redirected to portal login
3. Must login again
4. Re-launch Jupyter
5. Previous kernel/state is gone

## 🚨 Current Issues

### Issue 1: No Warning Before Expiration
Users don't know when their session will expire.

**Solution**: Add countdown timer in both portal and Jupyter

### Issue 2: Unsaved Work Can Be Lost
If kernel is shut down, unsaved notebooks are lost.

**Solution**: Auto-save notebooks before expiration

### Issue 3: Inconsistent Session Times
Portal session and Jupyter session might not align perfectly.

**Solution**: Synchronize expiration times

## ✅ Recommended Improvements

### 1. Session Warning System

Add to portal dashboard (already has countdown):
```javascript
// In portal-frontend
useEffect(() => {
  const checkExpiration = () => {
    const remaining = sessionData.session_remaining_seconds;
    if (remaining < 300) { // 5 minutes
      showWarning("جلسه شما در 5 دقیقه آینده منقضی می‌شود");
    }
    if (remaining < 60) { // 1 minute
      showCriticalWarning("جلسه شما در 1 دقیقه آینده منقضی می‌شود!");
    }
  };
  setInterval(checkExpiration, 30000); // Check every 30s
}, [sessionData]);
```

### 2. Jupyter Extension for Session Monitoring

Add to `jupyter-user-image/ipython_config.py`:
```python
c.InteractiveShellApp.exec_lines = [
    # ... existing lines ...
    'import os',
    'from datetime import datetime, timedelta',
    'session_start = datetime.now()',
    'session_end = session_start + timedelta(hours=8)',
    'print(f"⏰ جلسه شما در {session_end.strftime(\"%H:%M\")} منقضی می‌شود")',
]
```

### 3. Auto-Save Before Expiration

Add to `jupyterhub_config.py`:
```python
# Shutdown user servers after inactivity
c.JupyterHub.shutdown_on_logout = False  # Keep server running
c.ServerApp.shutdown_no_activity_timeout = 28800  # 8 hours

# Warning before shutdown
c.ServerApp.terminals_enabled = True
```

### 4. Session Extension Option

Allow users to extend their session:

**Backend** (`portal-backend/main.py`):
```python
@app.post("/api/extend-session", tags=["Session"])
async def extend_session(current_user: UserInfo = Depends(get_current_user)):
    """
    تمدید جلسه فعلی
    
    اضافه کردن 2 ساعت به جلسه فعلی
    """
    # Create new token with extended expiration
    new_token = create_access_token(
        data={"sub": current_user.username},
        expires_delta=timedelta(hours=2)
    )
    
    return {
        "access_token": new_token,
        "token_type": "bearer",
        "message": "جلسه شما 2 ساعت تمدید شد"
    }
```

**Frontend**: Show button when < 30 minutes remaining

### 5. Graceful Shutdown

When session expires, save state:

```python
# In jupyterhub_config.py
c.JupyterHub.shutdown_on_logout = False
c.DockerSpawner.remove = False  # Don't remove containers immediately

# Add custom shutdown handler
def shutdown_handler(spawner):
    # Save notebook state
    # Notify user
    # Log shutdown
    pass

c.Spawner.pre_spawn_hook = shutdown_handler
```

## 📊 Current Configuration

### JupyterHub (`jupyterhub/jupyterhub_config.py`)
```python
# Session expiration (8 hours)
c.JupyterHub.cookie_max_age_days = 0.333  # ~8 hours
c.JupyterHub.oauth_token_expires_in = 28800  # 8 hours in seconds
```

### Portal (`portal-backend/main.py`)
```python
# Create access token
access_token = create_access_token(
    data={"sub": form_data.username},
    expires_delta=timedelta(hours=8)
)
```

Both are 8 hours - synchronized ✅

## 🎯 Recommended Changes

### Change 1: Increase Session Time for Active Users

```python
# jupyterhub_config.py
c.JupyterHub.cookie_max_age_days = 1  # 24 hours
c.JupyterHub.oauth_token_expires_in = 86400  # 24 hours

# But shutdown inactive servers after 2 hours
c.ServerApp.shutdown_no_activity_timeout = 7200  # 2 hours
```

**Why**: Users can work all day without re-authentication, but inactive servers don't waste resources.

### Change 2: Keep Containers on Logout

```python
# jupyterhub_config.py
c.JupyterHub.shutdown_on_logout = False
c.DockerSpawner.remove = False  # Changed from True

# But cleanup old stopped containers daily
# (Add cron job or cleanup script)
```

**Why**: User can resume their work if they reconnect within 24 hours.

### Change 3: Activity-Based Extension

```python
# Auto-extend session if user is active
c.JupyterHub.activity_resolution = 60  # Check every minute
c.JupyterHub.hub_activity_interval = 300  # Report activity every 5 min

# Extend token if active
def activity_callback(user, activity):
    if is_active(activity):
        extend_user_token(user, hours=1)

c.JupyterHub.activity_callback = activity_callback
```

**Why**: Active users don't get kicked out unexpectedly.

## 🔧 Implementation Priority

### High Priority (Do Now)
1. ✅ Add session countdown timer to dashboard (already exists)
2. ⬜ Show warning when < 5 minutes remaining
3. ⬜ Add session expiration info to Jupyter startup message

### Medium Priority (This Week)
4. ⬜ Implement session extension endpoint
5. ⬜ Add "Extend Session" button to portal
6. ⬜ Increase session time to 24 hours
7. ⬜ Keep containers after logout

### Low Priority (Future)
8. ⬜ Auto-save notebooks before shutdown
9. ⬜ Activity-based session extension
10. ⬜ Email notification before expiration

## 🧪 Testing Session Expiration

### Quick Test (Without Waiting 8 Hours)

**1. Temporarily reduce session time:**

```python
# portal-backend/main.py
expires_delta=timedelta(minutes=2)  # Changed from hours=8
```

```python
# jupyterhub/jupyterhub_config.py
c.JupyterHub.cookie_max_age_days = 0.0014  # ~2 minutes
c.JupyterHub.oauth_token_expires_in = 120  # 2 minutes
```

**2. Rebuild and restart:**
```bash
docker-compose down
docker-compose build --no-cache portal-backend jupyterhub
docker-compose up -d
```

**3. Test scenario:**
- Login to portal
- Launch Jupyter
- Wait 2 minutes
- Try to interact with Jupyter → Should redirect to login
- Try to access portal API → Should get 401 Unauthorized

**4. Restore original settings** after testing!

## 📝 Summary

### Current Behavior
- **8-hour sessions** for both portal and Jupyter
- **No warning** before expiration
- **Hard logout** when expired
- **Work lost** if not saved

### Recommended Behavior
- **24-hour sessions** with activity tracking
- **Warnings** at 5 min and 1 min before expiration
- **Session extension** option for active users
- **Containers persist** after logout for resumption
- **Auto-save** before forced logout

### User Experience Goals
1. **Predictable**: Users know when session will expire
2. **Flexible**: Can extend if needed
3. **Safe**: Work is saved automatically
4. **Efficient**: Inactive sessions don't waste resources

---

**Next Steps**: 
1. ✅ Fix code logging (in progress)
2. ⬜ Add expiration warnings
3. ⬜ Implement session extension
4. ⬜ Increase default session time to 24h

