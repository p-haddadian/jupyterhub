\c shaparak;

INSERT INTO portal_users (username, email, full_name, organization, hashed_password, is_admin) VALUES
('admin', 'admin@shaparak.ir', 'مدیر سیستم', 'شاپرک', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5LE2AQDyDXN9i', TRUE),
('ali.rezaei', 'ali.rezaei@example.com', 'علی رضایی', 'بانک ملی', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5LE2AQDyDXN9i', FALSE),
('sara.ahmadi', 'sara.ahmadi@example.com', 'سارا احمدی', 'بانک ملت', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5LE2AQDyDXN9i', FALSE);

INSERT INTO customers (full_name, national_id, email, phone, birth_date, city, province, account_balance, credit_score, risk_category)
SELECT 
    (ARRAY['محمد رضایی', 'فاطمه احمدی', 'علی محمدی', 'زهرا حسینی', 'حسین کریمی'])[floor(random() * 5 + 1)],
    LPAD(floor(random() * 10000000000)::TEXT, 10, '0'),
    'user' || generate_series || '@example.com',
    '09' || LPAD(floor(random() * 1000000000)::TEXT, 9, '0'),
    DATE '1970-01-01' + (random() * (DATE '2000-01-01' - DATE '1970-01-01'))::INTEGER,
    (ARRAY['تهران', 'مشهد', 'اصفهان', 'شیراز'])[floor(random() * 4 + 1)],
    (ARRAY['تهران', 'خراسان رضوی', 'اصفهان', 'فارس'])[floor(random() * 4 + 1)],
    floor(random() * 1000000000)::DECIMAL(15, 2),
    floor(random() * 850 + 150)::INTEGER,
    (ARRAY['low', 'medium', 'high'])[floor(random() * 3 + 1)]
FROM generate_series(1, 100);

INSERT INTO transactions (customer_id, transaction_date, amount, transaction_type, card_number, merchant_name, merchant_category, status, description)
SELECT 
    floor(random() * 100 + 1)::INTEGER,
    TIMESTAMP '2024-01-01' + random() * (TIMESTAMP '2024-10-30' - TIMESTAMP '2024-01-01'),
    floor(random() * 10000000 + 10000)::DECIMAL(15, 2),
    (ARRAY['purchase', 'withdrawal', 'transfer'])[floor(random() * 3 + 1)],
    '6037' || LPAD(floor(random() * 1000000000000)::TEXT, 12, '0'),
    (ARRAY['دیجی‌کالا', 'اسنپ', 'رفاه'])[floor(random() * 3 + 1)],
    (ARRAY['خرده‌فروشی', 'رستوران', 'حمل‌ونقل'])[floor(random() * 3 + 1)],
    'completed',
    'تراکنش شماره ' || generate_series
FROM generate_series(1, 500);
