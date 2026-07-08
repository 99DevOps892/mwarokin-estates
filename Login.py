```python
"""
LogIn.py — Modern Flask Authentication Gateway for Mwarokin Estates
-------------------------------------------------------------------
A secure, session‑based login handler with automatic inactivity timeout
(60 seconds) and a seamless redirect flow. Mimics the behaviour of the
provided front‑end HTML but implemented server‑side in Python.

Uses Flask's built‑in session cookie, server‑side timestamp validation,
and a hard‑coded demo credential policy (any ID + password length >= 4).
"""

import os
from datetime import datetime, timedelta
from functools import wraps

from flask import Flask, request, session, redirect, url_for, render_template_string, flash

# ----------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------
class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    SESSION_TIMEOUT_MINUTES = 1                 # matches the JS 1‑minute inactivity
    SESSION_KEY = 'mwarokin_session'
    ACTIVITY_KEY = 'mwarokin_last_activity'
    REDIRECT_DEFAULT = 'dashboard'

# ----------------------------------------------------------------------
# App Initialization
# ----------------------------------------------------------------------
app = Flask(__name__)
app.config.from_object(Config)

# ----------------------------------------------------------------------
# The Login Page (embedded as a template string)
# ----------------------------------------------------------------------
LOGIN_PAGE_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Mwarokin Estates — Secure Sign In</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,500;0,600;0,700;1,300;1,400&family=Syne:wght@400;500;600;700&family=DM+Sans:wght@300;400;500;600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
<style>
  :root {
    --forest: #0d2818; --forest-mid: #1a3d28; --forest-light: #244d34; --forest-pale: #2e6040;
    --gold: #c9a84c; --gold-light: #e2c27a; --gold-pale: #f0dba8;
    --gold-dim: rgba(201,168,76,0.15); --gold-glow: rgba(201,168,76,0.08);
    --obsidian: #080f0b; --surface: #111f16; --surface-raised: #172a1e; --surface-card: #1c3323;
    --ivory: #f5f0e8; --ivory-dim: rgba(245,240,232,0.7); --ivory-muted: rgba(245,240,232,0.45); --ivory-subtle: rgba(245,240,232,0.15);
    --success: #4caf7d; --warning: #e8a838; --danger: #d64f3c; --info: #4a9ebb;
    --radius: 14px; --radius-sm: 8px; --radius-pill: 50px;
    --shadow: 0 8px 32px rgba(0,0,0,0.4); --shadow-gold: 0 4px 24px rgba(201,168,76,0.12);
    --transition: all 0.28s cubic-bezier(0.4,0,0.2,1);
    --border: 1px solid rgba(201,168,76,0.12); --border-strong: 1px solid rgba(201,168,76,0.28);
  }
  *,*::before,*::after{margin:0;padding:0;box-sizing:border-box;}
  html{scroll-behavior:smooth;}
  body{
    font-family:'DM Sans',sans-serif; background:var(--obsidian); color:var(--ivory);
    min-height:100vh; display:flex; align-items:center; justify-content:center;
    padding:24px; position:relative; overflow-x:hidden;
  }
  ::-webkit-scrollbar{width:6px;} ::-webkit-scrollbar-track{background:var(--obsidian);} ::-webkit-scrollbar-thumb{background:var(--forest-pale);border-radius:3px;}

  /* ambient background */
  body::before{
    content:''; position:fixed; top:-20%; right:-10%; width:600px; height:600px;
    background:radial-gradient(circle, rgba(201,168,76,0.08) 0%, transparent 70%); border-radius:50%; pointer-events:none;
  }
  body::after{
    content:''; position:fixed; bottom:-15%; left:-10%; width:500px; height:500px;
    background:radial-gradient(circle, rgba(46,96,64,0.35) 0%, transparent 70%); border-radius:50%; pointer-events:none;
  }

  .auth-wrap{
    display:grid; grid-template-columns:1fr 1fr; max-width:960px; width:100%;
    background:var(--forest); border:var(--border-strong); border-radius:22px;
    box-shadow:0 24px 90px rgba(0,0,0,0.55); overflow:hidden; position:relative; z-index:1;
  }

  /* LEFT — brand panel */
  .brand-panel{
    background:linear-gradient(160deg, var(--forest-mid) 0%, #1f4a2e 100%);
    padding:52px 44px; display:flex; flex-direction:column; justify-content:space-between;
    position:relative; overflow:hidden; border-right:var(--border);
  }
  .brand-panel::before{
    content:''; position:absolute; top:-70px; left:-70px; width:260px; height:260px;
    background:radial-gradient(circle, rgba(201,168,76,0.14) 0%, transparent 70%); border-radius:50%;
  }
  .brand-mark{display:flex; align-items:center; gap:14px; position:relative; z-index:1;}
  .brand-icon{
    width:46px; height:46px; background:linear-gradient(135deg, var(--gold), var(--gold-light));
    border-radius:12px; display:flex; align-items:center; justify-content:center; font-size:19px; color:var(--forest);
  }
  .brand-name{font-family:'Cormorant Garamond',serif; font-size:1.4rem; font-weight:600; color:var(--gold-light);}
  .brand-sub{font-size:0.62rem; font-weight:500; color:var(--ivory-muted); letter-spacing:0.18em; text-transform:uppercase;}

  .brand-copy{position:relative; z-index:1; margin-top:40px;}
  .brand-eyebrow{font-size:0.72rem; font-weight:600; color:var(--gold); letter-spacing:0.18em; text-transform:uppercase; margin-bottom:12px;}
  .brand-title{font-family:'Cormorant Garamond',serif; font-size:2.1rem; font-weight:600; line-height:1.2; color:var(--ivory); margin-bottom:14px;}
  .brand-title em{color:var(--gold-light); font-style:italic;}
  .brand-desc{font-size:0.9rem; color:var(--ivory-muted); line-height:1.65; max-width:340px;}

  .trust-row{position:relative; z-index:1; display:flex; gap:22px; margin-top:auto; padding-top:30px;}
  .trust-item{display:flex; align-items:center; gap:8px; font-size:0.72rem; color:var(--ivory-muted); font-weight:500;}
  .trust-item i{color:var(--gold); font-size:0.85rem;}

  /* RIGHT — form panel */
  .form-panel{background:var(--surface); padding:52px 46px; display:flex; flex-direction:column; justify-content:center;}
  .form-heading{margin-bottom:30px;}
  .form-title{font-family:'Cormorant Garamond',serif; font-size:1.7rem; font-weight:600; color:var(--ivory); margin-bottom:6px;}
  .form-title-sub{font-size:0.84rem; color:var(--ivory-muted);}

  #sessionBanner{
    display:none; align-items:center; gap:10px; background:rgba(232,168,56,0.1);
    border:1px solid rgba(232,168,56,0.3); color:var(--warning); border-radius:var(--radius-sm);
    padding:11px 14px; font-size:0.78rem; margin-bottom:20px; font-weight:500;
  }
  #sessionBanner.show{display:flex;}

  .form-group{margin-bottom:18px;}
  .form-label{display:block; font-size:0.76rem; font-weight:600; color:var(--ivory-muted); letter-spacing:0.06em; text-transform:uppercase; margin-bottom:8px;}
  .input-shell{position:relative; display:flex; align-items:center;}
  .input-shell i.leading{position:absolute; left:14px; color:var(--ivory-muted); font-size:0.85rem;}
  .form-control{
    width:100%; background:var(--surface-card); border:var(--border); border-radius:var(--radius-sm);
    padding:12px 14px 12px 40px; color:var(--ivory); font-family:'DM Sans',sans-serif; font-size:0.9rem;
    outline:none; transition:var(--transition);
  }
  .form-control:focus{border-color:rgba(201,168,76,0.4); box-shadow:0 0 0 3px rgba(201,168,76,0.08);}
  .form-control::placeholder{color:var(--ivory-muted);}
  .toggle-pass{position:absolute; right:14px; color:var(--ivory-muted); cursor:pointer; font-size:0.85rem; background:none; border:none;}
  .toggle-pass:hover{color:var(--gold-light);}

  .form-meta{display:flex; align-items:center; justify-content:space-between; margin:2px 0 22px;}
  .remember{display:flex; align-items:center; gap:8px; font-size:0.8rem; color:var(--ivory-muted); cursor:pointer; user-select:none;}
  .remember input{accent-color:var(--gold); width:15px; height:15px; cursor:pointer;}
  .forgot-link{font-size:0.8rem; color:var(--gold); text-decoration:none; font-weight:500;}
  .forgot-link:hover{color:var(--gold-light);}

  .btn-gold{
    width:100%; font-family:'DM Sans',sans-serif; font-weight:600; font-size:0.88rem;
    padding:13px 18px; border:none; border-radius:var(--radius-sm); cursor:pointer; transition:var(--transition);
    letter-spacing:0.03em; display:flex; align-items:center; justify-content:center; gap:8px;
    background:linear-gradient(135deg, var(--gold), #b8924a); color:var(--forest);
  }
  .btn-gold:hover{background:linear-gradient(135deg, var(--gold-light), var(--gold)); box-shadow:0 4px 18px rgba(201,168,76,0.3); transform:translateY(-1px);}
  .btn-gold:disabled{opacity:0.65; cursor:not-allowed; transform:none;}
  .btn-gold .fa-spinner{animation:spin 0.8s linear infinite;}
  @keyframes spin{to{transform:rotate(360deg);}}

  .divider{display:flex; align-items:center; gap:12px; margin:22px 0; color:var(--ivory-muted); font-size:0.72rem; text-transform:uppercase; letter-spacing:0.1em;}
  .divider::before, .divider::after{content:''; flex:1; height:1px; background:rgba(201,168,76,0.12);}

  .demo-note{
    background:var(--surface-raised); border:var(--border); border-radius:var(--radius-sm);
    padding:13px 15px; font-size:0.78rem; color:var(--ivory-muted); line-height:1.55; margin-bottom:20px;
  }
  .demo-note strong{color:var(--gold-light); font-weight:600;}

  .security-note{display:flex; align-items:center; justify-content:center; gap:7px; font-size:0.74rem; color:var(--ivory-muted); margin-top:20px;}
  .security-note i{color:var(--gold);}

  #toast{
    position:fixed; bottom:28px; right:28px; background:var(--forest-mid); border:var(--border-strong);
    border-radius:var(--radius); padding:14px 20px; display:flex; align-items:center; gap:12px;
    box-shadow:var(--shadow); z-index:999; min-width:280px; transform:translateX(120%);
    transition:transform 0.35s cubic-bezier(0.4,0,0.2,1);
  }
  #toast.show{transform:translateX(0);}
  .toast-icon{width:32px;height:32px;border-radius:50%;background:rgba(214,79,60,0.15);display:flex;align-items:center;justify-content:center;color:var(--danger);flex-shrink:0;}
  .toast-text{font-size:0.85rem;color:var(--ivory);font-weight:500;}

  @media (max-width:820px){
    .auth-wrap{grid-template-columns:1fr;}
    .brand-panel{display:none;}
    .form-panel{padding:40px 28px;}
  }
</style>
</head>
<body>

<div class="auth-wrap">
  <!-- BRAND PANEL -->
  <div class="brand-panel">
    <div>
      <div class="brand-mark">
        <div class="brand-icon"><i class="fas fa-city"></i></div>
        <div>
          <div class="brand-name">Mwarokin Estates</div>
          <div class="brand-sub">Resident Portal</div>
        </div>
      </div>
      <div class="brand-copy">
        <p class="brand-eyebrow">Secure Access</p>
        <h1 class="brand-title">Your home,<br><em>always within reach.</em></h1>
        <p class="brand-desc">Sign in to manage rent, bills, maintenance requests, and communication with your estate — all in one place.</p>
      </div>
    </div>
    <div class="trust-row">
      <div class="trust-item"><i class="fas fa-shield-alt"></i>256-bit encrypted</div>
      <div class="trust-item"><i class="fas fa-user-lock"></i>Session-protected</div>
    </div>
  </div>

  <!-- FORM PANEL -->
  <div class="form-panel">
    <div class="form-heading">
      <h2 class="form-title">Welcome back</h2>
      <p class="form-title-sub">Sign in to continue to your dashboard.</p>
    </div>

    {% if banner_message %}
    <div id="sessionBanner" class="show"><i class="fas fa-clock"></i><span>{{ banner_message }}</span></div>
    {% endif %}

    <form action="{{ url_for('login') }}" method="post" autocomplete="off">
      <div class="form-group">
        <label class="form-label">Tenant ID or Email</label>
        <div class="input-shell">
          <i class="fas fa-user leading"></i>
          <input type="text" id="loginId" name="login_id" class="form-control" placeholder="e.g. A-304 or john@example.com" required>
        </div>
      </div>
      <div class="form-group">
        <label class="form-label">Password</label>
        <div class="input-shell">
          <i class="fas fa-lock leading"></i>
          <input type="password" id="loginPass" name="password" class="form-control" placeholder="Enter your password" required>
          <button type="button" class="toggle-pass" id="togglePass"><i class="fas fa-eye"></i></button>
        </div>
      </div>
      <div class="form-meta">
        <label class="remember"><input type="checkbox" name="remember" checked> Keep me signed in</label>
        <a class="forgot-link" href="#" onclick="showToast('Password reset link sent if the account exists.'); return false;">Forgot password?</a>
      </div>
      <button type="submit" class="btn-gold" id="loginBtn"><i class="fas fa-lock"></i><span id="loginBtnText">Sign In Securely</span></button>
    </form>

    <div class="divider">Demo Access</div>
    <div class="demo-note">
      <strong>Prototype mode:</strong> enter any Tenant ID and a password of at least 4 characters to sign in. This screen simulates a secure Auth0-style gate for the Mwarokin Estates portal.
    </div>

    <div class="security-note"><i class="fas fa-shield-alt"></i>Protected session · auto sign-out after 1 minute of inactivity</div>
  </div>
</div>

<div id="toast">
  <div class="toast-icon"><i class="fas fa-exclamation"></i></div>
  <div class="toast-text" id="toastText">Message</div>
</div>

<script>
  document.getElementById('togglePass').addEventListener('click', function(){
    const input = document.getElementById('loginPass');
    const icon = this.querySelector('i');
    if (input.type === 'password') { input.type = 'text'; icon.className = 'fas fa-eye-slash'; }
    else { input.type = 'password'; icon.className = 'fas fa-eye'; }
  });

  function showToast(msg){
    const t = document.getElementById('toast');
    document.getElementById('toastText').textContent = msg;
    t.classList.add('show');
    setTimeout(() => t.classList.remove('show'), 3200);
  }

  // Show toast if flashed messages exist (from Flask)
  {% with messages = get_flashed_messages() %}
    {% if messages %}
      window.addEventListener('DOMContentLoaded', function() {
        showToast('{{ messages[0] }}');
      });
    {% endif %}
  {% endwith %}
</script>
</body>
</html>
"""

# ----------------------------------------------------------------------
# Session validation decorator
# ----------------------------------------------------------------------
def login_required(f):
    """Decorator that checks for a valid, non‑expired session."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_session_valid():
            # Clear any stale session data
            session.pop(Config.SESSION_KEY, None)
            session.pop(Config.ACTIVITY_KEY, None)
            return redirect(url_for('login_page', reason='timeout'))
        # Update activity timestamp on every request
        session[Config.ACTIVITY_KEY] = datetime.utcnow().isoformat()
        return f(*args, **kwargs)
    return decorated_function


def is_session_valid() -> bool:
    """Return True if a session exists and has not timed out."""
    session_data = session.get(Config.SESSION_KEY)
    if not session_data:
        return False

    last_activity_str = session.get(Config.ACTIVITY_KEY)
    if not last_activity_str:
        return False

    try:
        last_activity = datetime.fromisoformat(last_activity_str)
    except (ValueError, TypeError):
        return False

    timeout_delta = timedelta(minutes=Config.SESSION_TIMEOUT_MINUTES)
    if datetime.utcnow() - last_activity > timeout_delta:
        return False

    return True

# ----------------------------------------------------------------------
# Routes
# ----------------------------------------------------------------------
@app.route('/')
def login_page():
    """Render the login page with an optional banner message."""
    # If there's already a valid session, go straight to the dashboard
    if is_session_valid():
        return redirect(url_for('dashboard'))

    banner_message = None
    reason = request.args.get('reason')
    if reason == 'timeout':
        banner_message = 'You were signed out after 1 minute of inactivity. Please sign in again.'
    elif reason == 'noauth':
        banner_message = 'Please sign in to access the resident portal.'
    elif reason == 'loggedout':
        banner_message = 'You have been signed out.'

    return render_template_string(LOGIN_PAGE_HTML, banner_message=banner_message)


@app.route('/login', methods=['POST'])
def login():
    """Authenticate the user (demo: accept any ID + password length >= 4)."""
    login_id = request.form.get('login_id', '').strip()
    password = request.form.get('password', '')

    if not login_id or len(password) < 4:
        flash('Enter a Tenant ID and a password of at least 4 characters.')
        return redirect(url_for('login_page'))

    # (In a real app you would verify credentials against a database)
    # For the demo, we accept everything and create a session.
    session[Config.SESSION_KEY] = {
        'tenant_id': login_id,
        'login_time': datetime.utcnow().isoformat()
    }
    session[Config.ACTIVITY_KEY] = datetime.utcnow().isoformat()

    # If "Remember me" is checked, the session cookie will persist beyond browser close.
    # By default Flask uses permanent sessions; we'll set the cookie lifetime.
    if request.form.get('remember'):
        session.permanent = True
        app.permanent_session_lifetime = timedelta(days=7)
    else:
        session.permanent = False

    # Redirect to the dashboard (or to a custom redirect URL if provided)
    redirect_target = request.args.get('redirect') or url_for('dashboard')
    return redirect(redirect_target)


@app.route('/dashboard')
@login_required
def dashboard():
    """The protected dashboard (placeholder)."""
    tenant = session.get(Config.SESSION_KEY, {}).get('tenant_id', 'Guest')
    return f"""
    <h1>Welcome, {tenant}!</h1>
    <p>This is your Mwarokin Estates dashboard. (Session is active.)</p>
    <p><a href="{url_for('logout')}">Sign out</a></p>
    """


@app.route('/logout')
def logout():
    """Clear the session and redirect to login."""
    session.pop(Config.SESSION_KEY, None)
    session.pop(Config.ACTIVITY_KEY, None)
    return redirect(url_for('login_page', reason='loggedout'))


# ----------------------------------------------------------------------
# Entry point
# ----------------------------------------------------------------------
if __name__ == '__main__':
    # Use a strong secret key in production!
    app.run(debug=True, host='0.0.0.0', port=5000)
```