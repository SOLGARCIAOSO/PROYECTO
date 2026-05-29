function switchTab(tab, el) {
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.form-section').forEach(f => f.classList.remove('active'));
  el.classList.add('active');
  document.getElementById('form-' + tab).classList.add('active');
  document.getElementById('mensaje').className = '';
  document.getElementById('mensaje').textContent = '';
}

function showMsg(text, type) {
  const el = document.getElementById('mensaje');
  el.textContent = text;
  el.className = type;
}

async function loginUser() {
  const username = document.getElementById('login-user').value.trim();
  const password = document.getElementById('login-pass').value.trim();
  if (!username || !password) { showMsg('Completa todos los campos', 'error'); return; }

  const res = await fetch('http://localhost:5000/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password })
  });
  const data = await res.json();

  if (res.ok) {
    showMsg(data.mensaje, 'success');
    sessionStorage.setItem('fraudshield_user', username);
    setTimeout(() => {
      window.location.href = 'http://localhost:5000/app';
    }, 1000);
  } else {
    showMsg(data.mensaje, 'error');
  }
}

async function registerUser() {
  const username = document.getElementById('reg-user').value.trim();
  const password = document.getElementById('reg-pass').value.trim();
  if (!username || !password) { showMsg('Completa todos los campos', 'error'); return; }

  const res = await fetch('http://localhost:5000/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password })
  });
  const data = await res.json();
  showMsg(data.mensaje, res.ok ? 'success' : 'error');
}