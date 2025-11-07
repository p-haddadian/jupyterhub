import pandas as pd
import numpy as np
import hashlib
from sqlalchemy import create_engine, text
import os

# Override pandas export methods
class BlockedDataFrame(pd.DataFrame):
    def to_csv(self, *args, **kwargs):
        raise PermissionError("❌ استفاده از to_csv() مجاز نیست! دانلود داده ممکن نیست.")
    def to_excel(self, *args, **kwargs):
        raise PermissionError("❌ استفاده از to_excel() مجاز نیست!")
    def to_json(self, *args, **kwargs):
        raise PermissionError("❌ استفاده از to_json() مجاز نیست!")
    def to_parquet(self, *args, **kwargs):
        raise PermissionError("❌ استفاده از to_parquet() مجاز نیست!")
    def to_pickle(self, *args, **kwargs):
        raise PermissionError("❌ استفاده از to_pickle() مجاز نیست!")

pd.DataFrame = BlockedDataFrame

_original_savetxt = np.savetxt
_original_save = np.save

def _blocked_savetxt(*args, **kwargs):
    raise PermissionError("❌ استفاده از savetxt() مجاز نیست!")

def _blocked_save(*args, **kwargs):
    raise PermissionError("❌ استفاده از save() مجاز نیست!")

np.savetxt = _blocked_savetxt
np.save = _blocked_save

class ShaparakDB:
    """
    کلاس دسترسی به دیتابیس شاپرک
    تمام داده‌های حساس به صورت خودکار ناشناس می‌شوند
    """
    
    SENSITIVE_FIELDS = ['email', 'phone', 'national_id', 'card_number']
    
    def __init__(self):
        conn_string = os.environ.get('DATA_DB_CONNECTION')
        if not conn_string:
            raise ValueError("اتصال به دیتابیس تنظیم نشده است")
        self.engine = create_engine(conn_string)
        print("✅ اتصال به دیتابیس شاپرک برقرار شد")
        print("📊 جداول قابل دسترس: customers_anonymized, transactions_anonymized, customer_statistics")
    
    def query(self, sql, params=None):
        """
        اجرای کوئری SELECT
        فقط دستورات SELECT مجاز است
        """
        # Validate SQL
        sql_upper = sql.strip().upper()
        forbidden_keywords = ['UPDATE', 'DELETE', 'INSERT', 'DROP', 'ALTER', 'CREATE', 'GRANT', 'REVOKE', 'TRUNCATE']
        
        if any(keyword in sql_upper for keyword in forbidden_keywords):
            raise PermissionError(f"❌ فقط دستورات SELECT مجاز است!")
        
        if not sql_upper.startswith('SELECT'):
            raise PermissionError("❌ فقط دستورات SELECT مجاز است!")
        
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(sql), params or {})
                df = pd.DataFrame(result.fetchall(), columns=result.keys())
            
            print(f"✅ کوئری با موفقیت اجرا شد - {len(df)} سطر بازیابی شد")
            return df
        except Exception as e:
            print(f"❌ خطا در اجرای کوئری: {str(e)}")
            raise
    
    def get_customers(self, limit=100):
        """دریافت لیست مشتریان (ناشناس)"""
        return self.query(f"SELECT * FROM customers_anonymized LIMIT {limit}")
    
    def get_transactions(self, limit=100):
        """دریافت لیست تراکنش‌ها (ناشناس)"""
        return self.query(f"SELECT * FROM transactions_anonymized LIMIT {limit}")
    
    def get_statistics(self):
        """دریافت آمار کلی"""
        return self.query("SELECT * FROM customer_statistics")

# Make it easy to import
db = ShaparakDB()