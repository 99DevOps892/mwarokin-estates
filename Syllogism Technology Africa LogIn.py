```python
from flask import Flask, render_template_string, jsonify, request, session, redirect, url_for
import json
import datetime
import hashlib
import uuid
from functools import wraps

app = Flask(__name__)
app.secret_key = "syllogism_tech_africa_2026_secure_key"

# In-memory users database (demo)
users = {
    "demo@syllogism.africa": {
        "id": "user_001",
        "first_name": "John",
        "last_name": "Mwaro",
        "email": "demo@syllogism.africa",
        "password": hashlib.sha256("demo123".encode()).hexdigest(),  # demo123
        "created_at": "2025-01-15"
    }
}

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>Syllogism Technology Africa — LogIN Auth</title>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css" />
<style>
  :root {
    --ink: #0a0c10; --ink-soft: #1c2033; --accent: #1a56db; --gold: #c9a84c;
    --surface: #f5f4f0; --surface-raised: #ffffff; --radius: 14px;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: 'DM Sans', system-ui, sans-serif;
    background: var(--surface); color: var(--ink);
    min-height: 100vh;
  }
  .auth-wrapper { display: flex; min-height: 100vh; }
  .brand-panel {
    width: 44%; background: #0c1220; color: white; padding: 3rem;
    display: flex; flex-direction: column; justify-content: space-between;
    position: relative; overflow: hidden;
  }
  .form-panel {
    flex: 1; display: flex; align-items: center; justify-content: center;
    padding: 3rem 2rem; background: white;
  }
  .card {
    width: 100%; max-width: 420px; background: white; border-radius: var(--radius);
  }
  .btn {
    width: 100%; padding: 14px; background: var(--ink); color: white;
    border: none; border-radius: 10px; font-weight: 600; cursor: pointer;
    transition: all 0.3s;
  }
  .btn:hover { background: #1c2033; transform: translateY(-2px); }
  .input-group {
    margin-bottom: 1rem; position: relative;
  }
  .input-group input {
    width: 100%; padding: 14px 16px 14px 48px; border: 1px solid #ddd;
    border-radius: 10px; font-size: 1rem;
  }
  .input-group i {
    position: absolute; left: 16px; top: 50%; transform: translateY(-50%);
    color: #666;
  }
  .toast {
    position: fixed; bottom: 30px; right: 30px; padding: 16px 24px;
    background: #111; color: white; border-radius: 10px; display: none;
    z-index: 10000; box-shadow: 0 10px 30px rgba(0,0,0,0.3);
  }
</style>
</head>
<body>
<div class="auth-wrapper">
  <!-- Brand Panel -->
  <aside class="brand-panel">
    <div style="display:flex;align-items:center;gap:12px;">
      <div style="width:42px;height:42px;background:#1a56db;border-radius:10px;display:flex;align-items:center;justify-content:center;font-weight:800;color:white;font-size:20px;">STA</div>
      <div>
        <strong style="font-size:1.4rem;">Syllogism</strong><br>
        <small style="opacity:0.7;">Technology Africa</small>
      </div>
    </div>
    
    <div style="flex:1;display:flex;flex-direction:column;justify-content:center;">
      <p style="color:#c9a84c;font-weight:600;letter-spacing:2px;">ECO-SYSTEM</p>
      <h1 style="font-size:2.8rem;line-height:1.05;font-weight:800;margin:20px 0;">
        One Platform.<br><span style="color:#4a7ef7;">Infinite</span> Potential.
      </h1>
      <p style="max-width:340px;opacity:0.85;line-height:1.7;">
        Empowering Africa through cutting-edge technology solutions.
      </p>
    </div>
    
    <div style="font-size:0.9rem;opacity:0.6;">
      © 2026 Syllogism Technology Africa
    </div>
  </aside>

  <!-- Form Panel -->
  <main class="form-panel">
    <div class="card">
      <div style="padding:2rem 2.5rem;">
        <div style="display:flex;gap:8px;margin-bottom:2rem;">
          <button onclick="switchTab(0)" id="tab-login" style="flex:1;padding:12px;border:none;background:#f8f8f8;border-radius:9999px;font-weight:600;cursor:pointer;">Sign In</button>
          <button onclick="switchTab(1)" id="tab-register" style="flex:1;padding:12px;border:none;background:#f8f8f8;border-radius:9999px;font-weight:600;cursor:pointer;">Create Account</button>
        </div>

        <!-- LOGIN -->
        <div id="panel-login">
          <h2 style="font-size:1.8rem;margin-bottom:8px;">Welcome back</h2>
          <p style="color:#666;margin-bottom:2rem;">Sign in to continue to your dashboard</p>
          
          <form id="loginForm" onsubmit="handleLogin(event)">
            <div class="input-group">
              <i class="fas fa-envelope"></i>
              <input type="email" id="login-email" placeholder="you@example.com" required value="demo@syllogism.africa">
            </div>
            <div class="input-group">
              <i class="fas fa-lock"></i>
              <input type="password" id="login-password" placeholder="Password" required value="demo123">
            </div>
            <button type="submit" id="login-btn" class="btn">Sign In →</button>
          </form>
        </div>

        <!-- REGISTER -->
        <div id="panel-register" style="display:none;">
          <h2 style="font-size:1.8rem;margin-bottom:8px;">Join Syllogism</h2>
          <p style="color:#666;margin-bottom:2rem;">Create your account in seconds</p>
          
          <form id="registerForm" onsubmit="handleRegister(event)">
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:1rem;">
              <div class="input-group">
                <i class="fas fa-user"></i>
                <input type="text" id="reg-first" placeholder="First name" required>
              </div>
              <div class="input-group">
                <i class="fas fa-user"></i>
                <input type="text" id="reg-last" placeholder="Last name" required>
              </div>
            </div>
            <div class="input-group">
              <i class="fas fa-envelope"></i>
              <input type="email" id="reg-email" placeholder="Email address" required>
            </div>
            <div class="input-group">
              <i class="fas fa-lock"></i>
              <input type="password" id="reg-password" placeholder="Create password" required>
            </div>
            <button type="submit" id="reg-btn" class="btn">Create Account</button>
          </form>
        </div>
      </div>
    </div>
  </main>
</div>

<div id="toast" class="toast"></div>

<script>
  function switchTab(n) {
    document.getElementById('panel-login').style.display = n === 0 ? 'block' : 'none';
    document.getElementById('panel-register').style.display = n === 1 ? 'block' : 'none';
    document.getElementById('tab-login').style.background = n===0 ? '#111' : '#f8f8f8';
    document.getElementById('tab-login').style.color = n===0 ? 'white' : '#333';
    document.getElementById('tab-register').style.background = n===1 ? '#111' : '#f8f8f8';
    document.getElementById('tab-register').style.color = n===1 ? 'white' : '#333';
  }

  function showToast(message, isError=false) {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.style.background = isError ? '#b91c1c' : '#0b6e4f';
    toast.style.display = 'block';
    setTimeout(() => toast.style.display = 'none', 3500);
  }

  function handleLogin(e) {
    e.preventDefault();
    const btn = document.getElementById('login-btn');
    const originalText = btn.textContent;
    btn.textContent = 'Signing in...';
    btn.disabled = true;

    fetch('/api/login', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        email: document.getElementById('login-email').value,
        password: document.getElementById('login-password').value
      })
    })
    .then(r => r.json())
    .then(data => {
      if (data.success) {
        showToast('Login successful! Redirecting...');
        setTimeout(() => window.location.href = '/dashboard', 1200);
      } else {
        showToast(data.message || 'Invalid credentials', true);
      }
    })
    .finally(() => {
      btn.textContent = originalText;
      btn.disabled = false;
    });
  }

  function handleRegister(e) {
    e.preventDefault();
    const btn = document.getElementById('reg-btn');
    const originalText = btn.textContent;
    btn.textContent = 'Creating account...';
    btn.disabled = true;

    fetch('/api/register', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        first_name: document.getElementById('reg-first').value,
        last_name: document.getElementById('reg-last').value,
        email: document.getElementById('reg-email').value,
        password: document.getElementById('reg-password').value
      })
    })
    .then(r => r.json())
    .then(data => {
      if (data.success) {
        showToast('Account created successfully!');
        setTimeout(() => switchTab(0), 1500);
      } else {
        showToast(data.message || 'Registration failed', true);
      }
    })
    .finally(() => {
      btn.textContent = originalText;
      btn.disabled = false;
    });
  }

  // Demo credentials hint
  console.log('%cDemo credentials: demo@syllogism.africa / demo123', 'color:#c9a84c;font-weight:bold');
</script>
</body>
</html>"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({"success": False, "message": "Email and password required"})
    
    user = users.get(email)
    if user and user["password"] == hashlib.sha256(password.encode()).hexdigest():
        session['user_id'] = user["id"]
        session['email'] = email
        return jsonify({"success": True, "user": {"name": f"{user['first_name']} {user['last_name']}"}})
    
    return jsonify({"success": False, "message": "Invalid email or password"})

@app.route('/api/register', methods=['POST'])
def api_register():
    data = request.get_json()
    email = data.get('email')
    
    if email in users:
        return jsonify({"success": False, "message": "User already exists"})
    
    new_user = {
        "id": str(uuid.uuid4()),
        "first_name": data.get('first_name'),
        "last_name": data.get('last_name'),
        "email": email,
        "password": hashlib.sha256(data.get('password', '').encode()).hexdigest(),
        "created_at": datetime.datetime.now().strftime("%Y-%m-%d")
    }
    users[email] = new_user
    return jsonify({"success": True, "message": "Account created successfully"})

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/')
    return f"""
    <h1 style="text-align:center;padding:100px;font-family:sans-serif;">
        Welcome to Syllogism Technology Africa Dashboard!<br><br>
        <small style="color:#666;">Logged in as {session.get('email')}</small><br><br>
        <a href="/" style="color:#1a56db;">← Back to Login</a>
    </h1>
    """

if __name__ == '__main__':
    print("🌍 Syllogism Technology Africa Auth Portal")
    print("Running at: http://127.0.0.1:5000")
    print("Demo Login → demo@syllogism.africa / demo123")
    app.run(debug=True, port=5000)
```