import os
import random
import requests
from datetime import datetime
from functools import wraps
from urllib.parse import urlencode
from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from flask_cors import CORS
from models import db, User, TempEmail, EmailMessage

app = Flask(__name__)
CORS(app, supports_credentials=True)

database_url = os.environ.get('AUTH_DATABASE_URL', os.environ.get('DATABASE_URL', 'sqlite:///tempmail.db'))
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,
    'pool_recycle': 300,
}
app.secret_key = os.environ.get('SECRET_KEY', 'tempmail-secret-key-2024')

is_production = os.environ.get('RAILWAY_ENVIRONMENT') or os.environ.get('FLASK_ENV') == 'production'
if is_production:
    app.config['SESSION_COOKIE_SECURE'] = True
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['PREFERRED_URL_SCHEME'] = 'https'

GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', '')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', '')

db.init_app(app)

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36',
]

def get_headers():
    return {
        "Host": "api.internal.temp-mail.io",
        "Connection": "keep-alive",
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "application/json, text/plain, */*",
        "Application-Version": "2.2.14",
        "Application-Name": "web",
        "Origin": "https://temp-mail.io",
        "Referer": "https://temp-mail.io/",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "en-US,en;q=0.9",
    }

def get_current_user():
    user_id = session.get('user_id')
    if user_id:
        return User.query.get(user_id)
    return None

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Login diperlukan', 'require_login': True}), 401
        return f(*args, **kwargs)
    return decorated_function

def check_email_ownership(email_account, user):
    if email_account.user_id is None:
        return True
    if user and email_account.user_id == user.id:
        return True
    return False

@app.route('/')
def index():
    user = get_current_user()
    return render_template('index.html', user=user)

@app.route('/auth/login')
def auth_login():
    redirect_uri = request.host_url.rstrip('/') + '/auth/callback'
    
    state = os.urandom(16).hex()
    session['oauth_state'] = state
    
    params = {
        'client_id': GOOGLE_CLIENT_ID,
        'redirect_uri': redirect_uri,
        'response_type': 'code',
        'scope': 'openid email profile',
        'state': state,
        'access_type': 'offline',
        'prompt': 'consent'
    }
    
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
    return redirect(auth_url)

@app.route('/auth/callback')
def auth_callback():
    error = request.args.get('error')
    if error:
        return redirect('/?error=' + error)
    
    code = request.args.get('code')
    state = request.args.get('state')
    
    if not code:
        return redirect('/?error=no_code')
    
    if state != session.get('oauth_state'):
        return redirect('/?error=invalid_state')
    
    redirect_uri = request.host_url.rstrip('/') + '/auth/callback'
    
    try:
        token_response = requests.post(
            'https://oauth2.googleapis.com/token',
            data={
                'code': code,
                'client_id': GOOGLE_CLIENT_ID,
                'client_secret': GOOGLE_CLIENT_SECRET,
                'redirect_uri': redirect_uri,
                'grant_type': 'authorization_code'
            },
            timeout=10
        )
        
        if token_response.status_code != 200:
            return redirect('/?error=token_failed')
        
        tokens = token_response.json()
        access_token = tokens.get('access_token')
        refresh_token = tokens.get('refresh_token')
        
        userinfo_response = requests.get(
            'https://www.googleapis.com/oauth2/v2/userinfo',
            headers={'Authorization': f'Bearer {access_token}'},
            timeout=10
        )
        
        if userinfo_response.status_code != 200:
            return redirect('/?error=userinfo_failed')
        
        userinfo = userinfo_response.json()
        google_id = userinfo.get('id')
        email = userinfo.get('email')
        name = userinfo.get('name')
        picture = userinfo.get('picture')
        
        user = User.query.filter_by(google_id=google_id).first()
        
        if user:
            user.access_token = access_token
            if refresh_token:
                user.refresh_token = refresh_token
            user.last_login = datetime.utcnow()
            user.name = name
            user.picture = picture
        else:
            user = User(
                google_id=google_id,
                email=email,
                name=name,
                picture=picture,
                access_token=access_token,
                refresh_token=refresh_token
            )
            db.session.add(user)
        
        db.session.commit()
        
        session['user_id'] = user.id
        session.pop('oauth_state', None)
        
        return redirect('/')
        
    except Exception as e:
        print(f"OAuth Error: {str(e)}")
        return redirect('/?error=auth_failed')

@app.route('/auth/logout')
def auth_logout():
    session.clear()
    return redirect('/')

@app.route('/api/auth/status')
def auth_status():
    user = get_current_user()
    if user:
        return jsonify({
            'success': True,
            'logged_in': True,
            'user': user.to_dict()
        })
    return jsonify({
        'success': True,
        'logged_in': False,
        'user': None
    })

@app.route('/api/domains', methods=['GET'])
def get_domains():
    try:
        response = requests.get(
            "https://api.internal.temp-mail.io/api/v3/domains",
            headers=get_headers(),
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            domains = [d['name'] for d in data.get('domains', [])]
            return jsonify({'success': True, 'domains': domains})
        return jsonify({'success': False, 'error': 'Failed to fetch domains'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/email/create/random', methods=['POST'])
def create_random_email():
    try:
        user = get_current_user()
        
        random_length = random.randint(10, 15)
        payload = {
            "min_name_length": random_length,
            "max_name_length": random_length
        }
        
        response = requests.post(
            "https://api.internal.temp-mail.io/api/v3/email/new",
            json=payload,
            headers=get_headers(),
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            email_address = data.get('email')
            token = data.get('token')
            
            existing = TempEmail.query.filter_by(email=email_address).first()
            if existing:
                existing.token = token
                existing.is_active = True
                if user:
                    existing.user_id = user.id
                db.session.commit()
                return jsonify({'success': True, 'email': existing.to_dict()})
            
            new_email = TempEmail(
                email=email_address,
                token=token,
                digit=str(random_length),
                user_id=user.id if user else None
            )
            db.session.add(new_email)
            db.session.commit()
            
            return jsonify({'success': True, 'email': new_email.to_dict()})
        return jsonify({'success': False, 'error': 'Failed to create email'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/email/create/custom', methods=['POST'])
def create_custom_email():
    try:
        user = get_current_user()
        data = request.get_json()
        name = data.get('name', '').strip()
        domain = data.get('domain', '').strip()
        
        if not name or not domain:
            return jsonify({'success': False, 'error': 'Name and domain are required'})
        
        payload = {
            "name": name,
            "domain": domain
        }
        
        response = requests.post(
            "https://api.internal.temp-mail.io/api/v3/email/new",
            json=payload,
            headers=get_headers(),
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            email_address = result.get('email')
            token = result.get('token')
            
            existing = TempEmail.query.filter_by(email=email_address).first()
            if existing:
                existing.token = token
                existing.is_active = True
                if user:
                    existing.user_id = user.id
                db.session.commit()
                return jsonify({'success': True, 'email': existing.to_dict()})
            
            new_email = TempEmail(
                email=email_address,
                token=token,
                digit=str(len(name)),
                user_id=user.id if user else None
            )
            db.session.add(new_email)
            db.session.commit()
            
            return jsonify({'success': True, 'email': new_email.to_dict()})
        return jsonify({'success': False, 'error': 'Failed to create email'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/email/<int:email_id>/inbox', methods=['GET'])
def check_inbox(email_id):
    try:
        user = get_current_user()
        email_account = TempEmail.query.get(email_id)
        if not email_account:
            return jsonify({'success': False, 'error': 'Email not found'})
        
        if not check_email_ownership(email_account, user):
            return jsonify({'success': False, 'error': 'Akses ditolak'}), 403
        
        response = requests.get(
            f"https://api.internal.temp-mail.io/api/v3/email/{email_account.email}/messages",
            headers=get_headers(),
            timeout=10
        )
        
        if response.status_code == 200:
            messages = response.json()
            
            for msg in messages:
                existing = EmailMessage.query.filter_by(message_id=msg.get('id')).first()
                if not existing:
                    received_at = None
                    if msg.get('created_at'):
                        try:
                            received_at = datetime.fromisoformat(msg['created_at'].replace('Z', '+00:00'))
                        except:
                            received_at = datetime.utcnow()
                    
                    new_msg = EmailMessage(
                        message_id=msg.get('id'),
                        email_id=email_account.id,
                        from_email=msg.get('from', ''),
                        to_email=msg.get('to', email_account.email),
                        subject=msg.get('subject', '(No Subject)'),
                        body_text=msg.get('body_text', ''),
                        body_html=msg.get('body_html', ''),
                        cc=str(msg.get('cc', '')),
                        attachments=msg.get('attachments', []),
                        received_at=received_at
                    )
                    db.session.add(new_msg)
            
            db.session.commit()
            
            db_messages = EmailMessage.query.filter_by(email_id=email_id).order_by(EmailMessage.received_at.desc()).all()
            return jsonify({
                'success': True,
                'email': email_account.email,
                'messages': [m.to_dict() for m in db_messages]
            })
        elif response.status_code == 400:
            email_account.is_active = False
            db.session.commit()
            return jsonify({'success': False, 'error': 'Email expired'})
        return jsonify({'success': False, 'error': 'Failed to fetch inbox'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/emails', methods=['GET'])
def get_all_emails():
    try:
        user = get_current_user()
        if user:
            emails = TempEmail.query.filter_by(user_id=user.id).order_by(TempEmail.created_at.desc()).all()
        else:
            emails = TempEmail.query.filter_by(user_id=None).order_by(TempEmail.created_at.desc()).all()
        return jsonify({
            'success': True,
            'emails': [e.to_dict() for e in emails]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/email/<int:email_id>', methods=['GET'])
def get_email(email_id):
    try:
        user = get_current_user()
        email = TempEmail.query.get(email_id)
        if not email:
            return jsonify({'success': False, 'error': 'Email not found'})
        
        if not check_email_ownership(email, user):
            return jsonify({'success': False, 'error': 'Akses ditolak'}), 403
        
        return jsonify({'success': True, 'email': email.to_dict()})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/email/<int:email_id>', methods=['DELETE'])
def delete_email(email_id):
    try:
        user = get_current_user()
        email = TempEmail.query.get(email_id)
        if not email:
            return jsonify({'success': False, 'error': 'Email not found'})
        
        if not check_email_ownership(email, user):
            return jsonify({'success': False, 'error': 'Akses ditolak'}), 403
        
        db.session.delete(email)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Email deleted successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/email/<int:email_id>/activate', methods=['POST'])
def activate_email(email_id):
    try:
        user = get_current_user()
        email_account = TempEmail.query.get(email_id)
        if not email_account:
            return jsonify({'success': False, 'error': 'Email not found'})
        
        if not check_email_ownership(email_account, user):
            return jsonify({'success': False, 'error': 'Akses ditolak'}), 403
        
        name = email_account.email.split('@')[0]
        domain = email_account.email.split('@')[1]
        
        payload = {
            "name": name,
            "token": email_account.token,
            "domain": domain
        }
        
        response = requests.post(
            "https://api.internal.temp-mail.io/api/v3/email/new",
            json=payload,
            headers=get_headers(),
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            email_account.token = result.get('token', email_account.token)
            email_account.is_active = True
            db.session.commit()
            return jsonify({'success': True, 'email': email_account.to_dict()})
        return jsonify({'success': False, 'error': 'Failed to reactivate email'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/message/<int:message_id>', methods=['GET'])
def get_message(message_id):
    try:
        user = get_current_user()
        message = EmailMessage.query.get(message_id)
        if not message:
            return jsonify({'success': False, 'error': 'Message not found'})
        
        email_account = TempEmail.query.get(message.email_id)
        if email_account and not check_email_ownership(email_account, user):
            return jsonify({'success': False, 'error': 'Akses ditolak'}), 403
        
        return jsonify({'success': True, 'message': message.to_dict()})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'timestamp': datetime.utcnow().isoformat()})

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
