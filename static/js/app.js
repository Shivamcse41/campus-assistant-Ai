/**
 * CampConnect Dashboard JavaScript
 * ─────────────────────────────────
 * Handles client-side routing, document upload, status fetching,
 * chat testing, and embed widget code rendering.
 */

const API = ''; // Backend is hosted on the same origin/port
let token = localStorage.getItem('cc_token');
let clientId = localStorage.getItem('cc_client_id');
let businessName = localStorage.getItem('cc_business');

// Redirect to login if not authenticated
if (!token || !clientId) {
  logout();
}

// ── INITIALIZATION ────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  // Populate basic profile info immediately from localStorage
  const sidebarBusiness = document.getElementById('sidebar-business');
  const sidebarClientId = document.getElementById('sidebar-client-id');
  if (sidebarBusiness) sidebarBusiness.textContent = businessName || 'My Business';
  if (sidebarClientId) sidebarClientId.textContent = `ID: ${clientId ? clientId.substring(0, 8) + '...' : ''}`;

  // Load profile details from API to verify token and refresh stats
  loadProfile();

  // Setup drag & drop for upload zones
  setupDragAndDrop('quick-upload-zone', 'quick-file-input', quickUpload);
  setupDragAndDrop('doc-upload-zone', 'doc-upload-input', uploadDocument);

  // Initialize embed code display
  renderEmbedCode();
});

// ── TOAST NOTIFICATIONS ───────────────────────────────────────────────────────
function showToast(msg, type = 'info') {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  const icons = { success: '✅', error: '❌', info: 'ℹ️' };
  toast.innerHTML = `<span>${icons[type] || 'ℹ️'}</span><span>${msg}</span>`;
  container.appendChild(toast);

  // Auto-remove after 4 seconds
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(20px)';
    toast.style.transition = 'all 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

// ── AUTHENTICATION & PROFILE ──────────────────────────────────────────────────
async function loadProfile() {
  try {
    const res = await fetch(`${API}/auth/me`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    
    if (res.status === 401 || res.status === 403) {
      showToast('Session expired. Please login again.', 'error');
      setTimeout(logout, 1500);
      return;
    }

    if (!res.ok) throw new Error('Failed to load profile');

    const data = await res.json();
    businessName = data.business_name;
    localStorage.setItem('cc_business', businessName);

    // Update Sidebar
    document.getElementById('sidebar-business').textContent = businessName;
    document.getElementById('sidebar-client-id').textContent = `ID: ${clientId}`;

    // Update Overview Stats
    document.getElementById('stat-docs').textContent = data.documents_uploaded;
    document.getElementById('stat-queries').textContent = data.total_queries;
    document.getElementById('stat-status').textContent = data.documents_uploaded > 0 ? 'Active' : 'Needs Docs';
    document.getElementById('stat-business-short').textContent = businessName;

    // Apply colored state to status badge
    const statusEl = document.getElementById('stat-status');
    if (data.documents_uploaded > 0) {
      statusEl.style.color = 'var(--success)';
    } else {
      statusEl.style.color = 'var(--accent)';
    }

  } catch (err) {
    console.error(err);
    showToast('Could not fetch account details', 'error');
  }
}

function logout() {
  localStorage.removeItem('cc_token');
  localStorage.removeItem('cc_client_id');
  localStorage.removeItem('cc_business');
  window.location.href = '/static/login.html';
}

// ── NAVIGATION / TAB SWITCHER ─────────────────────────────────────────────────
function showSection(sectionId) {
  const sections = ['overview', 'documents', 'chat', 'embed'];
  
  // Hide all sections, remove active class from nav items
  sections.forEach(s => {
    const secEl = document.getElementById(`section-${s}`);
    const navEl = document.getElementById(`nav-${s}`);
    if (secEl) secEl.classList.add('hidden');
    if (navEl) navEl.classList.remove('active');
  });

  // Show target section, set active nav item
  const targetSec = document.getElementById(`section-${sectionId}`);
  const targetNav = document.getElementById(`nav-${sectionId}`);
  if (targetSec) targetSec.classList.remove('hidden');
  if (targetNav) targetNav.classList.add('active');

  // Trigger section-specific loads
  if (sectionId === 'documents') {
    loadDocuments();
  } else if (sectionId === 'overview') {
    loadProfile();
  }
}

// ── DRAG AND DROP SETUP ───────────────────────────────────────────────────────
function setupDragAndDrop(zoneId, inputId, uploadCallback) {
  const zone = document.getElementById(zoneId);
  const input = document.getElementById(inputId);
  if (!zone || !input) return;

  ['dragenter', 'dragover'].forEach(eventName => {
    zone.addEventListener(eventName, (e) => {
      e.preventDefault();
      zone.classList.add('drag-over');
    }, false);
  });

  ['dragleave', 'drop'].forEach(eventName => {
    zone.addEventListener(eventName, (e) => {
      e.preventDefault();
      zone.classList.remove('drag-over');
    }, false);
  });

  zone.addEventListener('drop', (e) => {
    const dt = e.dataTransfer;
    const files = dt.files;
    if (files.length > 0) {
      input.files = files;
      uploadCallback(input);
    }
  });
}

// ── UPLOAD DOCUMENTS ──────────────────────────────────────────────────────────
function performUpload(fileInput, progressBarId, progressFillId, statusId) {
  const file = fileInput.files[0];
  if (!file) return;

  if (!file.name.toLowerCase().endsWith('.pdf')) {
    showToast('Please upload a PDF document.', 'error');
    return;
  }

  const progressBar = document.getElementById(progressBarId);
  const progressFill = document.getElementById(progressFillId);
  const statusText = document.getElementById(statusId);

  progressBar.classList.remove('hidden');
  progressFill.style.width = '0%';
  statusText.textContent = `Uploading ${file.name}...`;
  statusText.className = 'text-sm text-secondary mt-3';

  const formData = new FormData();
  formData.append('file', file);

  const xhr = new XMLHttpRequest();
  xhr.open('POST', `${API}/api/upload/${clientId}`, true);
  xhr.setRequestHeader('Authorization', `Bearer ${token}`);

  xhr.upload.onprogress = (e) => {
    if (e.lengthComputable) {
      const percent = Math.round((e.loaded / e.total) * 100);
      progressFill.style.width = `${percent}%`;
      statusText.textContent = `Uploading: ${percent}%`;
    }
  };

  xhr.onload = () => {
    progressBar.classList.add('hidden');
    fileInput.value = ''; // Reset file input

    let response = {};
    try {
      response = JSON.parse(xhr.responseText);
    } catch (e) {
      response = { message: 'Server error' };
    }

    if (xhr.status === 200) {
      statusText.textContent = response.message || 'Upload successful!';
      statusText.className = 'text-sm text-success mt-3';
      showToast('Document uploaded successfully!', 'success');
      loadProfile(); // Refresh stats
      if (document.getElementById('section-documents').classList.contains('hidden') === false) {
        loadDocuments(); // Refresh doc list if active
      }
    } else {
      statusText.textContent = response.detail || 'Upload failed.';
      statusText.className = 'text-sm text-danger mt-3';
      showToast(response.detail || 'Upload failed', 'error');
    }
  };

  xhr.onerror = () => {
    progressBar.classList.add('hidden');
    fileInput.value = '';
    statusText.textContent = 'Network error during upload.';
    statusText.className = 'text-sm text-danger mt-3';
    showToast('Network error during upload', 'error');
  };

  xhr.send(formData);
}

function quickUpload(input) {
  performUpload(input, 'quick-progress-bar', 'quick-progress-fill', 'quick-upload-status');
}

function uploadDocument(input) {
  performUpload(input, 'doc-progress-bar', 'doc-progress-fill', 'doc-upload-status');
}

// ── GET & LIST DOCUMENTS ──────────────────────────────────────────────────────
async function loadDocuments() {
  const container = document.getElementById('doc-list');
  if (!container) return;

  try {
    const res = await fetch(`${API}/api/documents/${clientId}`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });

    if (!res.ok) throw new Error('Failed to fetch documents');

    const docs = await res.json();
    if (docs.length === 0) {
      container.innerHTML = `
        <div class="text-sm text-muted" style="text-align:center;padding:2.5rem;">
          No documents uploaded yet. Add a PDF to configure your AI.
        </div>
      `;
      return;
    }

    container.innerHTML = docs.map(doc => {
      const date = new Date(doc.uploaded_at).toLocaleString();
      return `
        <div class="doc-item">
          <div class="doc-icon">📄</div>
          <div class="doc-name">
            <div>${escapeHTML(doc.filename)}</div>
            <div class="doc-meta">Uploaded: ${date} • Chunks: ${doc.num_chunks}</div>
          </div>
          <button class="btn btn-danger" onclick="deleteDocument('${doc.id}')" style="padding:0.4rem 0.8rem;font-size:0.8rem;">
            🗑 Delete
          </button>
        </div>
      `;
    }).join('');

  } catch (err) {
    console.error(err);
    container.innerHTML = `
      <div class="text-sm text-danger" style="text-align:center;padding:2.5rem;">
        Failed to load documents. Please check your database.
      </div>
    `;
  }
}

// ── DELETE DOCUMENT ───────────────────────────────────────────────────────────
async function deleteDocument(docId) {
  if (!confirm('Are you sure you want to delete this document? This will remove all associated AI context.')) {
    return;
  }

  try {
    const res = await fetch(`${API}/api/document/${clientId}/${docId}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${token}` }
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Delete failed');

    showToast(data.message || 'Document deleted successfully!', 'success');
    loadProfile(); // Refresh stats
    loadDocuments(); // Refresh doc list

  } catch (err) {
    console.error(err);
    showToast(err.message || 'Failed to delete document', 'error');
  }
}

// ── QUICK ASK & LIVE CHAT ─────────────────────────────────────────────────────
async function quickAsk() {
  const inputEl = document.getElementById('quick-question');
  const btn = document.getElementById('quick-ask-btn');
  const answerCard = document.getElementById('quick-answer');
  const answerText = document.getElementById('quick-answer-text');
  const answerSource = document.getElementById('quick-answer-source');

  const question = inputEl.value.trim();
  if (!question) return;

  btn.disabled = true;
  btn.textContent = 'Searching...';
  answerCard.style.display = 'none';

  try {
    const res = await fetch(`${API}/api/query/${clientId}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({ question })
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Query failed');

    answerCard.style.display = 'block';
    answerText.textContent = data.answer;

    if (data.sources && data.sources.length > 0) {
      const srcNames = [...new Set(data.sources.map(s => s.source))].join(', ');
      answerSource.textContent = `Sources: ${srcNames}`;
    } else {
      answerSource.textContent = 'Sources: None';
    }

  } catch (err) {
    console.error(err);
    showToast(err.message || 'Error executing query', 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = '🔍 Ask Question';
  }
}

async function sendMessage() {
  const inputEl = document.getElementById('chat-input');
  const msgContainer = document.getElementById('chat-messages');
  const question = inputEl.value.trim();
  if (!question) return;

  // Append user message
  appendMessage('user', question);
  inputEl.value = '';

  // Append thinking bubble
  const thinkingBubble = appendMessage('bot', `
    <div class="typing-dots">
      <span></span><span></span><span></span>
    </div>
  `);
  msgContainer.scrollTop = msgContainer.scrollHeight;

  try {
    const res = await fetch(`${API}/api/query/${clientId}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({ question })
    });

    const data = await res.json();
    thinkingBubble.remove(); // Remove thinking bubble

    if (!res.ok) throw new Error(data.detail || 'Query failed');

    // Append response bubble
    let botHTML = `<div>${escapeHTML(data.answer)}</div>`;
    if (data.sources && data.sources.length > 0) {
      const srcList = [...new Set(data.sources.map(s => `${s.source} (p. ${s.page})`))];
      botHTML += `<span class="source-tag">📚 Source: ${escapeHTML(srcList.join(', '))}</span>`;
    }
    appendMessage('bot', botHTML);

  } catch (err) {
    console.error(err);
    thinkingBubble.remove();
    appendMessage('bot', `<span style="color:var(--danger)">⚠️ Error: ${escapeHTML(err.message)}</span>`);
  }

  msgContainer.scrollTop = msgContainer.scrollHeight;
}

function appendMessage(sender, content) {
  const container = document.getElementById('chat-messages');
  const bubble = document.createElement('div');
  bubble.className = `chat-bubble ${sender}`;
  bubble.innerHTML = content;
  container.appendChild(bubble);
  return bubble;
}

function clearChat() {
  const container = document.getElementById('chat-messages');
  if (container) {
    container.innerHTML = `
      <div class="chat-bubble bot">
        👋 Hi! I'm your AI assistant. Upload some documents and ask me anything about them!
      </div>
    `;
  }
}

// ── EMBED WIDGET CODE GENERATION ──────────────────────────────────────────────
function renderEmbedCode() {
  const box = document.getElementById('embed-code-box');
  if (!box) return;

  const currentHost = window.location.origin;
  const scriptTag = `<!-- CampConnect Embed Chatbot Widget -->
<script 
  src="${currentHost}/static/widget.js" 
  data-client-id="${clientId}" 
  defer>
</script>`;

  box.textContent = scriptTag;
}

function copyEmbedCode() {
  const box = document.getElementById('embed-code-box');
  if (!box) return;

  navigator.clipboard.writeText(box.textContent)
    .then(() => {
      showToast('Embed script copied to clipboard!', 'success');
    })
    .catch(err => {
      console.error(err);
      showToast('Failed to copy. Please select and copy manually.', 'error');
    });
}

// ── UTILITIES ─────────────────────────────────────────────────────────────────
function escapeHTML(str) {
  if (!str) return '';
  return str.replace(/[&<>'"]/g, 
    tag => ({
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      "'": '&#39;',
      '"': '&quot;'
    }[tag] || tag)
  );
}
