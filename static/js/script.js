/**
 * ============================================================
 *  FestVote — College Fest Voting System
 *  script.js — Complete API-integrated application logic
 * 
 *  This version connects the frontend to the Flask backend
 *  using REST API calls instead of localStorage
 * ============================================================
 */

/* ============================================================
   SECTION 1 — API HELPER MODULE
   ============================================================ */

const API = {
  baseURL: '/api',
  
  getToken() {
    return localStorage.getItem('authToken');
  },
  
  setToken(token) {
    localStorage.setItem('authToken', token);
  },
  
  removeToken() {
    localStorage.removeItem('authToken');
  },
  
  async request(endpoint, options = {}) {
    const headers = {
      'Content-Type': 'application/json',
      ...options.headers
    };
    
    const token = this.getToken();
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    
    try {
      const response = await fetch(`${this.baseURL}${endpoint}`, {
        ...options,
        headers
      });
      
      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.error || `HTTP ${response.status}`);
      }
      
      return data;
    } catch (error) {
      throw error;
    }
  },
  
  // Auth endpoints
  auth: {
    register: (name, email, password, role) =>
      API.request('/auth/register', {
        method: 'POST',
        body: JSON.stringify({ name, email, password, role })
      }),
    
    login: (email, password) =>
      API.request('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password })
      }),
    
    verify: () => API.request('/auth/verify', { method: 'POST' }),
    
    logout: () => API.request('/auth/logout', { method: 'POST' }),
    
    getMe: () => API.request('/auth/me', { method: 'GET' })
  },
  
  // Members endpoints
  members: {
    add: (name, email, password, role) =>
      API.request('/members', {
        method: 'POST',
        body: JSON.stringify({ name, email, password, role })
      }),
    
    getAll: (role = null) => {
      const url = role ? `/members?role=${role}` : '/members';
      return API.request(url);
    },
    
    get: (id) => API.request(`/members/${id}`),
    
    update: (id, data) =>
      API.request(`/members/${id}`, {
        method: 'PUT',
        body: JSON.stringify(data)
      }),
    
    delete: (id) =>
      API.request(`/members/${id}`, { method: 'DELETE' }),
    
    getStats: () => API.request('/members/stats/summary')
  },
  
  // Events endpoints
  events: {
    add: (name, description) =>
      API.request('/events', {
        method: 'POST',
        body: JSON.stringify({ name, description })
      }),
    
    getAll: () => API.request('/events'),
    
    get: (id) => API.request(`/events/${id}`),
    
    update: (id, data) =>
      API.request(`/events/${id}`, {
        method: 'PUT',
        body: JSON.stringify(data)
      }),
    
    delete: (id) =>
      API.request(`/events/${id}`, { method: 'DELETE' }),
    
    getStats: () => API.request('/events/stats/summary')
  },
  
  // Voting endpoints
  voting: {
    vote: (eventId) =>
      API.request('/vote', {
        method: 'POST',
        body: JSON.stringify({ event_id: eventId })
      }),
    
    getStatus: () => API.request('/vote/status'),
    
    getResults: () => API.request('/results'),
    
    getStats: () => API.request('/voting/stats'),
    
    getAllVotes: () => API.request('/votes')
  },
  
  // Admin endpoints
  admin: {
    getSettings: () => API.request('/admin/settings'),
    
    updateSettings: (data) =>
      API.request('/admin/settings', {
        method: 'PUT',
        body: JSON.stringify(data)
      }),
    
    toggleVoting: (action) =>
      API.request(`/admin/voting/${action}`, { method: 'POST' }),
    
    getDashboard: () => API.request('/admin/dashboard'),
    
    finalize: (topN) =>
      API.request(`/admin/finalize/${topN}`, { method: 'POST' }),
    
    unlock: () => API.request('/admin/unlock', { method: 'POST' }),
    
    reset: () =>
      API.request('/admin/reset', {
        method: 'POST',
        body: JSON.stringify({ confirm: true })
      })
  }
};


/* ============================================================
   SECTION 2 — UI CORE (Toast, Modal, Theme)
   ============================================================ */

function toast(title, desc = '', type = 'info', duration = 3500) {
  const icons = { success: '✓', error: '✕', warning: '⚠', info: 'ℹ' };
  const container = document.getElementById('toastContainer');

  const el = document.createElement('div');
  el.className = `toast toast-${type}`;
  el.innerHTML = `
    <span class="toast-icon">${icons[type]}</span>
    <div class="toast-content">
      <p class="toast-title">${title}</p>
      ${desc ? `<p class="toast-desc">${desc}</p>` : ''}
    </div>
  `;

  container.appendChild(el);

  setTimeout(() => {
    el.classList.add('toast-out');
    setTimeout(() => el.remove(), 350);
  }, duration);
}

function showModal({ icon = '⚠️', title = 'Confirm', message = '', confirmText = 'Confirm', confirmClass = 'btn-primary' } = {}) {
  return new Promise(resolve => {
    const overlay = document.getElementById('modalOverlay');
    const modalIcon = document.getElementById('modalIcon');
    const modalTitle = document.getElementById('modalTitle');
    const modalMsg = document.getElementById('modalMessage');
    const confirmBtn = document.getElementById('modalConfirm');
    const cancelBtn = document.getElementById('modalCancel');

    modalIcon.textContent = icon;
    modalTitle.textContent = title;
    modalMsg.textContent = message;
    confirmBtn.textContent = confirmText;
    confirmBtn.className = `btn ${confirmClass}`;

    overlay.classList.remove('hidden');

    const cleanup = (result) => {
      overlay.classList.add('hidden');
      confirmBtn.onclick = null;
      cancelBtn.onclick = null;
      resolve(result);
    };

    confirmBtn.onclick = () => cleanup(true);
    cancelBtn.onclick = () => cleanup(false);
    overlay.onclick = (e) => { if (e.target === overlay) cleanup(false); };
  });
}

function initTheme() {
  const saved = localStorage.getItem('festvote_theme') || 'dark';
  document.documentElement.setAttribute('data-theme', saved);
  updateThemeBtn(saved);
}

function toggleTheme() {
  const current = document.documentElement.getAttribute('data-theme');
  const next = current === 'dark' ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', next);
  localStorage.setItem('festvote_theme', next);
  updateThemeBtn(next);
}

function updateThemeBtn(theme) {
  const icon = document.getElementById('themeIcon');
  const label = document.getElementById('themeLabel');
  if (!icon || !label) return;
  icon.textContent = theme === 'dark' ? '☀️' : '🌙';
  label.textContent = theme === 'dark' ? 'Light Mode' : 'Dark Mode';
}


/* ============================================================
   SECTION 3 — ROUTER & PAGE MANAGEMENT
   ============================================================ */

function showPage(pageId) {
  document.querySelectorAll('.page').forEach(p => {
    p.classList.remove('active');
    p.classList.add('hidden');
  });
  const target = document.getElementById(pageId);
  if (target) {
    target.classList.remove('hidden');
    target.classList.add('active');
  }
}

let currentSection = 'overview';

function navigateTo(section) {
  currentSection = section;

  document.querySelectorAll('.nav-link').forEach(l => {
    l.classList.toggle('active', l.dataset.section === section);
  });

  const titles = {
    overview: 'Dashboard Overview',
    addMember: 'Add Member',
    viewMembers: 'All Members',
    addEvent: 'Add Event',
    viewEvents: 'All Events',
    voteEvents: 'Cast Your Vote',
    viewResults: 'Vote Results',
    systemSettings: 'System Settings',
    finalizeEvents: 'Finalize Results',
  };
  
  const titleEl = document.getElementById('topbarTitle');
  if (titleEl) titleEl.textContent = titles[section] || 'Dashboard';

  closeSidebar();

  const ca = document.getElementById('contentArea');
  if (ca) {
    ca.style.animation = 'none';
    void ca.offsetWidth;
    ca.style.animation = '';
  }

  renderSection(section);
}

function renderSection(section) {
  const ca = document.getElementById('contentArea');
  if (!ca) return;

  const renderers = {
    overview: renderOverview,
    addMember: renderAddMember,
    viewMembers: renderViewMembers,
    addEvent: renderAddEvent,
    viewEvents: renderViewEvents,
    voteEvents: renderVoteEvents,
    viewResults: renderViewResults,
    systemSettings: renderSystemSettings,
    finalizeEvents: renderFinalizeEvents,
  };

  const fn = renderers[section];
  if (fn) {
    ca.innerHTML = '';
    fn(ca);
  }
}


/* ============================================================
   SECTION 4 — SIDEBAR NAVIGATION
   ============================================================ */

function buildSidebar(role) {
  const session = JSON.parse(localStorage.getItem('user') || '{}');
  const sidebarNav = document.getElementById('sidebarNav');
  const sidebarName = document.getElementById('sidebarName');
  const sidebarRole = document.getElementById('sidebarRole');
  const sidebarAvatar = document.getElementById('sidebarAvatar');

  if (sidebarName) sidebarName.textContent = session.name;
  if (sidebarRole) {
    sidebarRole.textContent = roleLabel(role);
    sidebarRole.className = `role-badge ${role}`;
  }
  if (sidebarAvatar) sidebarAvatar.textContent = session.name?.[0].toUpperCase() || 'U';

  const allSections = {
    overview: { icon: '⊞', label: 'Overview', roles: ['admin', 'faculty', 'coordinator', 'student'] },
    systemSettings: { icon: '⚙', label: 'System Settings', roles: ['admin'] },
    addMember: { icon: '＋', label: 'Add Member', roles: ['admin', 'faculty'] },
    viewMembers: { icon: '◉', label: 'All Members', roles: ['admin', 'faculty'] },
    addEvent: { icon: '✦', label: 'Add Event', roles: ['admin', 'faculty'] },
    viewEvents: { icon: '≡', label: 'All Events', roles: ['admin', 'faculty'] },
    voteEvents: { icon: '◈', label: 'Vote', roles: ['admin', 'faculty', 'coordinator', 'student'] },
    viewResults: { icon: '▦', label: 'Vote Results', roles: ['admin', 'faculty', 'coordinator'] },
    finalizeEvents: { icon: '★', label: 'Finalize Results', roles: ['admin'] },
  };

  if (!sidebarNav) return;
  sidebarNav.innerHTML = '';

  let lastGroup = '';
  const groupNames = {
    overview: '',
    systemSettings: 'Administration',
    addMember: 'Members',
    viewMembers: 'Members',
    addEvent: 'Events',
    viewEvents: 'Events',
    voteEvents: 'Voting',
    viewResults: 'Voting',
    finalizeEvents: 'Voting',
  };

  Object.entries(allSections).forEach(([key, item]) => {
    if (!item.roles.includes(role)) return;

    const group = groupNames[key];
    if (group && group !== lastGroup) {
      const label = document.createElement('p');
      label.className = 'nav-section-label';
      label.textContent = group;
      sidebarNav.appendChild(label);
      lastGroup = group;
    }

    const link = document.createElement('button');
    link.className = 'nav-link';
    link.dataset.section = key;
    link.innerHTML = `<span class="nav-icon">${item.icon}</span> ${item.label}`;
    link.onclick = () => navigateTo(key);
    sidebarNav.appendChild(link);
  });
}

function roleLabel(role) {
  const map = {
    admin: 'Admin',
    faculty: 'Faculty',
    coordinator: 'Student Coordinator',
    student: 'Student',
  };
  return map[role] || role;
}

function openSidebar() {
  document.getElementById('sidebar').classList.add('open');
  document.getElementById('sidebarOverlay').classList.add('open');
}

function closeSidebar() {
  document.getElementById('sidebar').classList.remove('open');
  document.getElementById('sidebarOverlay').classList.remove('open');
}


/* ============================================================
   SECTION 5 — VIEW RENDERERS
   ============================================================ */

async function renderOverview(container) {
  try {
    const session = JSON.parse(localStorage.getItem('user') || '{}');
    const { members } = await API.members.getAll();
    const { events } = await API.events.getAll();
    const { total_votes } = await API.voting.getStats();
    const { settings } = await API.admin.getSettings();
    
    const myVote = JSON.parse(localStorage.getItem('userVote') || 'null');

    const hour = new Date().getHours();
    const greeting = hour < 12 ? 'Good Morning' : hour < 17 ? 'Good Afternoon' : 'Good Evening';

    container.innerHTML = `
      <div class="overview-welcome">
        <h2>${greeting}, ${session.name?.split(' ')[0]}! 👋</h2>
        <p>Welcome back to FestVote. You are logged in as <span class="role-badge ${session.role}">${roleLabel(session.role)}</span>.</p>
      </div>

      <div class="stats-grid">
        ${session.role !== 'student' ? `
          <div class="stat-card-modern glass-panel">
            <div class="stat-icon-bg">👥</div>
            <div class="stat-value" style="color: var(--accent-primary);">${members.length}</div>
            <div class="stat-label">Total Members</div>
          </div>
        ` : ''}
        <div class="stat-card-modern glass-panel">
          <div class="stat-icon-bg">🎉</div>
          <div class="stat-value" style="color: var(--accent-amber);">${events.length}</div>
          <div class="stat-label">Total Events</div>
        </div>
        <div class="stat-card-modern glass-panel">
          <div class="stat-icon-bg">🗳️</div>
          <div class="stat-value" style="color: var(--accent-emerald);">${total_votes}</div>
          <div class="stat-label">Votes Cast</div>
        </div>
        ${session.role !== 'student' ? `
          <div class="stat-card-modern glass-panel">
            <div class="stat-icon-bg">⚡</div>
            <div class="stat-value" style="color: var(--accent-cyan);">${settings.allowVoting ? 'ON' : 'OFF'}</div>
            <div class="stat-label">Voting Status</div>
          </div>
        ` : ''}
      </div>

      <div class="glass-panel" style="padding: 32px;">
        <h3 style="margin-bottom: 24px;">🎯 Your Status</h3>
        <div style="display: flex; flex-direction: column; gap: 16px;">
          <div style="display:flex; justify-content:space-between; align-items:center; padding-bottom: 16px; border-bottom: 1px solid var(--glass-border);">
            <span style="color: var(--text-secondary);">Vote Status</span>
            ${myVote
              ? `<span class="status-badge">✓ Voted for ${myVote.event_name}</span>`
              : settings.allowVoting
                ? `<span style="color: var(--accent-amber); font-weight: 600;">⏳ Not voted yet</span>`
                : `<span style="color: var(--text-muted);">Voting Closed</span>`
            }
          </div>
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <span style="color: var(--text-secondary);">Account Role</span>
            <span class="role-badge ${session.role}">${roleLabel(session.role)}</span>
          </div>
        </div>

        ${!myVote && settings.allowVoting ? `
          <div style="margin-top: 32px;">
            <button class="btn btn-primary" onclick="navigateTo('voteEvents')" style="width: 100%;">🗳️ Cast Your Vote Now</button>
          </div>
        ` : ''}
      </div>
    `;
  } catch (error) {
    toast('Error', error.message, 'error');
    container.innerHTML = `<div class="glass-panel" style="padding: 40px; text-align: center; color: var(--text-muted);">Failed to load overview</div>`;
  }
}

async function renderAddMember(container) {
  const session = JSON.parse(localStorage.getItem('user') || '{}');
  const isFaculty = session.role === 'faculty';

  const roleOptions = [
    { value: 'faculty', label: 'Faculty' },
    { value: 'coordinator', label: 'Student Coordinator' },
    { value: 'student', label: 'Student' },
  ];

  const optionsHTML = roleOptions
    .map(r => `<option value="${r.value}">${r.label}</option>`)
    .join('');

  container.innerHTML = `
    <div class="section-header">
      <div>
        <h2 class="section-title">＋ Add Member</h2>
        <p class="section-subtitle">Register a new user in the system</p>
      </div>
    </div>

    <div class="glass-panel" style="padding: 40px; max-width: 800px;">
      <h3 style="margin-bottom: 24px;">👤 Member Details</h3>
      <form id="addMemberForm" autocomplete="off" style="display: flex; flex-direction: column; gap: 24px;">
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 24px;">
          <div class="form-group">
            <label for="memberName">Full Name *</label>
            <div class="input-wrapper">
              <span class="input-icon">👤</span>
              <input type="text" id="memberName" placeholder="e.g. Arjun Mehta" required />
            </div>
          </div>
          <div class="form-group">
            <label for="memberEmail">Email Address *</label>
            <div class="input-wrapper">
              <span class="input-icon">✉</span>
              <input type="email" id="memberEmail" placeholder="user@college.edu" required />
            </div>
          </div>
        </div>
        
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 24px;">
          <div class="form-group">
            <label for="memberPassword">Password *</label>
            <div class="input-wrapper">
              <span class="input-icon">🔒</span>
              <input type="text" id="memberPassword" placeholder="Set a password" required />
            </div>
          </div>
          <div class="form-group">
            <label for="memberRole">Assign Role *</label>
            <div class="input-wrapper">
              <span class="input-icon">🛡</span>
              <select id="memberRole" required style="width: 100%; padding: 14px 16px 14px 44px; background: rgba(0,0,0,0.2); border: 1px solid var(--glass-border); border-radius: var(--radius-sm); color: var(--text-primary); outline: none;">
                <option value="" disabled selected>Select a role...</option>
                ${optionsHTML}
              </select>
            </div>
          </div>
        </div>

        <div style="display: flex; gap: 16px; margin-top: 16px;">
          <button type="submit" class="btn btn-primary">＋ Add Member</button>
          <button type="reset" class="btn btn-ghost">Clear</button>
        </div>
      </form>
    </div>
  `;

  document.getElementById('addMemberForm')?.addEventListener('submit', async function (e) {
    e.preventDefault();

    const name = document.getElementById('memberName').value.trim();
    const email = document.getElementById('memberEmail').value.trim();
    const password = document.getElementById('memberPassword').value.trim();
    const role = document.getElementById('memberRole').value;

    if (!name || !email || !password || !role) {
      toast('Missing Fields', 'Please fill in all required fields.', 'error');
      return;
    }

    try {
      const result = await API.members.add(name, email, password, role);
      toast('Member Added!', `${name} has been registered as ${roleLabel(role)}.`, 'success');
      this.reset();
      renderSection('addMember');
    } catch (error) {
      toast('Error', error.message, 'error');
    }
  });
}

async function renderViewMembers(container) {
  const session = JSON.parse(localStorage.getItem('user') || '{}');
  
  try {
    const { members } = await API.members.getAll();

    container.innerHTML = `
      <div class="section-header">
        <div>
          <h2 class="section-title">◉ All Members</h2>
          <p class="section-subtitle">${members.length} registered member${members.length !== 1 ? 's' : ''}</p>
        </div>
        ${session.role === 'admin' ? `<button class="btn btn-primary" onclick="navigateTo('addMember')">＋ Add Member</button>` : ''}
      </div>

      <div class="glass-panel">
        <div style="padding: 24px; border-bottom: 1px solid var(--glass-border);">
          <h3 style="font-size: 18px;">👥 Member Directory</h3>
        </div>
        ${members.length === 0 ? `
          <div style="padding: 40px; text-align: center; color: var(--text-muted);">No members found.</div>
        ` : `
          <div class="table-container">
            <table class="data-table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Name</th>
                  <th>Email</th>
                  <th>Role</th>
                  <th>Registered</th>
                  ${session.role === 'admin' ? '<th>Action</th>' : ''}
                </tr>
              </thead>
              <tbody>
                ${members.map((u, i) => `
                  <tr>
                    <td class="text-muted">${i + 1}</td>
                    <td>
                      <div style="display:flex; align-items:center; gap:12px;">
                        <div class="user-avatar" style="width:32px; height:32px; font-size:12px;">${u.name.charAt(0)}</div>
                        <span style="font-weight: 500;">${u.name}</span>
                      </div>
                    </td>
                    <td style="color: var(--text-secondary);">${u.email}</td>
                    <td><span class="role-badge ${u.role}">${roleLabel(u.role)}</span></td>
                    <td class="text-muted" style="font-size: 13px;">${new Date(u.created_at).toLocaleDateString('en-IN')}</td>
                    ${session.role === 'admin' ? `
                      <td>
                        ${u.role !== 'admin' ? `
                          <button onclick="deleteMember('${u.id}')" style="color: #F43F5E; background: rgba(244,63,94,0.1); width: 28px; height: 28px; border-radius: 6px; display: flex; align-items: center; justify-content: center; border: none; cursor: pointer; transition: all 0.2s;" title="Remove member" onmouseover="this.style.background='rgba(244,63,94,0.2)'" onmouseout="this.style.background='rgba(244,63,94,0.1)'">✕</button>
                        ` : '<span class="text-muted" style="font-size:11px;">—</span>'}
                      </td>
                    ` : ''}
                  </tr>
                `).join('')}
              </tbody>
            </table>
          </div>
        `}
      </div>
    `;
  } catch (error) {
    toast('Error', error.message, 'error');
    container.innerHTML = `<div class="glass-panel" style="padding: 40px; text-align: center; color: var(--text-muted);">Failed to load members</div>`;
  }
}

async function deleteMember(userId) {
  const ok = await showModal({
    icon: '🗑️',
    title: 'Remove Member',
    message: 'Are you sure you want to remove this member? This action cannot be undone.',
    confirmText: 'Remove',
    confirmClass: 'btn-rose',
  });
  if (!ok) return;

  try {
    await API.members.delete(userId);
    toast('Member Removed', 'Member has been deleted successfully.', 'success');
    renderSection('viewMembers');
  } catch (error) {
    toast('Error', error.message, 'error');
  }
}

async function renderAddEvent(container) {
  const session = JSON.parse(localStorage.getItem('user') || '{}');
  
  try {
    const { settings } = await API.admin.getSettings();
    const { events } = await API.events.getAll();

    if (!settings.allowAddingEvents && session.role !== 'admin') {
      container.innerHTML = `
        <div class="section-header">
          <div>
            <h2 class="section-title">✦ Add Event</h2>
          </div>
        </div>
        <div style="display: flex; align-items: center; gap: 14px; background: rgba(239, 68, 68, 0.08); border: 1px solid rgba(239, 68, 68, 0.2); border-radius: 12px; padding: 18px 22px;">
          <span style="font-size: 24px;">🚫</span>
          <div>
            <h4 style="color: #EF4444; margin-bottom: 4px;">Event Creation Disabled</h4>
            <p style="font-size: 14px; opacity: 0.8;">The Admin has disabled event creation.</p>
          </div>
        </div>
      `;
      return;
    }

    if (settings.isLocked) {
      container.innerHTML = `
        <div style="display: flex; align-items: center; gap: 14px; background: rgba(239, 68, 68, 0.08); border: 1px solid rgba(239, 68, 68, 0.2); border-radius: 12px; padding: 18px 22px;">
          <span style="font-size: 24px;">🔒</span>
          <div><h4 style="color: #EF4444; margin-bottom: 4px;">System Locked</h4><p>Cannot add events after finalization.</p></div>
        </div>
      `;
      return;
    }

    if (events.length >= settings.maxEvents) {
      container.innerHTML = `
        <div style="display: flex; align-items: center; gap: 14px; background: rgba(239, 68, 68, 0.08); border: 1px solid rgba(239, 68, 68, 0.2); border-radius: 12px; padding: 18px 22px;">
          <span style="font-size: 24px;">⛔</span>
          <div>
            <h4 style="color: #EF4444; margin-bottom: 4px;">Event Limit Reached</h4>
            <p>Maximum event limit of ${settings.maxEvents} has been reached.</p>
          </div>
        </div>
      `;
      return;
    }

    container.innerHTML = `
      <div class="section-header">
        <div>
          <h2 class="section-title">✦ Add Event</h2>
          <p class="section-subtitle">${events.length} of ${settings.maxEvents} events used</p>
        </div>
      </div>

      <div class="glass-panel" style="padding: 40px; margin-bottom: 32px;">
        <h3 style="margin-bottom: 24px;">🎉 Event Details</h3>
        <form id="addEventForm" autocomplete="off" style="display: flex; flex-direction: column; gap: 20px;">
          <div class="form-group">
            <label for="eventName">Event Name *</label>
            <div class="input-wrapper">
              <span class="input-icon">🎤</span>
              <input type="text" id="eventName" placeholder="e.g. Battle of Bands" required />
            </div>
          </div>
          <div class="form-group">
            <label for="eventDesc">Description *</label>
            <textarea id="eventDesc" placeholder="Describe the event briefly..." required style="width: 100%; padding: 14px; background: rgba(0,0,0,0.2); border: 1px solid var(--glass-border); border-radius: var(--radius-sm); color: var(--text-primary); min-height: 100px; outline: none;"></textarea>
          </div>
          <div class="form-actions" style="display: flex; gap: 12px;">
            <button type="submit" class="btn btn-primary">✦ Add Event</button>
            <button type="reset" class="btn btn-ghost">Clear</button>
          </div>
        </form>
      </div>

      <div class="glass-panel" style="padding: 24px;">
        <div style="margin-bottom: 16px;">
          <h3 style="font-size: 16px;">📊 Event Capacity</h3>
        </div>
        <div>
          <div style="height: 12px; background: rgba(255,255,255,0.05); border-radius: 10px; overflow: hidden; margin-bottom: 12px;">
            <div style="height: 100%; background: var(--accent-primary); width: ${(events.length / settings.maxEvents) * 100}%; transition: width 0.5s ease;"></div>
          </div>
          <p class="text-muted" style="font-size: 14px;">${events.length} / ${settings.maxEvents} events added</p>
        </div>
      </div>
    `;

    document.getElementById('addEventForm')?.addEventListener('submit', async function (e) {
      e.preventDefault();

      const name = document.getElementById('eventName').value.trim();
      const desc = document.getElementById('eventDesc').value.trim();

      if (!name || !desc) {
        toast('Missing Fields', 'Event name and description are required.', 'error');
        return;
      }

      try {
        await API.events.add(name, desc);
        toast('Event Added!', `"${name}" has been added successfully.`, 'success');
        this.reset();
        renderSection('addEvent');
      } catch (error) {
        toast('Error', error.message, 'error');
      }
    });
  } catch (error) {
    toast('Error', error.message, 'error');
    container.innerHTML = `<div class="glass-panel" style="padding: 40px; text-align: center; color: var(--text-muted);">Failed to load form</div>`;
  }
}

async function renderViewEvents(container) {
  const session = JSON.parse(localStorage.getItem('user') || '{}');
  
  try {
    const { events } = await API.events.getAll();

    container.innerHTML = `
      <div class="section-header">
        <div>
          <h2 class="section-title">≡ All Events</h2>
          <p class="section-subtitle">${events.length} event${events.length !== 1 ? 's' : ''}</p>
        </div>
        ${session.role === 'admin' || session.role === 'faculty' ? `
          <button class="btn btn-primary" onclick="navigateTo('addEvent')">✦ Add Event</button>
        ` : ''}
      </div>

      ${events.length === 0 ? `
        <div class="glass-panel" style="padding: 40px; text-align: center;">
          <span style="font-size: 40px; display: block; margin-bottom: 16px;">🎉</span>
          <p style="color: var(--text-muted);">No events have been added yet.</p>
        </div>
      ` : `
        <div class="glass-panel" style="padding: 0;">
          <div class="table-container" style="border: none; border-radius: 0;">
            <table class="data-table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Event Name</th>
                  <th>Description</th>
                  <th>Votes</th>
                  <th>Added</th>
                  ${session.role === 'admin' ? '<th>Action</th>' : ''}
                </tr>
              </thead>
              <tbody>
                ${events.map((ev, i) => `
                  <tr>
                    <td class="text-muted">${i + 1}</td>
                    <td style="font-weight: 500; color: var(--accent-glow);">${ev.name}</td>
                    <td style="max-width:260px; color:var(--text-secondary); font-size:14px;">${ev.description}</td>
                    <td>
                      <span class="status-badge" style="background: rgba(255,255,255,0.05); color: var(--text-primary);">🗳 ${ev.votes}</span>
                    </td>
                    <td class="text-muted" style="font-size: 13px;">${new Date(ev.created_at).toLocaleDateString('en-IN')}</td>
                    ${session.role === 'admin' ? `
                      <td>
                        <button onclick="deleteEvent('${ev.id}')" style="color: #F43F5E; background: rgba(244,63,94,0.1); width: 28px; height: 28px; border-radius: 6px; display: flex; align-items: center; justify-content: center; border: none; cursor: pointer; transition: all 0.2s;" title="Delete event" onmouseover="this.style.background='rgba(244,63,94,0.2)'" onmouseout="this.style.background='rgba(244,63,94,0.1)'">✕</button>
                      </td>
                    ` : ''}
                  </tr>
                `).join('')}
              </tbody>
            </table>
          </div>
        </div>
      `}
    `;
  } catch (error) {
    toast('Error', error.message, 'error');
    container.innerHTML = `<div class="glass-panel" style="padding: 40px; text-align: center; color: var(--text-muted);">Failed to load events</div>`;
  }
}

async function deleteEvent(eventId) {
  const ok = await showModal({
    icon: '🗑️',
    title: 'Delete Event',
    message: 'Delete this event? All related votes will be removed too.',
    confirmText: 'Delete',
    confirmClass: 'btn-rose',
  });

  if (!ok) return;

  try {
    await API.events.delete(eventId);
    toast('Event Deleted', 'Event has been removed.', 'success');
    renderSection('viewEvents');
  } catch (error) {
    toast('Error', error.message, 'error');
  }
}

async function renderVoteEvents(container) {
  const session = JSON.parse(localStorage.getItem('user') || '{}');
  
  try {
    const { settings } = await API.admin.getSettings();
    const { events } = await API.events.getAll();
    const voteStatus = await API.voting.getStatus();
    const myVote = voteStatus.has_voted ? voteStatus.vote : null;

    if (settings.isLocked) {
      container.innerHTML = `
        <div class="section-header">
          <div><h2 class="section-title">◈ Cast Your Vote</h2></div>
        </div>
        <div style="display: flex; align-items: center; gap: 14px; background: rgba(239, 68, 68, 0.08); border: 1px solid rgba(239, 68, 68, 0.2); border-radius: 12px; padding: 18px 22px;">
          <span style="font-size: 24px;">🔒</span>
          <div>
            <h4 style="color: #EF4444; margin-bottom: 4px;">System Locked</h4>
            <p style="font-size: 14px;">Voting has been closed after finalization.</p>
          </div>
        </div>
      `;
      return;
    }

    container.innerHTML = `
      <div class="section-header" style="margin-bottom: 32px;">
        <div>
          <h2 class="section-title">◈ Cast Your Vote</h2>
          <p class="section-subtitle">
            ${!settings.allowVoting
              ? '<span style="color: #EF4444;">⛔ Voting is currently disabled</span>'
              : myVote
                ? `<span style="color: var(--accent-emerald);">✅ You have voted for: <strong>${myVote.event_name}</strong></span>`
                : `Choose your favorite event`
            }
          </p>
        </div>
      </div>

      ${events.length === 0 ? `
        <div class="glass-panel" style="padding: 40px; text-align: center;">
          <span style="font-size: 40px; display: block; margin-bottom: 16px;">🎉</span>
          <p style="color: var(--text-muted);">No events available to vote on yet.</p>
        </div>
      ` : `
        <div class="events-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 24px;">
          ${events.map((ev, i) => {
            const voted = myVote?.event_id === ev.id;
            const hasVoted = !!myVote;

            return `
              <div class="glass-panel event-card" style="padding: 24px; display: flex; flex-direction: column; height: 100%; position: relative; overflow: hidden; border: 1px solid ${voted ? 'var(--accent-emerald)' : 'var(--glass-border)'}; box-shadow: ${voted ? '0 0 20px rgba(16,185,129,0.2)' : 'var(--glass-shadow)'};">
                
                <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 16px;">
                  <h3 style="font-size: 20px; line-height: 1.3;">${ev.name}</h3>
                  <span style="font-size: 32px; font-weight: 800; opacity: 0.1; line-height: 1;">${String(i + 1).padStart(2, '0')}</span>
                </div>
                
                <p style="color: var(--text-secondary); margin-bottom: 24px; flex: 1; font-size: 15px;">${ev.description}</p>
                
                <div style="display: flex; align-items: center; justify-content: space-between; border-top: 1px solid var(--glass-border); padding-top: 16px;">
                  <span class="status-badge" style="background: rgba(255,255,255,0.05); color: var(--text-primary);">🗳 ${ev.votes}</span>
                  
                  ${voted
                    ? `<span style="color: var(--accent-emerald); font-weight: 600; display: flex; align-items: center; gap: 6px;">✓ Voted</span>`
                    : `<button class="btn btn-primary btn-sm" onclick="castVote('${ev.id}')"
                        ${hasVoted || !settings.allowVoting ? 'disabled style="opacity:0.5; cursor:not-allowed; filter:grayscale(1);"' : ''}>
                        Vote Now
                      </button>`
                  }
                </div>
              </div>
            `;
          }).join('')}
        </div>
      `}
    `;
  } catch (error) {
    toast('Error', error.message, 'error');
    container.innerHTML = `<div class="glass-panel" style="padding: 40px; text-align: center; color: var(--text-muted);">Failed to load voting</div>`;
  }
}

async function castVote(eventId) {
  try {
    const result = await API.voting.vote(eventId);
    toast('Vote Cast!', `You voted for "${result.vote.event_name}". Thank you!`, 'success');
    
    // Save vote info locally
    localStorage.setItem('userVote', JSON.stringify({
      event_id: eventId,
      event_name: result.vote.event_name
    }));
    
    renderSection('voteEvents');
  } catch (error) {
    toast('Error', error.message, 'error');
  }
}

async function renderViewResults(container) {
  try {
    const { results, total_votes } = await API.voting.getResults();

    container.innerHTML = `
      <div class="section-header">
        <div>
          <h2 class="section-title">▦ Vote Results</h2>
          <p class="section-subtitle">${total_votes} total vote${total_votes !== 1 ? 's' : ''}</p>
        </div>
      </div>

      ${results.length === 0 ? `
        <div class="glass-panel" style="padding: 40px; text-align: center;">
          <span style="font-size: 40px; display: block; margin-bottom: 16px;">📊</span>
          <p style="color: var(--text-muted);">No results yet.</p>
        </div>
      ` : `
        <div style="display: flex; flex-direction: column; gap: 16px;">
          ${results.map((result, i) => `
            <div class="glass-panel" style="padding: 20px; animation: fadeInUp 0.5s ease both; animation-delay: ${i * 0.1}s; display: flex; flex-direction: column; gap: 12px;">
              <div style="display: flex; align-items: center; justify-content: space-between;">
                <div style="display: flex; align-items: center; gap: 16px;">
                  <div style="font-size: 24px; font-weight: 800; width: 40px; text-align: center; color: ${result.medal ? '#FBBF24' : 'var(--text-secondary)'};">${result.medal || result.rank}</div>
                  <h4 style="font-size: 16px; margin: 0;">${result.event_name}</h4>
                </div>
                <div style="text-align: right;">
                  <span style="font-size: 18px; font-weight: 700; color: var(--text-primary);">${result.votes}</span>
                  <span style="font-size: 12px; color: var(--text-secondary); margin-left: 4px;">votes</span>
                </div>
              </div>
              
              <div style="position: relative; height: 8px; background: rgba(255,255,255,0.05); border-radius: 10px; overflow: hidden;">
                <div style="position: absolute; left: 0; top: 0; height: 100%; width: ${result.percentage}%; background: linear-gradient(90deg, var(--accent-primary), var(--accent-secondary)); border-radius: 10px; transition: width 1s ease 0.2s;"></div>
              </div>
              
              <div style="display: flex; justify-content: flex-end;">
                <span style="font-size: 12px; color: var(--text-muted);">${result.percentage}% of total votes</span>
              </div>
            </div>
          `).join('')}
        </div>
      `}
    `;
  } catch (error) {
    toast('Error', error.message, 'error');
    container.innerHTML = `<div class="glass-panel" style="padding: 40px; text-align: center; color: var(--text-muted);">Failed to load results</div>`;
  }
}

async function renderSystemSettings(container) {
  try {
    const { settings } = await API.admin.getSettings();

    container.innerHTML = `
      <div class="section-header">
        <div>
          <h2 class="section-title">⚙️ System Settings</h2>
          <p class="section-subtitle">Control global system permissions</p>
        </div>
      </div>

      ${settings.isLocked ? `
        <div class="glass-panel" style="padding: 24px; margin-bottom: 24px; border-color: rgba(239,68,68,0.3); background: rgba(239,68,68,0.05); display: flex; align-items: center; justify-content: space-between;">
          <div style="display: flex; gap: 16px; align-items: center;">
            <span style="font-size: 24px;">🔒</span>
            <div>
              <h4 style="color: #EF4444; margin-bottom: 4px;">System Locked</h4>
              <p style="font-size: 14px; opacity: 0.8;">Unlock to modify settings.</p>
            </div>
          </div>
          <button class="btn btn-ghost" id="unlockBtn" style="border-color: #EF4444; color: #EF4444;">Unlock</button>
        </div>
      ` : ''}

      <div class="glass-panel" style="padding: 32px; margin-bottom: 24px;">
        <h3 style="margin-bottom: 24px; font-size: 18px;">Permissions</h3>
        <div style="display: grid; gap: 24px; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));">
          
          <div class="glass-panel" style="padding: 20px; display: flex; align-items: center; justify-content: space-between; background: rgba(0,0,0,0.2);">
            <div>
              <h4 style="font-size: 16px; margin-bottom: 4px;">✦ Allow Adding Events</h4>
              <p style="font-size: 13px; color: var(--text-secondary);">Faculty can create events</p>
            </div>
            <label class="switch">
              <input type="checkbox" id="toggleEvents" ${settings.allowAddingEvents ? 'checked' : ''} ${settings.isLocked ? 'disabled' : ''} style="transform: scale(1.5); accent-color: var(--accent-primary);"/>
            </label>
          </div>

          <div class="glass-panel" style="padding: 20px; display: flex; align-items: center; justify-content: space-between; background: rgba(0,0,0,0.2);">
            <div>
              <h4 style="font-size: 16px; margin-bottom: 4px;">🗳️ Allow Voting</h4>
              <p style="font-size: 13px; color: var(--text-secondary);">Users can cast votes</p>
            </div>
            <label class="switch">
              <input type="checkbox" id="toggleVoting" ${settings.allowVoting ? 'checked' : ''} ${settings.isLocked ? 'disabled' : ''} style="transform: scale(1.5); accent-color: var(--accent-emerald);"/>
            </label>
          </div>
        </div>
      </div>

      <div class="glass-panel" style="padding: 32px;">
        <h3 style="margin-bottom: 16px; font-size: 18px;">Events Configuration</h3>
        <div style="display: flex; gap: 16px; align-items: center; flex-wrap: wrap;">
          <p style="color: var(--text-secondary); flex: 1; min-width: 200px;">Maximum number of events allowed:</p>
          <div style="display: flex; gap: 12px;">
            <input type="number" id="maxEventsInput" value="${settings.maxEvents}" min="1" max="100" ${settings.isLocked ? 'disabled' : ''} 
                   style="width: 80px; padding: 10px; background: rgba(0,0,0,0.3); border: 1px solid var(--glass-border); border-radius: var(--radius-sm); color: white; text-align: center;" />
            <button class="btn btn-primary" id="saveMaxEvents" ${settings.isLocked ? 'disabled' : ''}>Save</button>
          </div>
        </div>
      </div>
    `;

    // Events
    document.getElementById('toggleEvents')?.addEventListener('change', async function () {
      try {
        await API.admin.updateSettings({ allowAddingEvents: this.checked });
        toast('Setting Saved', `Event adding is now ${this.checked ? 'allowed' : 'disabled'}.`, 'success');
      } catch (error) {
        toast('Error', error.message, 'error');
      }
    });

    document.getElementById('toggleVoting')?.addEventListener('change', async function () {
      try {
        await API.admin.updateSettings({ allowVoting: this.checked });
        toast('Setting Saved', `Voting is now ${this.checked ? 'enabled' : 'disabled'}.`, 'success');
      } catch (error) {
        toast('Error', error.message, 'error');
      }
    });

    document.getElementById('saveMaxEvents')?.addEventListener('click', async () => {
      const val = parseInt(document.getElementById('maxEventsInput').value);
      if (!val || val < 1) {
        toast('Invalid Value', 'Enter a number ≥ 1.', 'error');
        return;
      }
      try {
        await API.admin.updateSettings({ maxEvents: val });
        toast('Limit Updated', `Max events set to ${val}.`, 'success');
      } catch (error) {
        toast('Error', error.message, 'error');
      }
    });

    document.getElementById('unlockBtn')?.addEventListener('click', async () => {
      const ok = await showModal({
        icon: '🔓',
        title: 'Unlock System',
        message: 'This will allow voting and changes again. Continue?',
        confirmText: 'Unlock',
        confirmClass: 'btn-amber',
      });
      if (ok) {
        try {
          await API.admin.unlock();
          toast('System Unlocked', 'Settings are now editable.', 'success');
          renderSection('systemSettings');
        } catch (error) {
          toast('Error', error.message, 'error');
        }
      }
    });
  } catch (error) {
    toast('Error', error.message, 'error');
    container.innerHTML = `<div class="glass-panel" style="padding: 40px; text-align: center; color: var(--text-muted);">Failed to load settings</div>`;
  }
}

async function renderFinalizeEvents(container) {
  try {
    const { results } = await API.voting.getResults();
    const { settings } = await API.admin.getSettings();
    const { events } = await API.events.getAll();

    const isLocked = settings.isLocked;
    const finalized = settings.finalizedRank;

    container.innerHTML = `
      <div class="section-header">
        <div>
          <h2 class="section-title">★ Finalize Results</h2>
          <p class="section-subtitle">Select top N events and lock the system</p>
        </div>
      </div>

      ${isLocked ? `
        <div class="glass-panel" style="padding: 24px; border-left: 4px solid #EF4444; background: rgba(239, 68, 68, 0.1); margin-bottom: 32px; display: flex; align-items: center; gap: 16px;">
          <span style="font-size: 24px;">🔒</span>
          <div>
            <h4 style="color: #EF4444; margin-bottom: 4px;">Results Finalized</h4>
            <p style="font-size: 14px; opacity: 0.8;">System is locked. Top ${finalized} events shown below.</p>
          </div>
        </div>
      ` : ''}

      ${!isLocked ? `
        <div class="glass-panel" style="padding: 32px; margin-bottom: 32px;">
          <h3 style="margin-bottom: 16px;">🏆 Select Top N Events to Finalize</h3>
          <p style="color: var(--text-secondary); margin-bottom: 24px;">Choose how many top-ranked events to finalize. This will lock the system.</p>
          <div style="display: flex; gap: 12px; flex-wrap: wrap;">
            ${[5, 10, 20].map(n => `
              <button class="btn ${events.length < n ? 'btn-ghost' : 'btn-primary'}" 
                onclick="finalizeEvents(${n})"
                ${events.length < n ? 'disabled style="opacity: 0.5; cursor: not-allowed;"' : ''}>
                Top ${n}
              </button>
            `).join('')}
            <button class="btn btn-primary" style="background: linear-gradient(135deg, var(--accent-amber), #D97706); border: none;" onclick="finalizeEvents(${events.length})">
              All (${events.length})
            </button>
          </div>
          ${events.length === 0 ? `<p class="text-muted" style="margin-top:12px;">No events to finalize yet.</p>` : ''}
        </div>
      ` : ''}

      ${isLocked && finalized ? `
        <div class="glass-panel" style="padding: 0; overflow: hidden; margin-top: 32px;">
          <div style="padding: 24px; border-bottom: 1px solid var(--glass-border);">
            <h3>🏆 Top ${finalized} Finalized Events</h3>
          </div>
          <div style="padding: 24px; display: grid; gap: 16px; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));">
            ${results.slice(0, finalized).map((result, i) => `
              <div class="glass-panel" style="padding: 20px; display: flex; align-items: center; gap: 16px; background: rgba(255,255,255,0.02);">
                <div style="font-size: 24px; font-weight: 800; color: var(--accent-amber); width: 32px; text-align: center;">${i + 1}</div>
                <div>
                  <h4 style="margin-bottom: 4px;">${result.event_name}</h4>
                  <p style="color: var(--text-secondary); font-size: 13px;">${result.votes} vote${result.votes !== 1 ? 's' : ''}</p>
                </div>
              </div>
            `).join('')}
          </div>
        </div>
      ` : ''}

      ${!isLocked && events.length > 0 ? `
        <div class="glass-panel" style="padding: 0; margin-top: 32px;">
          <div style="padding: 24px; border-bottom: 1px solid var(--glass-border);">
            <h3>📊 Current Rankings Preview</h3>
          </div>
          <div class="table-container">
            <table class="data-table">
              <thead>
                <tr><th>Rank</th><th>Event</th><th>Votes</th></tr>
              </thead>
              <tbody>
                ${results.map((result, i) => `
                  <tr>
                    <td style="font-size: 16px;">${i === 0 ? '🥇' : i === 1 ? '🥈' : i === 2 ? '🥉' : `#${i + 1}`}</td>
                    <td style="font-weight: 500;">${result.event_name}</td>
                    <td><span style="background: rgba(255,255,255,0.05); color: var(--text-primary); padding: 4px 12px; border-radius: 20px; font-size: 13px;">🗳 ${result.votes}</span></td>
                  </tr>
                `).join('')}
              </tbody>
            </table>
          </div>
        </div>
      ` : ''}
    `;
  } catch (error) {
    toast('Error', error.message, 'error');
    container.innerHTML = `<div class="glass-panel" style="padding: 40px; text-align: center; color: var(--text-muted);">Failed to load finalization</div>`;
  }
}

async function finalizeEvents(n) {
  const { events } = await API.events.getAll();
  if (events.length === 0) {
    toast('No Events', 'Cannot finalize — no events exist.', 'error');
    return;
  }

  const ok = await showModal({
    icon: '🔒',
    title: `Finalize Top ${n} Events`,
    message: `This will lock the system and stop voting. Top ${n} events will be finalized.`,
    confirmText: 'Finalize & Lock',
    confirmClass: 'btn-rose',
  });

  if (!ok) return;

  try {
    await API.admin.finalize(n);
    toast('System Locked!', `Top ${n} events have been finalized.`, 'success');
    renderSection('finalizeEvents');
  } catch (error) {
    toast('Error', error.message, 'error');
  }
}

function formatDate(isoStr) {
  if (!isoStr) return '—';
  try {
    return new Date(isoStr).toLocaleDateString('en-IN', {
      day: '2-digit', month: 'short', year: 'numeric',
    });
  } catch { return isoStr; }
}


/* ============================================================
   SECTION 6 — LANDING & LOGIN
   ============================================================ */

function initLandingPage() {
  const form = document.getElementById('loginForm');
  const togglePw = document.getElementById('togglePw');
  const pwInput = document.getElementById('loginPassword');

  togglePw?.addEventListener('click', () => {
    const isText = pwInput.type === 'text';
    pwInput.type = isText ? 'password' : 'text';
    togglePw.textContent = isText ? '👁' : '🙈';
  });

  document.querySelectorAll('.demo-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.getElementById('loginEmail').value = btn.dataset.email;
      document.getElementById('loginPassword').value = btn.dataset.pw;
      btn.style.transform = 'scale(0.95)';
      setTimeout(() => btn.style.transform = '', 150);
      toast('Demo Credentials', `Loaded ${btn.textContent} account.`, 'info', 2500);
    });
  });

  form?.addEventListener('submit', async function (e) {
    e.preventDefault();

    const email = document.getElementById('loginEmail').value.trim().toLowerCase();
    const password = document.getElementById('loginPassword').value.trim();
    const btnText = document.querySelector('#loginBtn .btn-text');
    const btnLoader = document.querySelector('#loginBtn .btn-loader');

    if (btnText) btnText.classList.add('hidden');
    if (btnLoader) btnLoader.classList.remove('hidden');

    try {
      const result = await API.auth.login(email, password);

      API.setToken(result.token);
      localStorage.setItem('user', JSON.stringify(result.user));
      
      toast('Welcome Back!', `Logged in as ${result.user.name}.`, 'success');

      setTimeout(() => {
        initDashboard(result.user);
      }, 500);
    } catch (error) {
      toast('Login Failed', error.message, 'error');
      if (btnText) btnText.classList.remove('hidden');
      if (btnLoader) btnLoader.classList.add('hidden');
    }
  });
}


/* ============================================================
   SECTION 7 — DASHBOARD BOOTSTRAP
   ============================================================ */

function initDashboard(user) {
  showPage('dashboardPage');
  buildSidebar(user.role);
  navigateTo('overview');

  document.getElementById('menuToggle')?.addEventListener('click', openSidebar);
  document.getElementById('sidebarOverlay')?.addEventListener('click', closeSidebar);

  document.getElementById('logoutBtn')?.addEventListener('click', async () => {
    const ok = await showModal({
      icon: '⏻',
      title: 'Log Out',
      message: 'Are you sure you want to log out?',
      confirmText: 'Log Out',
      confirmClass: 'btn-rose',
    });
    if (ok) {
      API.removeToken();
      localStorage.removeItem('user');
      localStorage.removeItem('userVote');
      showPage('landingPage');
      toast('Logged Out', 'You have been signed out.', 'info');
      document.getElementById('loginForm')?.reset();
    }
  });

  document.getElementById('themeToggle')?.addEventListener('click', toggleTheme);
}


/* ============================================================
   SECTION 8 — APPLICATION INITIALIZATION
   ============================================================ */

function init() {
  initTheme();

  // Check if already logged in
  const token = API.getToken();
  if (token) {
    const user = JSON.parse(localStorage.getItem('user') || 'null');
    if (user) {
      initDashboard(user);
      return;
    } else {
      API.removeToken();
    }
  }

  // Show landing page
  showPage('landingPage');
  initLandingPage();
}

document.addEventListener('DOMContentLoaded', init);