from IPython.core.events import EventManager
from sqlalchemy import create_engine, text
import os
import datetime

class AuditLogger:
    def __init__(self, username, db_url):
        self.username = username
        self.engine = create_engine(db_url)
        self.cell_number = 0
        self.start_time = None
        print("✅ سیستم ثبت لاگ فعال شد - تمام کدها ثبت می‌شوند")
    
    def pre_run_cell(self, info):
        self.current_code = info.raw_cell
        self.start_time = datetime.datetime.now()
    
    def post_run_cell(self, result):
        if not hasattr(self, 'current_code'):
            return
        
        exec_time = int((datetime.datetime.now() - self.start_time).total_seconds() * 1000)
        
        status = 'success' if result.success else 'error'
        error_msg = str(result.error_in_exec) if hasattr(result, 'error_in_exec') and result.error_in_exec else None
        
        try:
            with self.engine.connect() as conn:
                conn.execute(
                    text("""
                        INSERT INTO code_execution_logs 
                        (username, session_id, cell_number, code, execution_time_ms, status, error_message)
                        VALUES (:username, :session_id, :cell_number, :code, :exec_time, :status, :error)
                    """),
                    {
                        'username': self.username,
                        'session_id': os.environ.get('JPY_SESSION_NAME', 'unknown'),
                        'cell_number': self.cell_number,
                        'code': self.current_code,
                        'exec_time': exec_time,
                        'status': status,
                        'error': error_msg
                    }
                )
                conn.commit()
        except Exception as e:
            print(f"⚠️  خطا در ثبت لاگ: {e}")
        
        self.cell_number += 1

def load_ipython_extension(ipython):
    username = os.environ.get('JUPYTERHUB_USER', 'unknown')
    db_url = os.environ.get('AUDIT_DB_CONNECTION')
    
    if db_url:
        logger = AuditLogger(username, db_url)
        ipython.events.register('pre_run_cell', logger.pre_run_cell)
        ipython.events.register('post_run_cell', logger.post_run_cell)