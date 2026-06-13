// Auth guard — include in every protected page
(async function () {
  const token = localStorage.getItem('auth_token');
  if (!token) { window.location.href = '/login'; return; }
  try {
    const res = await fetch('/api/verify', { headers: { Authorization: 'Bearer ' + token } });
    if (!res.ok) { localStorage.removeItem('auth_token'); window.location.href = '/login'; }
  } catch { window.location.href = '/login'; }
})();

function getToken() { return localStorage.getItem('auth_token'); }

async function doLogout() {
  const token = getToken();
  if (token) await fetch('/api/logout', { method: 'POST', headers: { Authorization: 'Bearer ' + token } });
  localStorage.removeItem('auth_token');
  window.location.href = '/login';
}
