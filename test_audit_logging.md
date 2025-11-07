# Testing Code Execution Audit Logging

## What Was Fixed

1. **Rebuilt Jupyter user image** - The audit logger extension wasn't loading due to image being outdated
2. **Module error fixed** - `ModuleNotFoundError: No module named 'shaparak_audit_logger'` is now resolved
3. **Stopped old containers** - New containers with working logging will be spawned

## How to Test

### Step 1: Launch Fresh Jupyter Instance

1. Go to portal: `http://localhost:8001/portal`
2. Click "راه‌اندازی Jupyter Lab"
3. Wait for Jupyter to load (it will spawn a new container with the updated image)

### Step 2: Check Extension Loaded

In the Jupyter terminal or first cell, you should see:
```
============================================================
🔒 سیستم تحلیل داده شاپرک
============================================================
👤 کاربر: test_user
📊 دسترسی به دیتابیس: db.get_customers(), db.get_transactions(), db.query(sql)
⚠️  تمام اکشن‌ها ثبت می‌شود
❌ نصب پکیج و دانلود فایل مجاز نیست
============================================================

✅ سیستم ثبت لاگ فعال شد - تمام کدها ثبت می‌شوند
```

### Step 3: Run Test Code

Create cells and run:

**Cell 1:**
```python
print("Hello Shaparak!")
x = 10 + 20
print(f"Result: {x}")
```

**Cell 2:**
```python
import pandas as pd
df = pd.DataFrame({'a': [1, 2, 3], 'b': [4, 5, 6]})
print(df)
```

**Cell 3** (This will cause an error - to test error logging):
```python
1 / 0  # This will raise ZeroDivisionError
```

### Step 4: Verify Logs in Database

Connect to PostgreSQL:
```bash
docker exec -it shaparak-postgres psql -U shaparak_admin -d shaparak
```

Check logs:
```sql
-- View all execution logs
SELECT 
    id,
    username,
    cell_number,
    LEFT(code, 50) as code_preview,
    execution_time_ms,
    status,
    timestamp
FROM code_execution_logs
ORDER BY timestamp DESC
LIMIT 10;

-- Count executions per user
SELECT username, COUNT(*) as total_executions
FROM code_execution_logs
GROUP BY username;

-- View errors
SELECT 
    username,
    cell_number,
    LEFT(code, 50) as code_preview,
    LEFT(error_message, 100) as error_preview,
    timestamp
FROM code_execution_logs
WHERE status = 'error'
ORDER BY timestamp DESC;
```

### Step 5: Check Dashboard Stats

The dashboard in the portal shows:
- **Today's executions**: Count of code cells run today
- **Total executions**: All-time count
- **Success rate**: Percentage of successful executions

These stats should now update in real-time as you run code!

## Expected Results

✅ Extension loads when kernel starts  
✅ Every code cell execution is logged  
✅ Success and error status are captured  
✅ Execution time is recorded  
✅ Full code content is saved  
✅ Dashboard stats update automatically  

## Troubleshooting

### Extension Still Not Loading

Check container logs:
```bash
# Find the new container
docker ps | Select-String jupyter

# Check logs (replace CONTAINER_ID)
docker logs CONTAINER_ID | Select-String -Pattern "audit|extension"
```

Should see:
```
✅ سیستم ثبت لاگ فعال شد - تمام کدها ثبت می‌شوند
```

### No Logs in Database

1. Check database connection in container:
```bash
docker exec -it CONTAINER_ID bash
echo $AUDIT_DB_CONNECTION
# Should show: postgresql://jupyter_readonly:jupyter_read_2025@postgres:5432/shaparak
```

2. Test connection:
```bash
docker exec -it CONTAINER_ID psql $AUDIT_DB_CONNECTION -c "SELECT 1;"
```

### Dashboard Not Updating

The portal backend queries:
```python
# In portal-backend/main.py around line 750
SELECT 
    COUNT(*) as total_executions,
    COUNT(CASE WHEN DATE(timestamp) = CURRENT_DATE THEN 1 END) as today_executions,
    COUNT(CASE WHEN status = 'error' THEN 1 END) as total_errors
FROM code_execution_logs
WHERE username = :username
```

Refresh the dashboard page to see updated stats.

## Enhancement Ideas

### 1. Real-Time Activity Feed

Add to dashboard:
```python
@app.get("/api/recent-activity")
async def get_recent_activity(current_user: UserInfo = Depends(get_current_user)):
    with engine.connect() as conn:
        result = conn.execute(
            text("""
                SELECT timestamp, cell_number, LEFT(code, 100) as code_preview, status
                FROM code_execution_logs
                WHERE username = :username
                ORDER BY timestamp DESC
                LIMIT 10
            """),
            {"username": current_user.username}
        )
        return [{"time": row[0], "cell": row[1], "code": row[2], "status": row[3]} 
                for row in result]
```

### 2. Admin Dashboard

View all user activity:
```python
@app.get("/api/admin/all-activity")
async def admin_all_activity(current_user: UserInfo = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(403, "Admin only")
    
    with engine.connect() as conn:
        result = conn.execute(
            text("""
                SELECT username, COUNT(*) as executions, 
                       MAX(timestamp) as last_active
                FROM code_execution_logs
                GROUP BY username
                ORDER BY last_active DESC
            """)
        )
        return [{"user": row[0], "executions": row[1], "last_active": row[2]} 
                for row in result]
```

### 3. Code Search

Search executed code:
```python
@app.get("/api/search-code")
async def search_code(
    query: str,
    current_user: UserInfo = Depends(get_current_user)
):
    with engine.connect() as conn:
        result = conn.execute(
            text("""
                SELECT timestamp, cell_number, code, status
                FROM code_execution_logs
                WHERE username = :username 
                AND code ILIKE :query
                ORDER BY timestamp DESC
                LIMIT 20
            """),
            {"username": current_user.username, "query": f"%{query}%"}
        )
        return [{"time": row[0], "cell": row[1], "code": row[2], "status": row[3]} 
                for row in result]
```

### 4. Execution Time Analytics

Add graphs showing:
- Average execution time per user
- Slow queries (>1000ms)
- Peak usage times

### 5. Anomaly Detection

Flag suspicious activity:
- Excessive failed executions
- Attempts to access unauthorized data
- Unusual execution patterns

## Summary

✅ **Code execution logging is now working**  
✅ **All code cells are automatically logged**  
✅ **Dashboard stats will update**  
✅ **Full audit trail for compliance**  

Test it now by running some code in Jupyter and checking the database!

