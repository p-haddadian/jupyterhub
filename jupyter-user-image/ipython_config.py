import sys
import os

c = get_config()

# Add extensions directory to Python path
extensions_dir = os.path.expanduser('~/.ipython/extensions')
if extensions_dir not in sys.path:
    sys.path.insert(0, extensions_dir)

# Load audit extension automatically
c.InteractiveShellApp.extensions = ['shaparak_audit_logger']

# Startup messages
c.InteractiveShellApp.exec_lines = [
    'import os',
    'import sys', 
    'import warnings',
    'warnings.filterwarnings("ignore")',
    '# Block exports BEFORE loading anything else',
    'import shaparak_export_blocker',
    '',
    'from shaparak_db_proxy import db',
    'print("\\n" + "="*60)',
    'print("🔒 سیستم تحلیل داده شاپرک")',
    'print("="*60)',
    'print(f"👤 کاربر: {os.environ.get(\'JUPYTERHUB_USER\', \'ناشناس\')}")',
    'print("📊 دسترسی به دیتابیس: db.get_customers(), db.get_transactions(), db.query(sql)")',
    'print("⚠️  تمام اکشن‌ها ثبت می‌شود")',
    'print("❌ نصب پکیج و دانلود فایل مجاز نیست")',
    'print("="*60 + "\\n")',
]