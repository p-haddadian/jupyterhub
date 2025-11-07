-- ============================================
-- Shaparak Database Initialization Script
-- ============================================
-- Note: Database "shaparak" and user "shaparak_admin" 
-- are already created by docker-compose environment variables

-- Connect to shaparak database
\c shaparak;

-- ============================================
-- Create Additional Users
-- ============================================

-- Create readonly user for Jupyter notebooks
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'jupyter_readonly') THEN
    CREATE USER jupyter_readonly WITH ENCRYPTED PASSWORD 'jupyter_read_2025';
    RAISE NOTICE 'User jupyter_readonly created';
  ELSE
    RAISE NOTICE 'User jupyter_readonly already exists';
  END IF;
END
$$;

-- Grant database privileges
GRANT CONNECT ON DATABASE shaparak TO shaparak_admin;
GRANT CONNECT ON DATABASE shaparak TO jupyter_readonly;

-- ============================================
-- Create Tables
-- ============================================

-- Portal Users Table
CREATE TABLE IF NOT EXISTS portal_users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    full_name VARCHAR(200) NOT NULL,
    organization VARCHAR(200),
    hashed_password VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    is_admin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);

-- Code Execution Audit Logs Table
CREATE TABLE IF NOT EXISTS code_execution_logs (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) NOT NULL,
    session_id VARCHAR(100),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    cell_number INTEGER,
    code TEXT NOT NULL,
    execution_time_ms INTEGER,
    status VARCHAR(20),
    error_message TEXT,
    output_preview TEXT
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_logs_username ON code_execution_logs(username);
CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON code_execution_logs(timestamp DESC);

-- User Sessions Table
CREATE TABLE IF NOT EXISTS user_sessions (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) NOT NULL,
    session_token VARCHAR(255) UNIQUE NOT NULL,
    jupyter_token VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip_address INET,
    is_active BOOLEAN DEFAULT TRUE
);

-- Demo Data: Customers Table
CREATE TABLE IF NOT EXISTS customers (
    customer_id SERIAL PRIMARY KEY,
    full_name VARCHAR(200) NOT NULL,
    national_id VARCHAR(10) NOT NULL,
    email VARCHAR(255),
    phone VARCHAR(15),
    birth_date DATE,
    city VARCHAR(100),
    province VARCHAR(100),
    registration_date DATE DEFAULT CURRENT_DATE,
    account_balance DECIMAL(15, 2),
    credit_score INTEGER,
    risk_category VARCHAR(20)
);

-- Demo Data: Transactions Table
CREATE TABLE IF NOT EXISTS transactions (
    transaction_id SERIAL PRIMARY KEY,
    customer_id INTEGER REFERENCES customers(customer_id),
    transaction_date TIMESTAMP NOT NULL,
    amount DECIMAL(15, 2) NOT NULL,
    transaction_type VARCHAR(50),
    card_number VARCHAR(16),
    merchant_name VARCHAR(200),
    merchant_category VARCHAR(100),
    status VARCHAR(20),
    description TEXT
);

-- ============================================
-- Create Anonymized Views
-- ============================================

-- Anonymized Customers View (OR REPLACE handles existing views)
CREATE OR REPLACE VIEW customers_anonymized AS
SELECT 
    customer_id,
    SUBSTRING(full_name, 1, 1) || REPEAT('*', LENGTH(full_name) - 1) AS full_name,
    MD5(national_id::TEXT) AS national_id_hash,
    MD5(email::TEXT) AS email_hash,
    LEFT(phone, 4) || '****' || RIGHT(phone, 3) AS phone_masked,
    EXTRACT(YEAR FROM birth_date) AS birth_year,
    city,
    province,
    registration_date,
    CASE 
        WHEN account_balance < 10000000 THEN 'low'
        WHEN account_balance < 100000000 THEN 'medium'
        WHEN account_balance < 500000000 THEN 'high'
        ELSE 'very_high'
    END AS balance_category,
    credit_score,
    risk_category
FROM customers;

-- Anonymized Transactions View
CREATE OR REPLACE VIEW transactions_anonymized AS
SELECT 
    transaction_id,
    customer_id,
    transaction_date,
    amount,
    transaction_type,
    '****-****-****-' || RIGHT(card_number, 4) AS card_number_masked,
    merchant_name,
    merchant_category,
    status,
    LEFT(description, 50) AS description_preview
FROM transactions;

-- Statistics View
CREATE MATERIALIZED VIEW IF NOT EXISTS customer_statistics AS
SELECT 
    province,
    COUNT(*) as customer_count,
    AVG(account_balance) as avg_balance,
    AVG(credit_score) as avg_credit_score
FROM customers
GROUP BY province;

-- ============================================
-- Set Permissions
-- ============================================

-- Grant permissions to shaparak_admin (full access)
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO shaparak_admin;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO shaparak_admin;
GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO shaparak_admin;

-- Grant permissions to jupyter_readonly (limited access)
GRANT SELECT ON customers_anonymized TO jupyter_readonly;
GRANT SELECT ON transactions_anonymized TO jupyter_readonly;
GRANT SELECT ON customer_statistics TO jupyter_readonly;
GRANT INSERT ON code_execution_logs TO jupyter_readonly;
GRANT USAGE, SELECT ON SEQUENCE code_execution_logs_id_seq TO jupyter_readonly;

-- Explicitly revoke access to sensitive tables
REVOKE ALL ON customers FROM jupyter_readonly;
REVOKE ALL ON transactions FROM jupyter_readonly;
REVOKE ALL ON portal_users FROM jupyter_readonly;
REVOKE ALL ON user_sessions FROM jupyter_readonly;

-- Set default privileges for future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO jupyter_readonly;

-- ============================================
-- Insert Sample Data
-- ============================================

-- Insert demo portal users (password is 'shaparak123' for all)
INSERT INTO portal_users (username, email, full_name, organization, hashed_password, is_admin) 
VALUES
    ('admin', 'admin@shaparak.ir', 'مدیر سیستم', 'شاپرک', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5LE2AQDyDXN9i', TRUE),
    ('ali.rezaei', 'ali.rezaei@example.com', 'علی رضایی', 'بانک ملی', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5LE2AQDyDXN9i', FALSE),
    ('sara.ahmadi', 'sara.ahmadi@example.com', 'سارا احمدی', 'بانک ملت', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5LE2AQDyDXN9i', FALSE),
    ('reza.mohammadi', 'reza.mohammadi@example.com', 'رضا محمدی', 'بانک صادرات', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5LE2AQDyDXN9i', FALSE)
ON CONFLICT (username) DO NOTHING;

-- Insert sample customers (100 records)
INSERT INTO customers (full_name, national_id, email, phone, birth_date, city, province, account_balance, credit_score, risk_category)
SELECT 
    (ARRAY['محمد رضایی', 'فاطمه احمدی', 'علی محمدی', 'زهرا حسینی', 'حسین کریمی', 'مریم موسوی', 'مهدی اکبری', 'سارا جعفری', 'امیر نجفی', 'لیلا صادقی'])[floor(random() * 10 + 1)],
    LPAD(floor(random() * 10000000000)::TEXT, 10, '0'),
    'user' || generate_series || '@example.com',
    '09' || LPAD(floor(random() * 1000000000)::TEXT, 9, '0'),
    DATE '1970-01-01' + (random() * (DATE '2000-01-01' - DATE '1970-01-01'))::INTEGER,
    (ARRAY['تهران', 'مشهد', 'اصفهان', 'شیراز', 'تبریز', 'کرج', 'اهواز', 'قم'])[floor(random() * 8 + 1)],
    (ARRAY['تهران', 'خراسان رضوی', 'اصفهان', 'فارس', 'آذربایجان شرقی', 'البرز', 'خوزستان', 'قم'])[floor(random() * 8 + 1)],
    floor(random() * 1000000000)::DECIMAL(15, 2),
    floor(random() * 850 + 150)::INTEGER,
    (ARRAY['low', 'medium', 'high'])[floor(random() * 3 + 1)]
FROM generate_series(1, 100)
ON CONFLICT DO NOTHING;

-- Insert sample transactions (500 records)
INSERT INTO transactions (customer_id, transaction_date, amount, transaction_type, card_number, merchant_name, merchant_category, status, description)
SELECT 
    floor(random() * 100 + 1)::INTEGER,
    TIMESTAMP '2024-01-01' + random() * (TIMESTAMP '2024-10-30' - TIMESTAMP '2024-01-01'),
    floor(random() * 10000000 + 10000)::DECIMAL(15, 2),
    (ARRAY['purchase', 'withdrawal', 'deposit', 'transfer', 'payment'])[floor(random() * 5 + 1)],
    '6037' || LPAD(floor(random() * 1000000000000)::TEXT, 12, '0'),
    (ARRAY['دیجی‌کالا', 'اسنپ', 'چارسومارکت', 'رفاه', 'شهروند', 'کوروش', 'مگامال'])[floor(random() * 7 + 1)],
    (ARRAY['خرده‌فروشی', 'رستوران', 'حمل‌ونقل', 'پوشاک', 'الکترونیک', 'بهداشت'])[floor(random() * 6 + 1)],
    (ARRAY['completed', 'pending', 'failed'])[floor(random() * 3 + 1)],
    'تراکنش خودکار شماره ' || generate_series
FROM generate_series(1, 500)
ON CONFLICT DO NOTHING;

-- Refresh materialized view
REFRESH MATERIALIZED VIEW customer_statistics;

-- ============================================
-- Verification
-- ============================================

-- Display summary
DO $$
DECLARE
    user_count INTEGER;
    customer_count INTEGER;
    transaction_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO user_count FROM portal_users;
    SELECT COUNT(*) INTO customer_count FROM customers;
    SELECT COUNT(*) INTO transaction_count FROM transactions;
    
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Database Initialization Complete!';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Portal Users: %', user_count;
    RAISE NOTICE 'Customers: %', customer_count;
    RAISE NOTICE 'Transactions: %', transaction_count;
    RAISE NOTICE '========================================';
END $$;