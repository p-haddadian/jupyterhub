"""
Block all data export methods to prevent data leakage
"""
import builtins

_original_open = builtins.open
_original_input = builtins.input

def _blocked_file_open(path, mode='r', *args, **kwargs):
    """Block file operations that could export data"""
    if 'w' in mode or 'a' in mode or '+' in mode:
        filename = str(path).split('/')[-1].split('\\')[-1]
        blocked_extensions = ['.csv', '.xlsx', '.xls', '.json', '.parquet', '.pickle', '.pkl', '.h5', '.hdf5', '.feather', '.xlsb']
        
        if any(filename.endswith(ext) for ext in blocked_extensions):
            raise PermissionError(f"❌ ذخیره فایل {filename} مجاز نیست! دانلود داده مجاز نمی‌باشد.")
    
    return _original_open(path, mode, *args, **kwargs)

def _blocked_input(prompt=''):
    """Block input() to prevent interaction-based data extraction"""
    raise PermissionError("❌ استفاده از input() مجاز نیست!")

builtins.open = _blocked_file_open
builtins.input = _blocked_input
print("🔒 سیستم جلوگیری از خروج داده فعال شد")