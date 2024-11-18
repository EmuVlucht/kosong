# M-Mail - Temporary Email Web Application

## Overview
Aplikasi web full-stack untuk membuat dan mengelola email sementara (temporary email). Dibangun dengan Flask (Python) backend dan frontend modern menggunakan HTML/CSS/JavaScript. Dilengkapi dengan sistem login menggunakan Google OAuth.

## Project Structure
```
.
├── app.py              # Flask backend application with Google OAuth
├── models.py           # SQLAlchemy database models (User, TempEmail, EmailMessage)
├── templates/
│   └── index.html      # Frontend HTML template with login UI
├── static/
│   ├── css/
│   │   └── style.css   # Modern CSS styling with auth components
│   └── js/
│       └── app.js      # Frontend JavaScript
├── page.drive.auth/    # Reference files for Google OAuth implementation
├── Procfile            # Railway/Heroku deployment
├── railway.toml        # Railway configuration
├── nixpacks.toml       # Nixpacks build configuration
└── pyproject.toml      # Python dependencies
```

## Technology Stack
- **Backend**: Flask 3.1.2, Flask-SQLAlchemy, Flask-CORS
- **Authentication**: Google OAuth 2.0
- **Database**: PostgreSQL (Railway)
- **Frontend**: HTML5, CSS3 (Custom modern design), JavaScript (Vanilla)
- **Deployment**: Gunicorn WSGI server, Railway

## Features
1. **Google OAuth Login** - Login dengan akun Google
2. **Per-User Email Storage** - Email tersimpan per akun pengguna
3. **Create Random Email** - Generate random temporary email
4. **Create Custom Email** - Choose email name and domain
5. **Inbox Check** - Auto-refresh inbox every 5 seconds
6. **View Messages** - Read full email content with attachments
7. **Email History** - All created emails saved to database
8. **Copy Email** - One-click copy email address
9. **Ownership Protection** - Email hanya bisa diakses oleh pemiliknya

## Database Schema
- **users**: Stores user accounts from Google OAuth (id, google_id, email, name, picture, tokens)
- **temp_emails**: Stores created email addresses with tokens (linked to user_id)
- **email_messages**: Stores received email messages

## API Endpoints
### Authentication
- `GET /auth/login` - Redirect to Google OAuth
- `GET /auth/callback` - OAuth callback handler
- `GET /auth/logout` - Logout user
- `GET /api/auth/status` - Check login status

### Email Operations
- `GET /` - Frontend web application
- `GET /health` - Health check endpoint
- `GET /api/domains` - Get available email domains
- `POST /api/email/create/random` - Create random email
- `POST /api/email/create/custom` - Create custom email
- `GET /api/emails` - List user's emails (filtered by user)
- `GET /api/email/<id>` - Get email details (ownership check)
- `GET /api/email/<id>/inbox` - Check inbox (ownership check)
- `DELETE /api/email/<id>` - Delete email (ownership check)
- `POST /api/email/<id>/activate` - Reactivate expired email (ownership check)
- `GET /api/message/<id>` - Get message details (ownership check)

## Environment Variables (Secrets)
- `AUTH_DATABASE_URL` - PostgreSQL connection string for auth database
- `DATABASE_URL` - Fallback PostgreSQL connection string
- `GOOGLE_CLIENT_ID` - Google OAuth Client ID
- `GOOGLE_CLIENT_SECRET` - Google OAuth Client Secret
- `SECRET_KEY` - Flask secret key (optional)
- `PORT` - Server port (default: 5000)

## Security Features
- Google OAuth 2.0 for secure authentication
- State parameter validation to prevent CSRF attacks
- Email ownership validation on all sensitive endpoints
- User-scoped data access (users can only see their own emails)
- Secure token storage

## Railway Deployment
Project sudah dikonfigurasi untuk deploy ke Railway:
1. Push repository ke GitHub
2. Connect repository ke Railway
3. Set environment variables:
   - `AUTH_DATABASE_URL`
   - `GOOGLE_CLIENT_ID`
   - `GOOGLE_CLIENT_SECRET`
4. Configure Google OAuth redirect URI: `https://your-domain.railway.app/auth/callback`
5. Deploy!

## Development
```bash
# Run locally
python app.py

# Production (with gunicorn)
gunicorn app:app --bind 0.0.0.0:5000 --workers 2
```

## Recent Changes
- **Dec 2024**: Added Google OAuth login system
- **Dec 2024**: Added User model with per-user email storage
- **Dec 2024**: Implemented ownership validation for security
- **Dec 2024**: Updated UI with login button and user info display
- **Dec 2024**: Converted from CLI to full-stack web application
- **Dec 2024**: Added PostgreSQL database integration
- **Dec 2024**: Created modern responsive frontend
- **Dec 2024**: Configured Railway deployment
