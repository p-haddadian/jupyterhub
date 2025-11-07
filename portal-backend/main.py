from fastapi.responses import HTMLResponse
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, validator
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import create_engine, text
import httpx
import os
import re
import asyncio
from typing import Optional, Dict, Any

app = FastAPI(
    title="Shaparak Data Platform API",
    description="API for secure data analysis platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
DATABASE_URL = os.environ.get('DATABASE_URL')
SECRET_KEY = os.environ.get('SECRET_KEY')
JUPYTERHUB_API_URL = os.environ.get('JUPYTERHUB_API_URL')
JUPYTERHUB_API_TOKEN = os.environ.get('JUPYTERHUB_API_TOKEN')

engine = create_engine(DATABASE_URL)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/token")

# ============= Models =============

class UserRegister(BaseModel):
    username: str
    email: EmailStr
    full_name: str
    password: str
    organization: str = ""
    
    @validator('username')
    def username_valid(cls, v):
        if not re.match(r'^[a-z0-9._-]{3,20}$', v):
            raise ValueError('نام کاربری باید 3-20 کاراکتر و فقط شامل حروف انگلیسی کوچک، اعداد، نقطه، خط تیره باشد')
        return v
    
    @validator('password')
    def password_strong(cls, v):
        if len(v) < 8:
            raise ValueError('رمز عبور باید حداقل 8 کاراکتر باشد')
        return v
    
    @validator('full_name')
    def name_not_empty(cls, v):
        if not v.strip():
            raise ValueError('نام و نام خانوادگی الزامی است')
        return v

class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    username: str
    full_name: str

class UserInfo(BaseModel):
    username: str
    email: str
    full_name: str
    organization: str
    created_at: datetime
    last_login: datetime = None
    is_admin: bool = False

class DashboardResponse(BaseModel):
    user: UserInfo
    session_remaining_seconds: int
    jupyter_status: dict
    stats: dict

class JupyterLaunchResponse(BaseModel):
    status: str
    url: str
    message: str

class MessageResponse(BaseModel):
    message: str
    details: dict = {}

# ============= Helper Functions =============

async def call_jupyterhub_api(
    method: str,
    endpoint: str,
    json_data: Optional[Dict[str, Any]] = None,
    retries: int = 3,
    timeout: float = 10.0
) -> Optional[httpx.Response]:
    """
    Make API call to JupyterHub with retry logic
    
    Args:
        method: HTTP method (GET, POST, DELETE, etc.)
        endpoint: API endpoint path (e.g., '/users/username')
        json_data: JSON data to send (for POST/PUT)
        retries: Number of retry attempts
        timeout: Request timeout in seconds
    
    Returns:
        Response object or None if all retries failed
    """
    url = f"{JUPYTERHUB_API_URL}{endpoint}"
    headers = {"Authorization": f"token {JUPYTERHUB_API_TOKEN}"}
    
    for attempt in range(retries):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                if method.upper() == "GET":
                    response = await client.get(url, headers=headers)
                elif method.upper() == "POST":
                    response = await client.post(url, headers=headers, json=json_data or {})
                elif method.upper() == "DELETE":
                    response = await client.delete(url, headers=headers)
                elif method.upper() == "PUT":
                    response = await client.put(url, headers=headers, json=json_data or {})
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")
                
                return response
                
        except (httpx.TimeoutException, httpx.ConnectError) as e:
            if attempt < retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff
                print(f"JupyterHub API call failed (attempt {attempt + 1}/{retries}): {e}. Retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
            else:
                print(f"JupyterHub API call failed after {retries} attempts: {e}")
                return None
        except Exception as e:
            print(f"Unexpected error calling JupyterHub API: {e}")
            return None
    
    return None

def create_access_token(data: dict, expires_delta: timedelta):
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    return jwt.encode(to_encode, SECRET_KEY, algorithm="HS256")

def verify_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        username = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="توکن نامعتبر است")
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="توکن منقضی شده یا نامعتبر است")

async def get_current_user(token: str = Depends(oauth2_scheme)) -> UserInfo:
    payload = verify_token(token)
    username = payload.get("sub")
    
    with engine.connect() as conn:
        result = conn.execute(
            text("""
                SELECT username, email, full_name, organization, created_at, last_login, is_admin 
                FROM portal_users 
                WHERE username = :username AND is_active = TRUE
            """),
            {"username": username}
        )
        user = result.fetchone()
    
    if not user:
        raise HTTPException(status_code=404, detail="کاربر یافت نشد")
    
    return UserInfo(
        username=user[0],
        email=user[1],
        full_name=user[2],
        organization=user[3] or "",
        created_at=user[4],
        last_login=user[5],
        is_admin=user[6]
    )

# ============= Routes =============

@app.get("/portal", response_class=HTMLResponse, tags=["Root"])
async def portal():
    """پورتال وب"""
    return """
    <!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>پورتال شاپرک - پلتفرم تحلیل داده</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.rtl.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/gh/rastikerdar/vazirmatn@v33.003/Vazirmatn-font-face.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <style>
        :root {
            /* Material Design 3 Color System - Organizational Theme */
            --md-primary: #1565C0;
            --md-primary-variant: #0D47A1;
            --md-secondary: #455A64;
            --md-secondary-variant: #263238;
            --md-accent: #FF6F00;
            --md-surface: #FFFFFF;
            --md-surface-variant: #F5F7FA;
            --md-background: #FAFBFC;
            --md-error: #D32F2F;
            --md-success: #2E7D32;
            --md-warning: #F57C00;
            --md-info: #1976D2;
            
            /* Text Colors */
            --md-on-surface: #1C1B1F;
            --md-on-surface-variant: #49454F;
            --md-on-primary: #FFFFFF;
            --md-outline: #79747E;
            --md-outline-variant: #CAC4D0;
            
            /* Elevation Shadows */
            --md-elevation-1: 0 1px 3px rgba(0,0,0,0.12), 0 1px 2px rgba(0,0,0,0.24);
            --md-elevation-2: 0 3px 6px rgba(0,0,0,0.16), 0 3px 6px rgba(0,0,0,0.23);
            --md-elevation-3: 0 10px 20px rgba(0,0,0,0.19), 0 6px 6px rgba(0,0,0,0.23);
            --md-elevation-4: 0 14px 28px rgba(0,0,0,0.25), 0 10px 10px rgba(0,0,0,0.22);
            --md-elevation-5: 0 19px 38px rgba(0,0,0,0.30), 0 15px 12px rgba(0,0,0,0.22);
        }

        * {
            box-sizing: border-box;
        }

        body {
            font-family: 'Vazirmatn', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, var(--md-primary) 0%, var(--md-primary-variant) 100%);
            min-height: 100vh;
            padding: 24px;
            margin: 0;
            line-height: 1.5;
            color: var(--md-on-surface);
        }

        /* Typography Scale */
        .headline-1 { font-size: 2.5rem; font-weight: 400; line-height: 1.2; }
        .headline-2 { font-size: 2rem; font-weight: 400; line-height: 1.2; }
        .headline-3 { font-size: 1.75rem; font-weight: 400; line-height: 1.3; }
        .headline-4 { font-size: 1.5rem; font-weight: 400; line-height: 1.3; }
        .headline-5 { font-size: 1.25rem; font-weight: 400; line-height: 1.4; }
        .headline-6 { font-size: 1.125rem; font-weight: 500; line-height: 1.4; }
        .body-1 { font-size: 1rem; font-weight: 400; line-height: 1.5; }
        .body-2 { font-size: 0.875rem; font-weight: 400; line-height: 1.43; }
        .caption { font-size: 0.75rem; font-weight: 400; line-height: 1.33; }
        .button-text { font-size: 0.875rem; font-weight: 500; line-height: 1.25; text-transform: uppercase; }

        .auth-card {
            background: var(--md-surface);
            border-radius: 28px;
            box-shadow: var(--md-elevation-5);
            overflow: hidden;
            max-width: 480px;
            margin: 40px auto;
            animation: slideUp 0.6s cubic-bezier(0.4, 0, 0.2, 1);
            border: 1px solid var(--md-outline-variant);
        }

        @keyframes slideUp {
            from { 
                opacity: 0; 
                transform: translateY(40px) scale(0.95); 
            }
            to { 
                opacity: 1; 
                transform: translateY(0) scale(1); 
            }
        }

        .auth-header {
            background: linear-gradient(135deg, var(--md-surface-variant) 0%, var(--md-background) 100%);
            padding: 48px 32px;
            text-align: center;
            position: relative;
        }

        .auth-header::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: linear-gradient(90deg, var(--md-primary) 0%, var(--md-accent) 100%);
        }

        .auth-header h1 {
            color: var(--md-on-surface);
            font-size: 2.25rem;
            font-weight: 600;
            margin: 0 0 8px 0;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 12px;
        }

        .auth-header h1 i {
            color: var(--md-primary);
            font-size: 2rem;
        }

        .auth-header p {
            color: var(--md-on-surface-variant);
            margin: 0;
            font-size: 1rem;
            font-weight: 400;
        }

        .auth-body {
            padding: 32px;
        }

        .form-label {
            font-weight: 500;
            color: var(--md-on-surface);
            margin-bottom: 8px;
            display: block;
            font-size: 0.875rem;
        }

        .form-control {
            border: 2px solid var(--md-outline-variant);
            border-radius: 16px;
            padding: 16px 20px;
            transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
            background: var(--md-surface);
            font-family: inherit;
            font-size: 1rem;
            width: 100%;
            outline: none;
        }

        .form-control:focus {
            border-color: var(--md-primary);
            background: var(--md-surface);
            box-shadow: 0 0 0 4px rgba(21, 101, 192, 0.12);
            transform: translateY(-1px);
        }

        .form-control:hover:not(:focus) {
            border-color: var(--md-outline);
        }

        .btn {
            border-radius: 20px;
            padding: 14px 24px;
            font-weight: 500;
            font-size: 0.875rem;
            text-transform: none;
            transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
            border: none;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            text-decoration: none;
            outline: none;
        }

        .btn-primary {
            background: var(--md-primary);
            color: var(--md-on-primary);
            box-shadow: var(--md-elevation-1);
        }

        .btn-primary:hover {
            background: var(--md-primary-variant);
            box-shadow: var(--md-elevation-2);
            transform: translateY(-1px);
        }

        .btn-primary:active {
            transform: translateY(0);
            box-shadow: var(--md-elevation-1);
        }

        .btn-danger {
            background: var(--md-error);
            color: white;
            box-shadow: var(--md-elevation-1);
        }

        .btn-danger:hover {
            background: #B71C1C;
            box-shadow: var(--md-elevation-2);
            transform: translateY(-1px);
        }

        .btn-link {
            color: var(--md-primary);
            text-decoration: none;
            font-weight: 500;
            transition: color 0.2s ease;
        }

        .btn-link:hover {
            color: var(--md-primary-variant);
            text-decoration: underline;
        }

        .alert {
            border-radius: 16px;
            padding: 16px 20px;
            border: none;
            font-weight: 400;
        }

        .alert-danger {
            background: rgba(211, 47, 47, 0.12);
            color: var(--md-error);
            border-left: 4px solid var(--md-error);
        }

        .alert-success {
            background: rgba(46, 125, 50, 0.12);
            color: var(--md-success);
            border-left: 4px solid var(--md-success);
        }

        .dashboard {
            max-width: 1280px;
            margin: 0 auto;
        }

        .navbar-custom {
            background: var(--md-surface);
            border-radius: 24px;
            padding: 24px 32px;
            box-shadow: var(--md-elevation-2);
            margin-bottom: 32px;
            border: 1px solid var(--md-outline-variant);
        }

        .stat-card {
            background: var(--md-surface);
            border-radius: 24px;
            padding: 32px;
            box-shadow: var(--md-elevation-1);
            margin-bottom: 24px;
            border: 1px solid var(--md-outline-variant);
            transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
            position: relative;
            overflow: hidden;
        }

        .stat-card:hover {
            box-shadow: var(--md-elevation-2);
            transform: translateY(-2px);
        }

        .stat-card h5 {
            color: var(--md-on-surface-variant);
            margin: 0 0 16px 0;
            font-size: 0.875rem;
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .stat-card h5 i {
            color: var(--md-primary);
            font-size: 1.25rem;
        }

        .stat-value {
            font-size: 2.75rem;
            font-weight: 600;
            color: var(--md-primary);
            line-height: 1;
            margin: 0;
        }

        .timer {
            font-size: 1.75rem;
            font-weight: 600;
            color: var(--md-accent);
            font-feature-settings: 'tnum';
        }

        .timer.warning {
            color: var(--md-error);
            animation: pulse 1s ease-in-out infinite alternate;
        }

        @keyframes pulse {
            from { opacity: 1; }
            to { opacity: 0.7; }
        }

        /* Utility Classes */
        .mb-3 { margin-bottom: 24px; }
        .mb-4 { margin-bottom: 32px; }
        .mt-3 { margin-top: 24px; }
        .mt-4 { margin-top: 32px; }
        .text-center { text-align: center; }
        .text-end { text-align: left; } /* RTL adjustment */
        .text-muted { color: var(--md-on-surface-variant); }
        .w-100 { width: 100%; }
        .d-none { display: none; }
        .d-flex { display: flex; }
        .justify-content-between { justify-content: space-between; }
        .align-items-center { align-items: center; }

        /* Grid System */
        .row {
            display: flex;
            flex-wrap: wrap;
            margin: -12px;
        }

        .row > * {
            padding: 12px;
        }

        .col-md-4 {
            flex: 0 0 33.333333%;
            max-width: 33.333333%;
        }

        .col-12 {
            flex: 0 0 100%;
            max-width: 100%;
        }

        @media (max-width: 768px) {
            .col-md-4 {
                flex: 0 0 100%;
                max-width: 100%;
            }
            
            body {
                padding: 16px;
            }
            
            .auth-card {
                margin: 20px auto;
                max-width: 100%;
            }
            
            .navbar-custom {
                padding: 20px;
                flex-direction: column;
                gap: 16px;
            }
            
            .stat-card {
                padding: 24px;
            }
        }

        /* RTL Specific Adjustments */
        [dir="rtl"] .text-end {
            text-align: right;
        }

        /* Loading Animation */
        .loading {
            opacity: 0.6;
            pointer-events: none;
        }

        /* Focus Management */
        .btn:focus-visible {
            outline: 2px solid var(--md-primary);
            outline-offset: 2px;
        }

        .form-control:focus-visible {
            outline: none;
        }

        /* Accessibility */
        .visually-hidden {
            position: absolute !important;
            width: 1px !important;
            height: 1px !important;
            padding: 0 !important;
            margin: -1px !important;
            overflow: hidden !important;
            clip: rect(0, 0, 0, 0) !important;
            white-space: nowrap !important;
            border: 0 !important;
        }

        /* High contrast mode support */
        @media (prefers-contrast: high) {
            .btn {
                border: 2px solid currentColor;
            }
            
            .form-control {
                border: 2px solid currentColor;
            }
            
            .stat-card {
                border: 2px solid var(--md-outline);
            }
        }

        /* Reduce motion for users who prefer it */
        @media (prefers-reduced-motion: reduce) {
            * {
                animation-duration: 0.01ms !important;
                animation-iteration-count: 1 !important;
                transition-duration: 0.01ms !important;
            }
        }

        /* Better focus indicators */
        *:focus-visible {
            outline: 2px solid var(--md-primary);
            outline-offset: 2px;
        }

        /* Notification System */
        .notification {
            position: fixed;
            top: 24px;
            right: 24px;
            z-index: 1000;
            max-width: 400px;
            background: var(--md-surface);
            border-radius: 16px;
            box-shadow: var(--md-elevation-3);
            border: 1px solid var(--md-outline-variant);
            animation: slideInRight 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            overflow: hidden;
        }

        .notification-content {
            padding: 16px 20px;
            display: flex;
            align-items: center;
            gap: 12px;
            position: relative;
        }

        .notification-success {
            border-left: 4px solid var(--md-success);
        }

        .notification-error {
            border-left: 4px solid var(--md-error);
        }

        .notification-warning {
            border-left: 4px solid var(--md-warning);
        }

        .notification-info {
            border-left: 4px solid var(--md-info);
        }

        .notification-success .fas {
            color: var(--md-success);
        }

        .notification-error .fas {
            color: var(--md-error);
        }

        .notification-warning .fas {
            color: var(--md-warning);
        }

        .notification-info .fas {
            color: var(--md-info);
        }

        .notification-close {
            background: none;
            border: none;
            color: var(--md-on-surface-variant);
            cursor: pointer;
            padding: 4px;
            border-radius: 50%;
            transition: background-color 0.2s ease;
            margin-right: auto;
        }

        .notification-close:hover {
            background: var(--md-surface-variant);
        }

        @keyframes slideInRight {
            from {
                opacity: 0;
                transform: translateX(100%);
            }
            to {
                opacity: 1;
                transform: translateX(0);
            }
        }

        /* Loading spinner */
        .fa-spinner {
            animation: spin 1s linear infinite;
        }

        @keyframes spin {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
        }

        /* Enhanced hover effects */
        .stat-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 3px;
            background: linear-gradient(90deg, var(--md-primary), var(--md-accent));
            transform: scaleX(0);
            transition: transform 0.3s ease;
        }

        .stat-card:hover::before {
            transform: scaleX(1);
        }
    </style>
</head>
<body>
    <div id="app"></div>

    <script>
        const API_URL = 'http://localhost:8001';
        let token = localStorage.getItem('token');
        let timerInterval;

        // Render functions
        function renderLogin() {
            document.getElementById('app').innerHTML = `
                <div class="auth-card">
                    <div class="auth-header">
                        <h1><i class="fas fa-shield-alt"></i> شاپرک</h1>
                        <p>پلتفرم تحلیل داده امن</p>
                    </div>
                    <div class="auth-body">
                        <form id="loginForm">
                            <div class="mb-3">
                                <label for="username" class="form-label">نام کاربری</label>
                                <input type="text" class="form-control" id="username" name="username" required 
                                       aria-describedby="username-help" autocomplete="username">
                                <small id="username-help" class="form-text text-muted">نام کاربری خود را وارد کنید</small>
                            </div>
                            <div class="mb-3">
                                <label for="password" class="form-label">رمز عبور</label>
                                <input type="password" class="form-control" id="password" name="password" required 
                                       aria-describedby="password-help" autocomplete="current-password">
                                <small id="password-help" class="form-text text-muted">رمز عبور خود را وارد کنید</small>
                            </div>
                            <button type="submit" class="btn btn-primary w-100" aria-label="ورود به سیستم">ورود</button>
                        </form>
                        <div class="alert alert-danger mt-3 d-none" id="error-msg"></div>
                        <div class="text-center mt-3">
                            <p>حساب کاربری ندارید؟ <a href="#" class="btn-link" onclick="showRegister(); return false;">ثبت‌نام</a></p>
                            <small class="text-muted">کاربر دمو: ali.rezaei / shaparak123</small>
                        </div>
                    </div>
                </div>
            `;

            document.getElementById('loginForm').addEventListener('submit', handleLogin);
        }

        function renderRegister() {
            document.getElementById('app').innerHTML = `
                <div class="auth-card">
                    <div class="auth-header">
                        <h1><i class="fas fa-user-plus"></i> ثبت‌نام</h1>
                        <p>ایجاد حساب کاربری جدید</p>
                    </div>
                    <div class="auth-body">
                        <form id="registerForm">
                            <div class="mb-3">
                                <label for="reg_username" class="form-label">نام کاربری</label>
                                <input type="text" class="form-control" id="reg_username" name="username" required 
                                       pattern="[a-z0-9._-]{3,20}" aria-describedby="reg_username-help" autocomplete="username">
                                <small id="reg_username-help" class="text-muted">فقط حروف انگلیسی کوچک، اعداد، نقطه و خط تیره (3-20 کاراکتر)</small>
                            </div>
                            <div class="mb-3">
                                <label for="reg_email" class="form-label">ایمیل</label>
                                <input type="email" class="form-control" id="reg_email" name="email" required 
                                       aria-describedby="reg_email-help" autocomplete="email">
                                <small id="reg_email-help" class="text-muted">آدرس ایمیل معتبر وارد کنید</small>
                            </div>
                            <div class="mb-3">
                                <label for="reg_fullname" class="form-label">نام و نام خانوادگی</label>
                                <input type="text" class="form-control" id="reg_fullname" name="fullname" required 
                                       aria-describedby="reg_fullname-help" autocomplete="name">
                                <small id="reg_fullname-help" class="text-muted">نام کامل خود را وارد کنید</small>
                            </div>
                            <div class="mb-3">
                                <label for="reg_org" class="form-label">سازمان</label>
                                <input type="text" class="form-control" id="reg_org" name="organization" 
                                       aria-describedby="reg_org-help" autocomplete="organization">
                                <small id="reg_org-help" class="text-muted">نام سازمان یا شرکت خود را وارد کنید (اختیاری)</small>
                            </div>
                            <div class="mb-3">
                                <label for="reg_password" class="form-label">رمز عبور</label>
                                <input type="password" class="form-control" id="reg_password" name="password" required 
                                       minlength="8" aria-describedby="reg_password-help" autocomplete="new-password">
                                <small id="reg_password-help" class="text-muted">حداقل 8 کاراکتر - ترکیبی از حروف، اعداد و علائم</small>
                            </div>
                            <button type="submit" class="btn btn-primary w-100" aria-label="ثبت‌نام در سیستم">ثبت‌نام</button>
                        </form>
                        <div class="alert alert-danger mt-3 d-none" id="error-msg"></div>
                        <div class="alert alert-success mt-3 d-none" id="success-msg"></div>
                        <div class="text-center mt-3">
                            <p>قبلاً ثبت‌نام کرده‌اید؟ <a href="#" class="btn-link" onclick="showLogin(); return false;">ورود</a></p>
                        </div>
                    </div>
                </div>
            `;

            document.getElementById('registerForm').addEventListener('submit', handleRegister);
        }

        function renderDashboard(data) {
            const hours = Math.floor(data.session_remaining_seconds / 3600);
            const minutes = Math.floor((data.session_remaining_seconds % 3600) / 60);
            const seconds = data.session_remaining_seconds % 60;

            document.getElementById('app').innerHTML = `
                <div class="dashboard" role="main">
                    <nav class="navbar-custom d-flex justify-content-between align-items-center" role="navigation" aria-label="ناوبری اصلی">
                        <div>
                            <h3 class="mb-0"><i class="fas fa-user-circle" aria-hidden="true"></i> ${data.user.full_name}</h3>
                            <small class="text-muted">${data.user.email}</small>
                        </div>
                        <div class="text-end">
                            <div class="timer" id="session-timer" role="timer" aria-live="polite" aria-label="زمان باقیمانده جلسه">${String(hours).padStart(2,'0')}:${String(minutes).padStart(2,'0')}:${String(seconds).padStart(2,'0')}</div>
                            <small>زمان باقیمانده جلسه</small>
                        </div>
                        <button class="btn btn-danger" onclick="logout()" aria-label="خروج از سیستم">خروج</button>
                    </nav>

                    <section class="row" role="region" aria-labelledby="stats-heading">
                        <h2 id="stats-heading" class="visually-hidden">آمار عملکرد</h2>
                        <div class="col-md-4">
                            <div class="stat-card" role="article" aria-labelledby="today-executions">
                                <h5 id="today-executions"><i class="fas fa-play-circle" aria-hidden="true"></i> اجرا امروز</h5>
                                <div class="stat-value" aria-label="${data.stats.today_executions} اجرا در امروز">${data.stats.today_executions}</div>
                            </div>
                        </div>
                        <div class="col-md-4">
                            <div class="stat-card" role="article" aria-labelledby="total-executions">
                                <h5 id="total-executions"><i class="fas fa-chart-line" aria-hidden="true"></i> مجموع اجرا</h5>
                                <div class="stat-value" aria-label="${data.stats.total_executions} اجرای کل">${data.stats.total_executions}</div>
                            </div>
                        </div>
                        <div class="col-md-4">
                            <div class="stat-card" role="article" aria-labelledby="success-rate">
                                <h5 id="success-rate"><i class="fas fa-check-circle" aria-hidden="true"></i> نرخ موفقیت</h5>
                                <div class="stat-value" aria-label="نرخ موفقیت ${data.stats.success_rate} درصد">${data.stats.success_rate}%</div>
                            </div>
                        </div>
                    </section>

                    <div class="stat-card text-center">
                        <h4 class="mb-4"><i class="fas fa-rocket"></i> دسترسی به Jupyter Notebook</h4>
                        <button id="launch-jupyter" class="btn btn-primary btn-lg px-5" onclick="launchJupyter()">
                            <i class="fas fa-play"></i> راه‌اندازی Jupyter Lab
                        </button>
                        <p class="mt-3 text-muted">
                            <i class="fas fa-exclamation-triangle"></i>
                            تمام کدها ثبت می‌شود | دانلود فایل و نصب پکیج مجاز نیست
                        </p>
                    </div>
                </div>
            `;

            startTimer(data.session_remaining_seconds);
        }

        // Event handlers
        async function handleLogin(e) {
            e.preventDefault();
            const submitButton = e.target.querySelector('button[type="submit"]');
            const username = document.getElementById('username').value;
            const password = document.getElementById('password').value;

            // Clear previous errors
            const errorDiv = document.getElementById('error-msg');
            if (errorDiv) errorDiv.classList.add('d-none');

            setLoading(submitButton, true);

            try {
                const formData = new FormData();
                formData.append('username', username);
                formData.append('password', password);

                const response = await fetch(`${API_URL}/api/token`, {
                    method: 'POST',
                    body: formData
                });

                if (response.ok) {
                    const data = await response.json();
                    token = data.access_token;
                    localStorage.setItem('token', token);
                    showNotification('ورود با موفقیت انجام شد', 'success');
                    setTimeout(() => loadDashboard(), 1000);
                } else {
                    const error = await response.json();
                    showError(error.detail || 'نام کاربری یا رمز عبور اشتباه است');
                }
            } catch (error) {
                showError('خطا در برقراری ارتباط با سرور');
            } finally {
                setLoading(submitButton, false);
            }
        }

        async function handleRegister(e) {
            e.preventDefault();
            const submitButton = e.target.querySelector('button[type="submit"]');
            const data = {
                username: document.getElementById('reg_username').value,
                email: document.getElementById('reg_email').value,
                full_name: document.getElementById('reg_fullname').value,
                organization: document.getElementById('reg_org').value,
                password: document.getElementById('reg_password').value
            };

            // Clear previous messages
            const errorDiv = document.getElementById('error-msg');
            const successDiv = document.getElementById('success-msg');
            if (errorDiv) errorDiv.classList.add('d-none');
            if (successDiv) successDiv.classList.add('d-none');

            setLoading(submitButton, true);

            try {
                const response = await fetch(`${API_URL}/api/register`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });

                if (response.ok) {
                    const result = await response.json();
                    showNotification('ثبت‌نام با موفقیت انجام شد. در حال انتقال به صفحه ورود...', 'success');
                    if (successDiv) {
                        successDiv.textContent = result.message;
                        successDiv.classList.remove('d-none');
                    }
                    setTimeout(() => showLogin(), 2000);
                } else {
                    const error = await response.json();
                    showError(error.detail || 'خطا در ثبت‌نام');
                }
            } catch (error) {
                showError('خطا در برقراری ارتباط با سرور');
            } finally {
                setLoading(submitButton, false);
            }
        }

        async function loadDashboard() {
            try {
                const response = await fetch(`${API_URL}/api/dashboard`, {
                    headers: { 'Authorization': `Bearer ${token}` }
                });

                if (response.ok) {
                    const data = await response.json();
                    renderDashboard(data);
                } else {
                    localStorage.removeItem('token');
                    showLogin();
                }
            } catch (error) {
                showError('خطا در دریافت اطلاعات');
            }
        }

        async function launchJupyter() {
            const launchButton = document.getElementById('launch-jupyter');
            if (launchButton) setLoading(launchButton, true);

            try {
                const response = await fetch(`${API_URL}/api/jupyter/launch`, {
                    method: 'POST',
                    headers: { 'Authorization': `Bearer ${token}` }
                });

                if (response.ok) {
                    const data = await response.json();
                    showNotification('Jupyter Lab در حال بارگذاری...', 'success');
                    // Open directly after a short delay
                    setTimeout(() => {
                        window.open(`http://localhost:8000${data.url}`, '_blank');
                    }, 1000);
                } else {
                    const error = await response.json();
                    showNotification('خطا: ' + (error.detail || 'خطا در راه‌اندازی Jupyter Lab'), 'error');
                }
            } catch (error) {
                showNotification('خطا در برقراری ارتباط با سرور', 'error');
            } finally {
                if (launchButton) {
                    setTimeout(() => setLoading(launchButton, false), 1000);
                }
            }
        }

        function startTimer(remainingSeconds) {
            let remaining = remainingSeconds;
            timerInterval = setInterval(() => {
                remaining--;
                if (remaining <= 0) {
                    showNotification('جلسه شما منقضی شد', 'error');
                    logout();
                    return;
                }

                const hours = Math.floor(remaining / 3600);
                const minutes = Math.floor((remaining % 3600) / 60);
                const seconds = remaining % 60;

                const timerEl = document.getElementById('session-timer');
                if (timerEl) {
                    timerEl.textContent = `${String(hours).padStart(2,'0')}:${String(minutes).padStart(2,'0')}:${String(seconds).padStart(2,'0')}`;
                    
                    // Add warning animation for low time
                    if (remaining < 300) { // 5 minutes
                        timerEl.classList.add('warning');
                        if (remaining === 299) {
                            showNotification('توجه: 5 دقیقه تا پایان جلسه باقی مانده است', 'warning');
                        }
                    } else {
                        timerEl.classList.remove('warning');
                    }
                    
                    // Warning at 1 minute
                    if (remaining === 60) {
                        showNotification('توجه: 1 دقیقه تا پایان جلسه باقی مانده است', 'error');
                    }
                }
            }, 1000);
        }

        function logout() {
            clearInterval(timerInterval);
            localStorage.removeItem('token');
            token = null;
            showLogin();
        }

        function showLogin() {
            clearInterval(timerInterval);
            renderLogin();
        }

        function showRegister() {
            renderRegister();
        }

        function showError(msg) {
            const errorDiv = document.getElementById('error-msg');
            if (errorDiv) {
                errorDiv.textContent = msg;
                errorDiv.classList.remove('d-none');
                setTimeout(() => {
                    errorDiv.classList.add('d-none');
                }, 5000);
            }
        }

        // Modern notification system
        function showNotification(message, type = 'info', duration = 4000) {
            // Remove existing notifications
            const existing = document.querySelector('.notification');
            if (existing) existing.remove();

            const notification = document.createElement('div');
            notification.className = `notification notification-${type}`;
            notification.setAttribute('role', 'alert');
            notification.setAttribute('aria-live', 'polite');
            notification.setAttribute('aria-atomic', 'true');
            notification.innerHTML = `
                <div class="notification-content">
                    <i class="fas ${getNotificationIcon(type)}" aria-hidden="true"></i>
                    <span>${message}</span>
                    <button onclick="this.parentElement.parentElement.remove()" class="notification-close" aria-label="بستن پیام">
                        <i class="fas fa-times" aria-hidden="true"></i>
                    </button>
                </div>
            `;
            
            document.body.appendChild(notification);
            
            // Auto remove
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.style.opacity = '0';
                    notification.style.transform = 'translateX(-100%)';
                    setTimeout(() => notification.remove(), 300);
                }
            }, duration);
        }

        function getNotificationIcon(type) {
            switch(type) {
                case 'success': return 'fa-check-circle';
                case 'error': return 'fa-exclamation-circle';
                case 'warning': return 'fa-exclamation-triangle';
                default: return 'fa-info-circle';
            }
        }

        function setLoading(element, loading) {
            if (loading) {
                element.classList.add('loading');
                element.disabled = true;
                const originalText = element.textContent;
                element.setAttribute('data-original-text', originalText);
                element.innerHTML = '<i class="fas fa-spinner fa-spin"></i> در حال بارگذاری...';
            } else {
                element.classList.remove('loading');
                element.disabled = false;
                const originalText = element.getAttribute('data-original-text');
                if (originalText) {
                    element.textContent = originalText;
                }
            }
        }

        // Initialize
        if (token) {
            loadDashboard();
        } else {
            renderLogin();
        }
    </script>
</body>
</html>
    """

@app.get("/", tags=["Root"])
async def root():
    return {
        "service": "Shaparak Data Platform API",
        "version": "1.0.0",
        "docs": "/docs",
        "status": "running"
    }

@app.get("/health", tags=["Root"])
async def health_check():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_status = "connected"
    except:
        db_status = "disconnected"
    
    return {
        "status": "healthy",
        "database": db_status,
        "timestamp": datetime.utcnow().isoformat()
    }

@app.post("/api/register", response_model=MessageResponse, status_code=201, tags=["Authentication"])
async def register(user: UserRegister):
    """
    ثبت‌نام کاربر جدید
    
    - **username**: نام کاربری (فقط حروف انگلیسی کوچک، اعداد، نقطه، خط تیره)
    - **email**: ایمیل معتبر
    - **password**: رمز عبور (حداقل 8 کاراکتر)
    - **full_name**: نام و نام خانوادگی
    - **organization**: سازمان (اختیاری)
    """
    
    # Check if username or email already exists
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT username, email FROM portal_users WHERE username = :username OR email = :email"),
            {"username": user.username, "email": user.email}
        )
        existing = result.fetchone()
    
    if existing:
        if existing[0] == user.username:
            raise HTTPException(status_code=400, detail="این نام کاربری قبلاً استفاده شده است")
        else:
            raise HTTPException(status_code=400, detail="این ایمیل قبلاً ثبت شده است")
    
    # Hash password
    hashed_password = pwd_context.hash(user.password)
    
    try:
        # Insert into database
        with engine.connect() as conn:
            conn.execute(
                text("""
                    INSERT INTO portal_users (username, email, full_name, organization, hashed_password, is_active)
                    VALUES (:username, :email, :full_name, :org, :password, TRUE)
                """),
                {
                    "username": user.username,
                    "email": user.email,
                    "full_name": user.full_name,
                    "org": user.organization,
                    "password": hashed_password
                }
            )
            conn.commit()
        
        # Create user in JupyterHub
        response = await call_jupyterhub_api(
            "POST",
            f"/users/{user.username}",
            json_data={"admin": False}
        )
        if response:
            if response.status_code in [201, 200]:
                print(f"Successfully created JupyterHub user: {user.username}")
            elif response.status_code == 409:
                print(f"JupyterHub user already exists: {user.username}")
            else:
                print(f"Warning: JupyterHub user creation failed with status {response.status_code}: {response.text}")
        else:
            print(f"Warning: Could not connect to JupyterHub to create user")
        
        return MessageResponse(
            message="ثبت‌نام با موفقیت انجام شد. اکنون می‌توانید وارد شوید.",
            details={"username": user.username}
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطا در ثبت‌نام: {str(e)}")

@app.post("/api/token", response_model=Token, tags=["Authentication"])
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    ورود به سیستم و دریافت توکن دسترسی
    
    توکن به مدت 8 ساعت معتبر است.
    """
    
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT username, hashed_password, is_active, full_name FROM portal_users WHERE username = :username"),
            {"username": form_data.username}
        )
        user = result.fetchone()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="نام کاربری یا رمز عبور اشتباه است",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user[2]:  # is_active
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="حساب کاربری شما غیرفعال شده است. با مدیر سیستم تماس بگیرید."
        )
    
    if not pwd_context.verify(form_data.password, user[1]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="نام کاربری یا رمز عبور اشتباه است",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Update last login
    with engine.connect() as conn:
        conn.execute(
            text("UPDATE portal_users SET last_login = CURRENT_TIMESTAMP WHERE username = :username"),
            {"username": form_data.username}
        )
        conn.commit()
    
    # Create access token
    access_token = create_access_token(
        data={"sub": form_data.username},
        expires_delta=timedelta(hours=8)
    )
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=28800,  # 8 hours
        username=user[0],
        full_name=user[3]
    )

@app.get("/api/me", response_model=UserInfo, tags=["Users"])
async def get_current_user_info(current_user: UserInfo = Depends(get_current_user)):
    """دریافت اطلاعات کاربر جاری"""
    return current_user

@app.get("/api/dashboard", response_model=DashboardResponse, tags=["Dashboard"])
async def get_dashboard(current_user: UserInfo = Depends(get_current_user), token: str = Depends(oauth2_scheme)):
    """
    دریافت اطلاعات داشبورد کاربر
    
    شامل:
    - اطلاعات کاربر
    - زمان باقیمانده جلسه
    - وضعیت Jupyter
    - آمار استفاده
    """
    
    # Get token expiration
    payload = verify_token(token)
    exp_timestamp = payload.get("exp")
    remaining_seconds = max(0, int(exp_timestamp - datetime.utcnow().timestamp()))
    
    # Get JupyterHub status
    jupyter_status = {"status": "unknown"}
    response = await call_jupyterhub_api("GET", f"/users/{current_user.username}", timeout=5.0)
    
    if response:
        if response.status_code == 200:
            user_data = response.json()
            jupyter_status = {
                "status": "available",
                "username": user_data.get("name"),
                "servers": user_data.get("servers", {}),
                "server_active": bool(user_data.get("servers"))
            }
        elif response.status_code == 404:
            # User not found in JupyterHub, try to create
            create_response = await call_jupyterhub_api(
                "POST",
                f"/users/{current_user.username}",
                json_data={"admin": False}
            )
            if create_response and create_response.status_code in [200, 201]:
                jupyter_status = {"status": "created", "server_active": False}
            else:
                jupyter_status = {"status": "error", "message": "Failed to create user"}
        else:
            jupyter_status = {"status": "error", "code": response.status_code}
    else:
        jupyter_status = {"status": "unavailable", "error": "Connection failed"}
    
    # Get usage statistics
    with engine.connect() as conn:
        result = conn.execute(
            text("""
                SELECT 
                    COUNT(*) as total_executions,
                    COUNT(CASE WHEN DATE(timestamp) = CURRENT_DATE THEN 1 END) as today_executions,
                    COUNT(CASE WHEN status = 'error' THEN 1 END) as total_errors,
                    AVG(execution_time_ms) as avg_execution_time,
                    MAX(timestamp) as last_execution
                FROM code_execution_logs
                WHERE username = :username
            """),
            {"username": current_user.username}
        )
        stats_row = result.fetchone()
        stats = {
            "total_executions": stats_row[0] or 0,
            "today_executions": stats_row[1] or 0,
            "total_errors": stats_row[2] or 0,
            "success_rate": round((1 - (stats_row[2] or 0) / max(stats_row[0] or 1, 1)) * 100, 1),
            "avg_execution_time_ms": round(stats_row[3] or 0, 2),
            "last_execution": stats_row[4].isoformat() if stats_row[4] else None
        }
    
    return DashboardResponse(
        user=current_user,
        session_remaining_seconds=remaining_seconds,
        jupyter_status=jupyter_status,
        stats=stats
    )

@app.post("/api/jupyter/launch", response_model=JupyterLaunchResponse, tags=["Jupyter"])
async def launch_jupyter(current_user: UserInfo = Depends(get_current_user)):
    """
    راه‌اندازی Jupyter Notebook
    
    اگر سرور قبلاً در حال اجرا باشد، URL آن را برمی‌گرداند.
    با استفاده از توکن احراز هویت برای دسترسی مستقیم.
    """
    
    # First, ensure user exists in JupyterHub
    check_response = await call_jupyterhub_api("GET", f"/users/{current_user.username}", timeout=30.0)
    
    if not check_response:
        raise HTTPException(
            status_code=503,
            detail="خطا در اتصال به JupyterHub. لطفاً مجدداً تلاش کنید."
        )
    
    if check_response.status_code == 404:
        # User doesn't exist, create them
        create_response = await call_jupyterhub_api(
            "POST",
            f"/users/{current_user.username}",
            json_data={"admin": False},
            timeout=30.0
        )
        if not create_response or create_response.status_code not in [200, 201]:
            raise HTTPException(
                status_code=500, 
                detail=f"خطا در ایجاد کاربر JupyterHub"
            )
    elif check_response.status_code == 200:
        # User exists, check if server is already running
        user_info = check_response.json()
        servers = user_info.get("servers", {})
        
        # Check default server (unnamed server)
        if "" in servers:
            server_info = servers[""]
            if server_info.get("ready"):
                # Generate auth token for direct access
                token_response = await call_jupyterhub_api(
                    "POST",
                    f"/users/{current_user.username}/tokens",
                    json_data={"expires_in": 3600, "note": "Portal access token"},
                    timeout=10.0
                )
                if token_response and token_response.status_code == 200:
                    token_data = token_response.json()
                    token = token_data.get("token")
                    return JupyterLaunchResponse(
                        status="running",
                        url=f"/user/{current_user.username}/lab?token={token}",
                        message="Jupyter Lab در حال اجرا است"
                    )
                else:
                    # Fallback without token
                    return JupyterLaunchResponse(
                        status="running",
                        url=f"/user/{current_user.username}/lab",
                        message="Jupyter Lab در حال اجرا است"
                    )
            elif server_info.get("pending"):
                return JupyterLaunchResponse(
                    status="starting",
                    url=f"/user/{current_user.username}/lab",
                    message="Jupyter Lab در حال راه‌اندازی است... لطفاً صبر کنید."
                )
    else:
        raise HTTPException(
            status_code=500,
            detail=f"خطا در بررسی وضعیت کاربر: {check_response.status_code}"
        )
    
    # Start the server
    start_response = await call_jupyterhub_api(
        "POST",
        f"/users/{current_user.username}/server",
        timeout=30.0
    )
    
    if not start_response:
        raise HTTPException(
            status_code=503,
            detail="خطا در اتصال به JupyterHub برای راه‌اندازی سرور"
        )
    
    if start_response.status_code in [200, 201, 202]:
        # Generate auth token for when server is ready
        token_response = await call_jupyterhub_api(
            "POST",
            f"/users/{current_user.username}/tokens",
            json_data={"expires_in": 3600, "note": "Portal access token"},
            timeout=10.0
        )
        
        if token_response and token_response.status_code == 200:
            token_data = token_response.json()
            token = token_data.get("token")
            return JupyterLaunchResponse(
                status="starting",
                url=f"/user/{current_user.username}/lab?token={token}",
                message="Jupyter Lab در حال راه‌اندازی است... لطفاً 30 ثانیه صبر کنید."
            )
        else:
            # Fallback without token
            return JupyterLaunchResponse(
                status="starting",
                url=f"/user/{current_user.username}/lab",
                message="Jupyter Lab در حال راه‌اندازی است... لطفاً 30 ثانیه صبر کنید."
            )
    elif start_response.status_code == 400:
        # Server might already be starting
        return JupyterLaunchResponse(
            status="starting",
            url=f"/user/{current_user.username}/lab",
            message="Jupyter Lab در حال راه‌اندازی است... لطفاً صبر کنید."
        )
    else:
        error_detail = start_response.text
        raise HTTPException(
            status_code=500,
            detail=f"خطا در راه‌اندازی Jupyter: {start_response.status_code} - {error_detail}"
        )

@app.get("/api/audit-logs", tags=["Audit"])
async def get_audit_logs(
    current_user: UserInfo = Depends(get_current_user),
    limit: int = 50,
    offset: int = 0
):
    """
    دریافت لاگ‌های اجرای کد
    
    - **limit**: تعداد رکوردها (پیش‌فرض: 50)
    - **offset**: شروع از رکورد (پیش‌فرض: 0)
    """
    
    with engine.connect() as conn:
        result = conn.execute(
            text("""
                SELECT 
                    id,
                    timestamp,
                    cell_number,
                    LEFT(code, 100) as code_preview,
                    execution_time_ms,
                    status,
                    LEFT(error_message, 200) as error_preview
                FROM code_execution_logs
                WHERE username = :username
                ORDER BY timestamp DESC
                LIMIT :limit OFFSET :offset
            """),
            {"username": current_user.username, "limit": limit, "offset": offset}
        )
        logs = [
            {
                "id": row[0],
                "timestamp": row[1].isoformat() if row[1] else None,
                "cell_number": row[2],
                "code_preview": row[3],
                "execution_time_ms": row[4],
                "status": row[5],
                "error_preview": row[6]
            }
            for row in result.fetchall()
        ]
    
    return {"logs": logs, "count": len(logs)}

@app.get("/api/activity/recent", tags=["Activity"])
async def get_recent_activity(
    limit: int = 10,
    current_user: UserInfo = Depends(get_current_user)
):
    """
    دریافت آخرین فعالیت‌های کاربر
    
    نمایش آخرین کدهای اجرا شده با جزئیات کامل
    """
    with engine.connect() as conn:
        result = conn.execute(
            text("""
                SELECT 
                    id,
                    timestamp,
                    cell_number,
                    code,
                    execution_time_ms,
                    status,
                    error_message
                FROM code_execution_logs
                WHERE username = :username
                ORDER BY timestamp DESC
                LIMIT :limit
            """),
            {"username": current_user.username, "limit": limit}
        )
        activities = [
            {
                "id": row[0],
                "timestamp": row[1].isoformat() if row[1] else None,
                "cell_number": row[2],
                "code": row[3],
                "execution_time_ms": row[4],
                "status": row[5],
                "error_message": row[6]
            }
            for row in result.fetchall()
        ]
    
    return {"activities": activities, "count": len(activities)}

@app.get("/api/activity/stats", tags=["Activity"])
async def get_activity_stats(
    days: int = 7,
    current_user: UserInfo = Depends(get_current_user)
):
    """
    دریافت آمار فعالیت در بازه زمانی
    
    آمار روزانه اجرای کد در N روز گذشته
    """
    with engine.connect() as conn:
        result = conn.execute(
            text("""
                SELECT 
                    DATE(timestamp) as date,
                    COUNT(*) as executions,
                    COUNT(CASE WHEN status = 'success' THEN 1 END) as success_count,
                    COUNT(CASE WHEN status = 'error' THEN 1 END) as error_count,
                    AVG(execution_time_ms) as avg_time
                FROM code_execution_logs
                WHERE username = :username
                AND timestamp >= CURRENT_DATE - INTERVAL ':days days'
                GROUP BY DATE(timestamp)
                ORDER BY date DESC
            """),
            {"username": current_user.username, "days": days}
        )
        daily_stats = [
            {
                "date": row[0].isoformat() if row[0] else None,
                "executions": row[1],
                "success_count": row[2],
                "error_count": row[3],
                "avg_time_ms": round(row[4] or 0, 2)
            }
            for row in result.fetchall()
        ]
    
    return {"daily_stats": daily_stats, "period_days": days}

@app.get("/api/activity/search", tags=["Activity"])
async def search_code(
    query: str,
    limit: int = 20,
    current_user: UserInfo = Depends(get_current_user)
):
    """
    جستجو در کدهای اجرا شده
    
    جستجوی متن در تاریخچه کدهای اجرا شده
    """
    if len(query) < 2:
        raise HTTPException(
            status_code=400,
            detail="حداقل 2 کاراکتر برای جستجو نیاز است"
        )
    
    with engine.connect() as conn:
        result = conn.execute(
            text("""
                SELECT 
                    id,
                    timestamp,
                    cell_number,
                    code,
                    execution_time_ms,
                    status
                FROM code_execution_logs
                WHERE username = :username 
                AND code ILIKE :query
                ORDER BY timestamp DESC
                LIMIT :limit
            """),
            {"username": current_user.username, "query": f"%{query}%", "limit": limit}
        )
        results = [
            {
                "id": row[0],
                "timestamp": row[1].isoformat() if row[1] else None,
                "cell_number": row[2],
                "code": row[3],
                "execution_time_ms": row[4],
                "status": row[5]
            }
            for row in result.fetchall()
        ]
    
    return {"results": results, "query": query, "count": len(results)}

@app.get("/api/admin/all-users-activity", tags=["Admin"])
async def get_all_users_activity(
    current_user: UserInfo = Depends(get_current_user)
):
    """
    دریافت فعالیت تمام کاربران (فقط ادمین)
    
    نمای کلی از فعالیت تمام کاربران سیستم
    """
    # Check if user is admin
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT is_admin FROM portal_users WHERE username = :username"),
            {"username": current_user.username}
        )
        user = result.fetchone()
        if not user or not user[0]:
            raise HTTPException(
                status_code=403,
                detail="دسترسی محدود به مدیران سیستم"
            )
    
    # Get all users activity
    with engine.connect() as conn:
        result = conn.execute(
            text("""
                SELECT 
                    username,
                    COUNT(*) as total_executions,
                    COUNT(CASE WHEN DATE(timestamp) = CURRENT_DATE THEN 1 END) as today_executions,
                    COUNT(CASE WHEN status = 'error' THEN 1 END) as error_count,
                    AVG(execution_time_ms) as avg_time,
                    MAX(timestamp) as last_active
                FROM code_execution_logs
                GROUP BY username
                ORDER BY last_active DESC
            """)
        )
        all_activity = [
            {
                "username": row[0],
                "total_executions": row[1],
                "today_executions": row[2],
                "error_count": row[3],
                "avg_time_ms": round(row[4] or 0, 2),
                "last_active": row[5].isoformat() if row[5] else None
            }
            for row in result.fetchall()
        ]
    
    return {"users_activity": all_activity, "total_users": len(all_activity)}

@app.get("/api/admin/system-stats", tags=["Admin"])
async def get_system_stats(
    current_user: UserInfo = Depends(get_current_user)
):
    """
    دریافت آمار کلی سیستم (فقط ادمین)
    
    آمار جامع استفاده از سیستم
    """
    # Check if user is admin
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT is_admin FROM portal_users WHERE username = :username"),
            {"username": current_user.username}
        )
        user = result.fetchone()
        if not user or not user[0]:
            raise HTTPException(
                status_code=403,
                detail="دسترسی محدود به مدیران سیستم"
            )
    
    # Get system-wide statistics
    with engine.connect() as conn:
        # Total stats
        result = conn.execute(
            text("""
                SELECT 
                    COUNT(*) as total_executions,
                    COUNT(DISTINCT username) as active_users,
                    COUNT(CASE WHEN DATE(timestamp) = CURRENT_DATE THEN 1 END) as today_executions,
                    COUNT(CASE WHEN status = 'error' THEN 1 END) as total_errors,
                    AVG(execution_time_ms) as avg_execution_time
                FROM code_execution_logs
            """)
        )
        stats_row = result.fetchone()
        
        # Top users
        top_users_result = conn.execute(
            text("""
                SELECT username, COUNT(*) as execution_count
                FROM code_execution_logs
                GROUP BY username
                ORDER BY execution_count DESC
                LIMIT 5
            """)
        )
        top_users = [{"username": row[0], "executions": row[1]} for row in top_users_result.fetchall()]
        
        # Recent errors
        errors_result = conn.execute(
            text("""
                SELECT username, timestamp, LEFT(code, 100) as code_preview, LEFT(error_message, 200) as error
                FROM code_execution_logs
                WHERE status = 'error'
                ORDER BY timestamp DESC
                LIMIT 10
            """)
        )
        recent_errors = [
            {
                "username": row[0],
                "timestamp": row[1].isoformat() if row[1] else None,
                "code_preview": row[2],
                "error": row[3]
            }
            for row in errors_result.fetchall()
        ]
    
    return {
        "total_executions": stats_row[0] or 0,
        "active_users": stats_row[1] or 0,
        "today_executions": stats_row[2] or 0,
        "total_errors": stats_row[3] or 0,
        "avg_execution_time_ms": round(stats_row[4] or 0, 2),
        "top_users": top_users,
        "recent_errors": recent_errors
    }