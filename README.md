# Secure Login System with RBAC (Flask + MySQL)

A security-focused web application for internship evaluation. It includes secure authentication, role-based authorization, CAPTCHA, account lockout, and admin user management.

## Features

- User registration and login
- Password hashing with Argon2 (`passlib`)
- JWT authentication using HttpOnly cookies
- Role-based access control (`admin`, `user`)
- Admin dashboard for user management
- Dedicated admin-only Add Users page (`/admin/users/add`)
- Admin delete action for both user/admin accounts with last-admin protection
- Turnstile CAPTCHA with local math fallback
- Account lockout after repeated failed attempts
- CSRF protection on all forms
- Audit logging for auth/admin operations
- Profile center with avatar upload, editable identity fields, and password change
- Read-only members directory for all logged-in users (shows who is admin/user)
- Client-side + server-side validation
- Pytest test suite for auth, RBAC, and security flows

## Tech Stack

- Backend: Flask
- Database: MySQL (production/development), SQLite (tests)
- ORM/Migrations: SQLAlchemy + Flask-Migrate (Alembic)
- Auth: Flask-JWT-Extended
- Forms/CSRF: Flask-WTF

## Prerequisites

Install these first:

- Python 3.12+
- `python3-venv`
- Git
- MySQL Server

Ubuntu example:

```bash
sudo apt update
sudo apt install -y git python3-venv mysql-server
```

## Setup

1. Clone and enter project

```bash
git clone <your-repo-url> secure-login-rbac
cd secure-login-rbac
```

2. Create and activate virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

3. Install dependencies

```bash
pip install -r requirements.txt
```

4. Configure environment

```bash
cp .env.example .env
```

Update `.env` values with secure secrets.

5. Create MySQL database and user

```sql
CREATE DATABASE secure_login_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'secure_user'@'localhost' IDENTIFIED BY 'secure_password';
GRANT ALL PRIVILEGES ON secure_login_db.* TO 'secure_user'@'localhost';
FLUSH PRIVILEGES;
```

6. Apply database migrations

```bash
export FLASK_APP=run.py
flask db upgrade
```

7. Run the app

```bash
python run.py
```

Open: `http://127.0.0.1:5000`

## One-Command Real MySQL Setup (Recommended)

If you want a full real setup (no SQLite) in one flow:

```bash
./scripts/setup_real_mysql.sh
```

This script will:
- install MySQL server/client (via `sudo`)
- start and enable MySQL service
- create database and app user
- update `.env` with real MySQL URL and strong secrets
- run `flask db upgrade`

Then start app:

```bash
./scripts/run_real.sh
```

## CAPTCHA Modes

### Turnstile mode (production-like)

In `.env`:

```env
TURNSTILE_ENABLED=true
TURNSTILE_SITE_KEY=your_site_key
TURNSTILE_SECRET_KEY=your_secret_key
```

### Local math fallback (development)

In `.env`:

```env
TURNSTILE_ENABLED=false
```

## Default Security Config

- JWT in `HttpOnly` cookies
- `SameSite=Lax`
- 2-hour access token expiry
- Lockout after 5 failed attempts
- Lockout duration: 30 minutes
- Lockout counting window: 15 minutes

## Routes

- `GET /register` - Registration form
- `POST /register` - Register account
- `GET /login` - Login form
- `POST /login` - Authenticate user
- `POST /logout` - Logout user
- `GET /directory` - Members directory (authenticated, read-only)
- `GET /dashboard` - Legacy route (redirects to `/directory`)
- `GET /profile` - Profile settings page
- `POST /profile/details` - Update profile identity fields
- `POST /profile/password` - Change account password
- `POST /profile/avatar` - Upload profile photo
- `GET /admin/dashboard` - Admin dashboard (admin only)
- `GET /admin/users/add` - Add users page (admin only)
- `POST /admin/users/add` - Create user/admin account (admin only)
- `POST /admin/users/<id>/role` - Change role
- `POST /admin/users/<id>/status` - Activate/deactivate account
- `POST /admin/users/<id>/unlock` - Unlock account
- `POST /admin/users/<id>/delete` - Delete account (admin only)

## Testing

Run tests:

```bash
pytest -q
```

## Troubleshooting

### Error: `Can't connect to MySQL server on 'localhost' ([Errno 111] Connection refused)`

This means app is configured for MySQL but MySQL service is not installed/running yet.

Fix:

```bash
./scripts/setup_real_mysql.sh
```

Or manually:

```bash
sudo systemctl enable --now mysql
sudo systemctl status mysql
```

### Error: `'cryptography' package is required for sha256_password or caching_sha2_password`

Install dependencies again inside venv:

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

Then run migration again:

```bash
export FLASK_APP=run.py
flask db upgrade
```

## Manual End-to-End Test Script

1. Register one `admin` and one `user` account.
2. Login with both accounts and verify redirects.
3. Confirm user cannot open `/admin/dashboard`.
4. Confirm admin can change role/status and unlock users.
5. Confirm admin can delete user/admin when at least one other admin remains.
6. Confirm last remaining admin cannot be deleted.
7. Update profile details/avatar/password from profile page.
8. Trigger repeated failed logins and verify account lockout.
9. Verify CAPTCHA failure blocks registration/login.
10. Verify duplicate registration is rejected.

## Debug Checklist

- Duplicate email/username handling
- Invalid email/password validation
- Weak password rejection
- JWT cookie issuance and logout invalidation
- Lockout behavior and unlock behavior
- CSRF token presence on POST forms
- Admin self-demotion/self-deactivation prevention

## Suggested Credentials (create during setup)

Create these manually via registration:

- Admin: `admin_demo@example.com`
- User: `user_demo@example.com`

Use strong passwords as required by policy.
