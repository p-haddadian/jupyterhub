# Code Execution Monitoring & Activity API

## 🎯 Overview

Complete code execution logging and monitoring system for tracking all user activity in Jupyter notebooks.

## ✅ What's Fixed

1. **Audit Logger Extension** - Rebuilt Jupyter user image with working `shaparak_audit_logger`
2. **Database Logging** - All code executions now automatically logged to PostgreSQL
3. **Dashboard Stats** - Enhanced with average execution time and last execution timestamp
4. **New API Endpoints** - 6 new endpoints for comprehensive activity monitoring

## 📊 Enhanced Dashboard Stats

The `/api/dashboard` endpoint now returns:

```json
{
  "stats": {
    "total_executions": 150,
    "today_executions": 12,
    "total_errors": 5,
    "success_rate": 96.7,
    "avg_execution_time_ms": 234.56,
    "last_execution": "2025-10-30T15:30:45"
  }
}
```

## 🆕 New API Endpoints

### 1. Get Recent Activity
**GET** `/api/activity/recent?limit=10`

Returns the most recent code executions with full details.

**Parameters:**
- `limit` (optional, default: 10) - Number of recent activities to return

**Response:**
```json
{
  "activities": [
    {
      "id": 123,
      "timestamp": "2025-10-30T15:30:45",
      "cell_number": 5,
      "code": "import pandas as pd\ndf = pd.read_csv('data.csv')\nprint(df.head())",
      "execution_time_ms": 234,
      "status": "success",
      "error_message": null
    },
    {
      "id": 122,
      "timestamp": "2025-10-30T15:29:12",
      "cell_number": 4,
      "code": "1 / 0",
      "execution_time_ms": 12,
      "status": "error",
      "error_message": "ZeroDivisionError: division by zero"
    }
  ],
  "count": 2
}
```

**Usage Example:**
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8001/api/activity/recent?limit=5"
```

---

### 2. Get Activity Statistics
**GET** `/api/activity/stats?days=7`

Returns daily execution statistics for the past N days.

**Parameters:**
- `days` (optional, default: 7) - Number of days to include in statistics

**Response:**
```json
{
  "daily_stats": [
    {
      "date": "2025-10-30",
      "executions": 45,
      "success_count": 42,
      "error_count": 3,
      "avg_time_ms": 187.23
    },
    {
      "date": "2025-10-29",
      "executions": 38,
      "success_count": 36,
      "error_count": 2,
      "avg_time_ms": 201.45
    }
  ],
  "period_days": 7
}
```

**Usage Example:**
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8001/api/activity/stats?days=30"
```

**Use Cases:**
- Generate activity charts
- Track productivity trends
- Monitor error patterns over time

---

### 3. Search Code History
**GET** `/api/activity/search?query=pandas&limit=20`

Search through executed code history by keyword.

**Parameters:**
- `query` (required) - Search keyword (minimum 2 characters)
- `limit` (optional, default: 20) - Maximum number of results

**Response:**
```json
{
  "results": [
    {
      "id": 123,
      "timestamp": "2025-10-30T15:30:45",
      "cell_number": 5,
      "code": "import pandas as pd\ndf = pd.read_csv('data.csv')",
      "execution_time_ms": 234,
      "status": "success"
    }
  ],
  "query": "pandas",
  "count": 1
}
```

**Usage Examples:**
```bash
# Find all uses of a library
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8001/api/activity/search?query=matplotlib"

# Find specific functions
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8001/api/activity/search?query=read_csv"
```

**Use Cases:**
- Code reuse - find how you used a library before
- Debug tracking - find where errors occurred
- Audit - verify which APIs were called

---

### 4. Admin: All Users Activity
**GET** `/api/admin/all-users-activity` 🔒 **Admin Only**

View activity summary for all users in the system.

**Response:**
```json
{
  "users_activity": [
    {
      "username": "test_user",
      "total_executions": 150,
      "today_executions": 12,
      "error_count": 5,
      "avg_time_ms": 234.56,
      "last_active": "2025-10-30T15:30:45"
    },
    {
      "username": "ali.rezaei",
      "total_executions": 89,
      "today_executions": 0,
      "error_count": 2,
      "avg_time_ms": 189.34,
      "last_active": "2025-10-29T18:22:10"
    }
  ],
  "total_users": 2
}
```

**Usage Example:**
```bash
curl -H "Authorization: Bearer ADMIN_TOKEN" \
  "http://localhost:8001/api/admin/all-users-activity"
```

**Use Cases:**
- Monitor system-wide activity
- Identify inactive users
- Track user engagement
- Capacity planning

---

### 5. Admin: System Statistics
**GET** `/api/admin/system-stats` 🔒 **Admin Only**

Comprehensive system-wide statistics and insights.

**Response:**
```json
{
  "total_executions": 500,
  "active_users": 5,
  "today_executions": 67,
  "total_errors": 23,
  "avg_execution_time_ms": 198.45,
  "top_users": [
    {"username": "test_user", "executions": 150},
    {"username": "ali.rezaei", "executions": 89},
    {"username": "sara.ahmadi", "executions": 78}
  ],
  "recent_errors": [
    {
      "username": "test_user",
      "timestamp": "2025-10-30T15:29:12",
      "code_preview": "1 / 0",
      "error": "ZeroDivisionError: division by zero"
    }
  ]
}
```

**Usage Example:**
```bash
curl -H "Authorization: Bearer ADMIN_TOKEN" \
  "http://localhost:8001/api/admin/system-stats"
```

**Use Cases:**
- System health monitoring
- Error tracking and debugging
- Usage analytics
- Performance optimization

---

### 6. Get Execution Logs (Existing, Enhanced)
**GET** `/api/logs?limit=20&offset=0`

Paginated view of execution logs with previews.

**Response:**
```json
{
  "logs": [
    {
      "id": 123,
      "timestamp": "2025-10-30T15:30:45",
      "cell_number": 5,
      "code_preview": "import pandas as pd\ndf = pd.read_csv('data.csv')\nprint(df.head())",
      "execution_time_ms": 234,
      "status": "success",
      "error_preview": null
    }
  ],
  "count": 1
}
```

---

## 🧪 Testing the System

### Step 1: Launch Jupyter and Run Code

1. Go to portal: `http://localhost:8001/portal`
2. Click "راه‌اندازی Jupyter Lab"
3. Create a notebook and run test cells:

```python
# Cell 1: Success
print("Hello Shaparak!")
x = 10 + 20
print(f"Result: {x}")
```

```python
# Cell 2: Data processing
import pandas as pd
df = pd.DataFrame({'a': [1, 2, 3], 'b': [4, 5, 6]})
print(df)
```

```python
# Cell 3: Intentional error
1 / 0  # ZeroDivisionError
```

### Step 2: Verify Logging in Jupyter

When the kernel starts, you should see:
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

### Step 3: Check Dashboard Stats

Refresh the dashboard page - you should see updated stats:
- **امروز**: Should show today's execution count
- **کل اجراها**: Total execution count
- **نرخ موفقیت**: Success rate percentage
- **میانگین زمان**: Average execution time

### Step 4: Query the API

```bash
# Get your auth token
TOKEN=$(curl -X POST http://localhost:8001/api/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=test_user&password=your_password" \
  | jq -r '.access_token')

# View recent activity
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8001/api/activity/recent?limit=5 | jq

# Search for pandas usage
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8001/api/activity/search?query=pandas" | jq

# Get daily stats
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8001/api/activity/stats?days=7" | jq
```

### Step 5: Verify in Database

```bash
# Connect to PostgreSQL
docker exec -it shaparak-postgres psql -U shaparak_admin -d shaparak
```

```sql
-- View all logs
SELECT id, username, cell_number, LEFT(code, 50) as code, 
       execution_time_ms, status, timestamp
FROM code_execution_logs
ORDER BY timestamp DESC
LIMIT 10;

-- Count by user
SELECT username, COUNT(*) as executions
FROM code_execution_logs
GROUP BY username;

-- View errors
SELECT username, LEFT(code, 50), LEFT(error_message, 100), timestamp
FROM code_execution_logs
WHERE status = 'error'
ORDER BY timestamp DESC;
```

---

## 📈 Frontend Integration Examples

### React: Display Recent Activity

```typescript
const RecentActivity = () => {
  const [activities, setActivities] = useState([]);

  useEffect(() => {
    fetch('http://localhost:8001/api/activity/recent?limit=5', {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    .then(res => res.json())
    .then(data => setActivities(data.activities));
  }, []);

  return (
    <div>
      <h3>آخرین فعالیت‌ها</h3>
      {activities.map(act => (
        <div key={act.id} className="activity-card">
          <div className="time">{new Date(act.timestamp).toLocaleString('fa-IR')}</div>
          <div className="code"><pre>{act.code}</pre></div>
          <div className="status">{act.status === 'success' ? '✅' : '❌'}</div>
          <div className="time">{act.execution_time_ms}ms</div>
        </div>
      ))}
    </div>
  );
};
```

### Chart.js: Activity Timeline

```javascript
fetch('http://localhost:8001/api/activity/stats?days=7', {
  headers: { 'Authorization': `Bearer ${token}` }
})
.then(res => res.json())
.then(data => {
  const chart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: data.daily_stats.map(d => d.date),
      datasets: [{
        label: 'تعداد اجرا',
        data: data.daily_stats.map(d => d.executions),
        borderColor: 'rgb(75, 192, 192)',
      }]
    }
  });
});
```

---

## 🔐 Security Considerations

1. **User Isolation**: Each user can only see their own activity
2. **Admin Access**: System-wide endpoints require admin privileges
3. **Code Privacy**: Full code content only accessible to the user who executed it
4. **Token-Based Auth**: All endpoints require valid Bearer token

---

## 🚀 Performance Optimizations

### Database Indexing

```sql
-- Add indexes for faster queries
CREATE INDEX idx_code_logs_username ON code_execution_logs(username);
CREATE INDEX idx_code_logs_timestamp ON code_execution_logs(timestamp);
CREATE INDEX idx_code_logs_status ON code_execution_logs(status);
CREATE INDEX idx_code_logs_username_timestamp ON code_execution_logs(username, timestamp DESC);
```

### Query Optimization

All queries use:
- Proper indexing
- LIMIT clauses to prevent large result sets
- LEFT() function for code previews (reduces data transfer)
- Aggregate functions for statistics

---

## 📋 Database Schema

```sql
CREATE TABLE code_execution_logs (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) NOT NULL,
    session_id VARCHAR(255),
    cell_number INTEGER,
    code TEXT NOT NULL,
    execution_time_ms INTEGER,
    status VARCHAR(50),
    error_message TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Indexes
    INDEX idx_username (username),
    INDEX idx_timestamp (timestamp),
    INDEX idx_status (status),
    INDEX idx_username_timestamp (username, timestamp DESC)
);
```

---

## 🎨 Use Case Examples

### 1. Productivity Dashboard
Show user's daily activity with charts and trends.

### 2. Code Snippet Library
Allow users to search and reuse their previous code.

### 3. Error Analysis
Track and categorize errors to improve documentation.

### 4. Compliance Audit
Generate reports of all code executed for regulatory compliance.

### 5. Performance Monitoring
Identify slow queries and optimize them.

### 6. Learning Analytics
Track which libraries and functions users use most.

---

## 🔧 Troubleshooting

### Extension Not Loading

Check Jupyter container logs:
```bash
docker logs CONTAINER_ID | grep -i "audit\|extension"
```

Should see:
```
✅ سیستم ثبت لاگ فعال شد - تمام کدها ثبت می‌شوند
```

If not, rebuild the image:
```bash
cd jupyter-user-image
docker build -t shaparak-jupyter-user:latest .
```

### No Data in API Responses

1. Verify extension is loaded (see above)
2. Check database connection:
```bash
docker exec -it JUPYTER_CONTAINER bash
echo $AUDIT_DB_CONNECTION
```
3. Test database access:
```bash
docker exec -it shaparak-postgres psql -U shaparak_admin -d shaparak \
  -c "SELECT COUNT(*) FROM code_execution_logs;"
```

### Dashboard Not Updating

The dashboard queries the database in real-time. If stats don't update:
1. Hard refresh the page (Ctrl+F5)
2. Check browser console for errors
3. Verify API endpoint is working:
```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8001/api/dashboard
```

---

## 📝 Summary

✅ **All code executions are logged automatically**  
✅ **6 new API endpoints for comprehensive monitoring**  
✅ **Enhanced dashboard with detailed statistics**  
✅ **Admin endpoints for system-wide oversight**  
✅ **Code search and activity history**  
✅ **Full audit trail for compliance**  

**Next Steps:**
1. Launch Jupyter and run test code
2. Verify logging in database
3. Test the new API endpoints
4. Build frontend components to display activity data
5. Set up admin monitoring dashboard

