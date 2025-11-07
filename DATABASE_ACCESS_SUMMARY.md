# Database Access for Jupyter Users

## Summary

Users in Jupyter have **read-only access** to anonymized demo data via the `jupyter_readonly` database user.

## What Users Can Access

### ✅ **Available Tables/Views**

1. **`customers_anonymized`** (View)
   - Anonymized customer data
   - Sensitive fields (name, email, national_id, phone) are hashed or masked
   - Fields: customer_id, full_name (masked), national_id_hash, email_hash, phone_masked, birth_year, city, province, registration_date, balance_category, credit_score, risk_category

2. **`transactions_anonymized`** (View)
   - Anonymized transaction data
   - Card numbers masked (shows only last 4 digits)
   - Fields: transaction_id, customer_id, transaction_date, amount, transaction_type, card_number_masked, merchant_name, merchant_category, status, description_preview

3. **`customer_statistics`** (Materialized View)
   - Statistical aggregations by province
   - Fields: province, customer_count, avg_balance, avg_credit_score

4. **`code_execution_logs`** (Table)
   - INSERT permission only
   - For audit logging code executions

### ❌ **Not Accessible**

- `customers` (raw table with PII)
- `transactions` (raw table with card numbers)
- `portal_users`
- `user_sessions`

## How Users Access Data

### 1. **Via `shaparak_db_proxy` Python API** (Recommended)

Automatically loaded when Jupyter starts:

```python
from shaparak_db_proxy import db

# Get customers
customers = db.get_customers(limit=100)

# Get transactions
transactions = db.get_transactions(limit=100)

# Get statistics
stats = db.get_statistics()

# Custom SQL query (SELECT only)
df = db.query("SELECT * FROM customers_anonymized WHERE province = 'تهران' LIMIT 10")
```

### 2. **Direct PostgreSQL Access**

```python
import psycopg2
import os

conn = psycopg2.connect(os.environ.get('DATA_DB_CONNECTION'))
cursor = conn.cursor()
cursor.execute("SELECT * FROM customers_anonymized LIMIT 10")
rows = cursor.fetchall()
```

## Security Features

1. **Automatic Anonymization**
   - Names: First character + asterisks
   - Email/National ID: MD5 hash
   - Phone: First 4 + mask + last 3 digits
   - Card: Masked showing only last 4 digits

2. **SQL Injection Protection**
   - `db.query()` validates SQL before execution
   - Only SELECT statements allowed
   - Forbidden keywords: UPDATE, DELETE, INSERT, DROP, ALTER, CREATE, GRANT, REVOKE, TRUNCATE

3. **Row-Level Security**
   - Cannot access raw PII tables
   - Only anonymized views accessible

4. **Audit Logging**
   - All queries logged (via audit extension)
   - Tracks username, code, timestamp, execution time

## Environment Variables

Set in Jupyter containers:

- `DATA_DB_CONNECTION`: `postgresql://jupyter_readonly:jupyter_read_2025@postgres:5432/shaparak`
- `AUDIT_DB_CONNECTION`: `postgresql://jupyter_readonly:jupyter_read_2025@postgres:5432/shaparak`

## Database Permissions

```sql
-- jupyter_readonly user has:
GRANT SELECT ON customers_anonymized TO jupyter_readonly;
GRANT SELECT ON transactions_anonymized TO jupyter_readonly;
GRANT SELECT ON customer_statistics TO jupyter_readonly;
GRANT INSERT ON code_execution_logs TO jupyter_readonly;

-- Explicitly denied:
REVOKE ALL ON customers FROM jupyter_readonly;
REVOKE ALL ON transactions FROM jupyter_readonly;
REVOKE ALL ON portal_users FROM jupyter_readonly;
REVOKE ALL ON user_sessions FROM jupyter_readonly;
```

## Sample Data

- **100 customers** across 8 Iranian provinces
- **500 transactions** from Jan 2024 to Oct 2024
- Mix of transaction types: purchase, withdrawal, deposit, transfer, payment
- Various merchants and categories

## Example Queries

### Basic Data Exploration
```python
from shaparak_db_proxy import db

# Customer distribution by province
df = db.query("""
    SELECT province, 
           COUNT(*) as count,
           AVG(credit_score) as avg_score
    FROM customers_anonymized
    GROUP BY province
    ORDER BY count DESC
""")

# Transaction statistics by type
df = db.query("""
    SELECT transaction_type,
           COUNT(*) as count,
           AVG(amount) as avg_amount,
           MIN(amount) as min_amount,
           MAX(amount) as max_amount
    FROM transactions_anonymized
    GROUP BY transaction_type
""")
```

### Time-Series Analysis
```python
# Monthly transaction volume
df = db.query("""
    SELECT DATE_TRUNC('month', transaction_date) as month,
           COUNT(*) as transaction_count,
           SUM(amount) as total_amount
    FROM transactions_anonymized
    WHERE status = 'completed'
    GROUP BY month
    ORDER BY month
""")
```

### Customer Segments
```python
# High-value customers by balance category
df = db.query("""
    SELECT balance_category,
           COUNT(*) as count,
           AVG(credit_score) as avg_credit_score
    FROM customers_anonymized
    GROUP BY balance_category
    HAVING COUNT(*) >= 10
    ORDER BY count DESC
""")
```

## Testing Access

Test in Jupyter:

```python
import os
from shaparak_db_proxy import db

# Check environment variable
print("DB Connection:", os.environ.get('DATA_DB_CONNECTION'))

# Test access
try:
    customers = db.get_customers(5)
    print("\n✅ Access granted!")
    print(f"Retrieved {len(customers)} customers")
    print(customers.head())
except Exception as e:
    print(f"❌ Access denied: {e}")
```

## Troubleshooting

### Permission Denied Error
- Check database permissions: `docker exec shaparak-postgres psql -U jupyter_readonly -d shaparak -c "\dp"`
- Verify `jupyter_readonly` user exists: `docker exec shaparak-postgres psql -U shaparak_admin -d shaparak -c "\du"`

### Table/View Not Found
- Views may not exist - check init script ran: `docker exec shaparak-postgres psql -U shaparak_admin -d shaparak -c "\dv"`
- Re-run init if needed: `docker exec shaparak-postgres psql -U shaparak_admin -f /docker-entrypoint-initdb.d/01-init.sql`

### Connection Error
- Verify `DATA_DB_CONNECTION` environment variable in container
- Test connection: `docker exec jupyter-container printenv | grep DATA_DB_CONNECTION`

## Notes

- All data is synthetic/demo data
- Real production data would need stricter anonymization
- Consider adding more views for common analytical queries
- Materialized views may need periodic refresh: `REFRESH MATERIALIZED VIEW customer_statistics;`

