/* =========================================================
   ResumeMate AI — app.js  (full rewrite, clean)
   Talks to the FastAPI backend at http://localhost:8000
   ========================================================= */

const API_BASE = 'http://localhost:8000';

/* ───────────────────────────────────────────────────────────
   STATE
─────────────────────────────────────────────────────────── */
let skills = [];
let generatedPDFBytes = null;
let generatedFilename = 'resume.pdf';
let _pdfBlobUrl = null;

/* ───────────────────────────────────────────────────────────
   NAV
─────────────────────────────────────────────────────────── */
function showSection(id) {
  document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
  document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
  document.getElementById(`section-${id}`).classList.add('active');
  document.getElementById(`nav-${id}`).classList.add('active');
}

/* ───────────────────────────────────────────────────────────
   API STATUS CHECK
─────────────────────────────────────────────────────────── */
async function checkAPIStatus() {
  const dot   = document.getElementById('api-status');
  const label = document.getElementById('api-status-label');
  try {
    const r = await fetch(`${API_BASE}/docs`, { method: 'HEAD', signal: AbortSignal.timeout(3000) });
    if (r.ok) {
      dot.className   = 'status-dot online';
      label.textContent = 'API Online';
    } else { throw new Error('not ok'); }
  } catch {
    dot.className   = 'status-dot offline';
    label.textContent = 'API Offline';
  }
}

/* ───────────────────────────────────────────────────────────
   SKILLS TAG INPUT
─────────────────────────────────────────────────────────── */
(function initSkills() {
  const input = document.getElementById('skills-input');
  if (!input) return;
  input.addEventListener('keydown', e => {
    if (e.key === 'Enter' || e.key === ',') { e.preventDefault(); addSkillFromInput(); }
  });
  input.addEventListener('blur', addSkillFromInput);
})();

function addSkillFromInput() {
  const input = document.getElementById('skills-input');
  const val = input.value.trim().replace(/,$/, '');
  if (val && !skills.includes(val)) { skills.push(val); renderSkills(); }
  input.value = '';
}
function removeSkill(skill) { skills = skills.filter(s => s !== skill); renderSkills(); }
function renderSkills() {
  const container = document.getElementById('skills-tags');
  container.innerHTML = '';
  skills.forEach(skill => {
    const tag = document.createElement('div');
    tag.className = 'tag';
    tag.innerHTML = `${skill} <button class="tag-remove" onclick="removeSkill('${skill.replace(/'/g,"\\'")}')">✕</button>`;
    container.appendChild(tag);
  });
}

/* ───────────────────────────────────────────────────────────
   DYNAMIC LIST BUILDERS
─────────────────────────────────────────────────────────── */
let expCount = 0;
function addExperience(data = {}) {
  const id = ++expCount;
  const container = document.getElementById('experience-list');
  const div = document.createElement('div');
  div.className = 'list-item'; div.id = `exp-${id}`;
  div.innerHTML = `
    <button class="remove-btn" onclick="removeItem('exp-${id}')">Remove</button>
    <div class="grid-2">
      <div class="field"><label>Job Title *</label><input type="text" id="exp-${id}-title" placeholder="Senior Software Engineer" value="${data.title||''}"/></div>
      <div class="field"><label>Company *</label><input type="text" id="exp-${id}-company" placeholder="Acme Corp" value="${data.company||''}"/></div>
      <div class="field"><label>Location</label><input type="text" id="exp-${id}-location" placeholder="San Francisco, CA" value="${data.location||''}"/></div>
      <div class="field"><label>Start Date *</label><input type="text" id="exp-${id}-start" placeholder="2020-03-01" value="${data.start_date||''}"/></div>
      <div class="field"><label>End Date</label><input type="text" id="exp-${id}-end" placeholder="Present" value="${data.end_date||'Present'}"/></div>
    </div>
    <div class="field" style="margin-top:10px">
      <label>Bullet Points</label>
      <div class="bullets-container" id="exp-${id}-bullets"></div>
      <button class="add-bullet-btn" onclick="addBullet('exp-${id}-bullets')">+ Add bullet</button>
    </div>`;
  container.appendChild(div);
  (data.description || ['']).forEach(b => addBullet(`exp-${id}-bullets`, b));
}

let eduCount = 0;
function addEducation(data = {}) {
  const id = ++eduCount;
  const container = document.getElementById('education-list');
  const div = document.createElement('div');
  div.className = 'list-item'; div.id = `edu-${id}`;
  div.innerHTML = `
    <button class="remove-btn" onclick="removeItem('edu-${id}')">Remove</button>
    <div class="grid-2">
      <div class="field"><label>Degree *</label><input type="text" id="edu-${id}-degree" placeholder="B.Sc. Computer Science" value="${data.degree||''}"/></div>
      <div class="field"><label>Institution *</label><input type="text" id="edu-${id}-inst" placeholder="MIT" value="${data.institution||''}"/></div>
      <div class="field"><label>Location</label><input type="text" id="edu-${id}-location" placeholder="Cambridge, MA" value="${data.location||''}"/></div>
      <div class="field"><label>Graduation Year</label><input type="text" id="edu-${id}-year" placeholder="2023" value="${data.graduation_year||''}"/></div>
      <div class="field"><label>GPA</label><input type="text" id="edu-${id}-gpa" placeholder="3.8" value="${data.gpa||''}"/></div>
    </div>`;
  container.appendChild(div);
}

let projCount = 0;
function addProject(data = {}) {
  const id = ++projCount;
  const container = document.getElementById('projects-list');
  const div = document.createElement('div');
  div.className = 'list-item'; div.id = `proj-${id}`;
  div.innerHTML = `
    <button class="remove-btn" onclick="removeItem('proj-${id}')">Remove</button>
    <div class="grid-2">
      <div class="field"><label>Project Title *</label><input type="text" id="proj-${id}-title" placeholder="E-commerce Platform" value="${data.title||''}"/></div>
      <div class="field"><label>Technologies</label><input type="text" id="proj-${id}-tech" placeholder="React, Node.js, MongoDB" value="${data.technologies||''}"/></div>
      <div class="field"><label>Link</label><input type="url" id="proj-${id}-link" placeholder="https://github.com/..." value="${data.link||''}"/></div>
      <div class="field"><label>Date</label><input type="text" id="proj-${id}-date" placeholder="2024-01-15" value="${data.date||''}"/></div>
    </div>
    <div class="field" style="margin-top:10px"><label>Description *</label><textarea id="proj-${id}-desc" rows="2" placeholder="A scalable platform that…">${data.description||''}</textarea></div>`;
  container.appendChild(div);
}

let certCount = 0;
function addCertification(data = {}) {
  const id = ++certCount;
  const container = document.getElementById('certifications-list');
  const div = document.createElement('div');
  div.className = 'list-item'; div.id = `cert-${id}`;
  div.innerHTML = `
    <button class="remove-btn" onclick="removeItem('cert-${id}')">Remove</button>
    <div class="grid-2">
      <div class="field"><label>Certification Name *</label><input type="text" id="cert-${id}-name" placeholder="AWS Solutions Architect" value="${data.name||''}"/></div>
      <div class="field"><label>Issuer *</label><input type="text" id="cert-${id}-issuer" placeholder="Amazon Web Services" value="${data.issuer||''}"/></div>
      <div class="field"><label>Date</label><input type="text" id="cert-${id}-date" placeholder="2023-06-01" value="${data.date||''}"/></div>
    </div>`;
  container.appendChild(div);
}

let bulletCount = 0;
function addBullet(containerId, value = '') {
  const id = ++bulletCount;
  const container = document.getElementById(containerId);
  const row = document.createElement('div');
  row.className = 'bullet-row'; row.id = `bullet-${id}`;
  row.innerHTML = `
    <input type="text" id="bullet-${id}-val" placeholder="Bullet point describing achievement…" value="${value}" />
    <button class="bullet-remove" onclick="removeItem('bullet-${id}')">✕</button>`;
  container.appendChild(row);
}

function removeItem(id) {
  const el = document.getElementById(id);
  if (!el) return;
  el.style.transition = 'opacity .15s ease, transform .15s ease';
  el.style.opacity = '0'; el.style.transform = 'translateY(-4px)';
  setTimeout(() => el.remove(), 150);
}

/* ───────────────────────────────────────────────────────────
   COLLECT FORM DATA
─────────────────────────────────────────────────────────── */
function collectFormData() {
  const g = id => document.getElementById(id)?.value.trim() || '';
  const achievements = document.getElementById('achievements').value
    .split('\n').map(s => s.trim()).filter(Boolean);

  const experience = [];
  document.querySelectorAll('[id^="exp-"]').forEach(el => {
    if (!el.classList.contains('list-item')) return;
    const id = el.id;
    const bullets = [];
    document.querySelectorAll(`#${id}-bullets .bullet-row`).forEach(row => {
      const v = row.querySelector('input')?.value.trim();
      if (v) bullets.push(v);
    });
    experience.push({
      title: g(`${id}-title`), company: g(`${id}-company`),
      location: g(`${id}-location`), start_date: g(`${id}-start`),
      end_date: g(`${id}-end`) || 'Present', description: bullets
    });
  });

  const education = [];
  document.querySelectorAll('[id^="edu-"]').forEach(el => {
    if (!el.classList.contains('list-item')) return;
    const id = el.id;
    education.push({
      degree: g(`${id}-degree`), institution: g(`${id}-inst`),
      location: g(`${id}-location`), graduation_year: g(`${id}-year`), gpa: g(`${id}-gpa`)
    });
  });

  const projects = [];
  document.querySelectorAll('[id^="proj-"]').forEach(el => {
    if (!el.classList.contains('list-item')) return;
    const id = el.id;
    projects.push({
      title: g(`${id}-title`), description: g(`${id}-desc`),
      technologies: g(`${id}-tech`), link: g(`${id}-link`), date: g(`${id}-date`)
    });
  });

  const certifications = [];
  document.querySelectorAll('[id^="cert-"]').forEach(el => {
    if (!el.classList.contains('list-item')) return;
    const id = el.id;
    certifications.push({ name: g(`${id}-name`), issuer: g(`${id}-issuer`), date: g(`${id}-date`) });
  });

  return {
    name: g('name'), title: g('title'), email: g('email'),
    phone: g('phone') || undefined, location: g('location') || undefined,
    linkedin_url: g('linkedin') || undefined, github_url: g('github') || undefined,
    portfolio_url: g('portfolio') || undefined, summary: g('summary') || undefined,
    skills, experience, education, projects, certifications, achievements,
    additional_info: g('additional_info') || undefined
  };
}

/* ───────────────────────────────────────────────────────────
   GENERATE RESUME
─────────────────────────────────────────────────────────── */
async function generateResume() {
  const data = collectFormData();
  if (!data.name || !data.title || !data.email) {
    showToast('⚠️ Please fill in Name, Title, and Email.'); return;
  }
  showResult('processing');
  animatePipeline();

  const formData = new FormData();
  formData.append('data', JSON.stringify(data));

  try {
    const response = await fetch(`${API_BASE}/process-resume`, { method: 'POST', body: formData });
    if (!response.ok) {
      let errMsg = `Server error ${response.status}`;
      try { const b = await response.json(); errMsg = b.detail?.message || JSON.stringify(b.detail) || errMsg; } catch {}
      throw new Error(errMsg);
    }
    const metaHeader = response.headers.get('X-Metadata');
    const metadata   = metaHeader ? JSON.parse(metaHeader) : {};
    generatedPDFBytes = await response.blob();
    generatedFilename = metadata.filename || 'resume.pdf';
    showResultCard(metadata);
  } catch (err) {
    showResult('error');
    document.getElementById('error-msg').textContent = err.message;
  }
}

function animatePipeline() {
  const steps = document.querySelectorAll('.step');
  steps.forEach(s => s.classList.remove('active', 'done'));
  let i = 0;
  const interval = setInterval(() => {
    if (i > 0) { steps[i-1].classList.remove('active'); steps[i-1].classList.add('done'); }
    if (i >= steps.length) { clearInterval(interval); return; }
    steps[i].classList.add('active');
    i++;
  }, 1800);
}

function showResult(mode) {
  document.getElementById('result-placeholder').style.display = mode === 'placeholder' ? 'block' : 'none';
  document.getElementById('processing-panel').style.display   = mode === 'processing'  ? 'block' : 'none';
  document.getElementById('result-card').style.display        = mode === 'result'      ? 'block' : 'none';
  document.getElementById('error-card').style.display         = mode === 'error'       ? 'block' : 'none';
}

function showResultCard(metadata) {
  showResult('result');
  const score = metadata.ats_score || 0;
  animateNumber(document.getElementById('score-number'), 0, score, 1200);
  const offset = 314 - (score / 100) * 314;
  setTimeout(() => { document.getElementById('ring-fill').style.strokeDashoffset = offset; }, 100);
  const { grade, color } = getGrade(score);
  const gradeEl = document.getElementById('score-grade');
  gradeEl.textContent = grade; gradeEl.style.color = color;
  renderFeedback('feedback-section', metadata.ats_feedback || {});
  const logEl = document.getElementById('log-content');
  logEl.innerHTML = '';
  [...(metadata.processing_steps||[]), ...(metadata.errors||[]).map(e => '❌ ' + e)]
    .forEach(s => { const d = document.createElement('div'); d.textContent = s; logEl.appendChild(d); });
}

/* ───────────────────────────────────────────────────────────
   SCORE RING GRADIENT
─────────────────────────────────────────────────────────── */
document.querySelectorAll('.score-ring').forEach(svg => {
  svg.insertAdjacentHTML('afterbegin', `
    <defs>
      <linearGradient id="ring-grad" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0%"   stop-color="#7C5CFC"/>
        <stop offset="50%"  stop-color="#3B82F6"/>
        <stop offset="100%" stop-color="#10B981"/>
      </linearGradient>
    </defs>`);
});

/* ───────────────────────────────────────────────────────────
   RENDER ATS FEEDBACK
─────────────────────────────────────────────────────────── */
function renderFeedback(containerId, feedback) {
  const container = document.getElementById(containerId);
  container.innerHTML = '';
  if (!feedback || !Object.keys(feedback).length) {
    container.innerHTML = '<p style="color:var(--text-3);font-size:.85rem">No detailed feedback available.</p>';
    return;
  }
  const map = {
    strengths:       { label: '✅ Strengths',        cls: 'pos' },
    weaknesses:      { label: '⚠️ Areas to Improve',  cls: 'neg' },
    improvements:    { label: '💡 Recommendations',   cls: 'neg' },
    recommendations: { label: '💡 Recommendations',   cls: 'neg' },
    keywords:        { label: '🔑 Keywords',           cls: 'neu' },
    suggestions:     { label: '💡 Suggestions',        cls: 'neu' },
  };
  Object.entries(feedback).forEach(([key, value]) => {
    if (key === 'score' || !value) return;
    const meta = map[key] || { label: key.replace(/_/g,' ').replace(/\b\w/g,c=>c.toUpperCase()), cls: 'neu' };
    const items = Array.isArray(value) ? value : [String(value)];
    if (!items.length) return;
    const sec = document.createElement('div');
    sec.className = 'feedback-category';
    sec.innerHTML = `<h4>${meta.label}</h4><ul class="feedback-list">${items.map(i=>`<li class="${meta.cls}">${i}</li>`).join('')}</ul>`;
    container.appendChild(sec);
  });
}

/* ───────────────────────────────────────────────────────────
   GRADE + PILL
─────────────────────────────────────────────────────────── */
function getGrade(score) {
  if (score >= 90) return { grade: '🌟 Excellent — ATS Ready!',    color: 'var(--green-l)' };
  if (score >= 75) return { grade: '👍 Good — Minor Tweaks Needed', color: 'var(--blue-l)'  };
  if (score >= 60) return { grade: '📝 Average — Needs Work',       color: '#FCD34D'        };
  return               { grade: '⚠️ Below Average — Revamp Needed', color: '#F87171'        };
}
function scorePillClass(score) {
  if (score >= 90) return 'great';
  if (score >= 75) return 'good';
  if (score >= 60) return 'avg';
  return 'low';
}

/* ───────────────────────────────────────────────────────────
   DOWNLOAD PDF (builder result)
─────────────────────────────────────────────────────────── */
function downloadPDF() {
  if (!generatedPDFBytes) { showToast('⚠️ No PDF available.'); return; }
  const url = URL.createObjectURL(generatedPDFBytes);
  const a = document.createElement('a');
  a.href = url; a.download = generatedFilename; a.click();
  URL.revokeObjectURL(url);
  showToast('✅ PDF downloaded!');
}

/* ───────────────────────────────────────────────────────────
   ATS SCORE SECTION (PDF upload)
─────────────────────────────────────────────────────────── */
let selectedPDFFile = null;

function handleDragOver(e)  { e.preventDefault(); document.getElementById('upload-zone').classList.add('drag-over'); }
function handleDragLeave()  { document.getElementById('upload-zone').classList.remove('drag-over'); }
function handleDrop(e) {
  e.preventDefault();
  document.getElementById('upload-zone').classList.remove('drag-over');
  const file = e.dataTransfer.files[0];
  if (file && file.type === 'application/pdf') setSelectedFile(file);
  else showToast('⚠️ Please drop a PDF file.');
}
function handleFileSelect(e) { const f = e.target.files[0]; if (f) setSelectedFile(f); }
function setSelectedFile(file) {
  selectedPDFFile = file;
  document.getElementById('upload-zone').style.display = 'none';
  document.getElementById('selected-file').style.display = 'flex';
  document.getElementById('file-name-label').textContent = file.name;
}
function removeFile() {
  selectedPDFFile = null;
  document.getElementById('pdf-upload').value = '';
  document.getElementById('upload-zone').style.display = 'block';
  document.getElementById('selected-file').style.display = 'none';
  document.getElementById('score-result-card').style.display = 'none';
}

async function scoreResume() {
  if (!selectedPDFFile) { showToast('⚠️ Please select a PDF file first.'); return; }
  const nameInput = document.getElementById('ats-name');
  const candidateName = nameInput ? nameInput.value.trim() : '';
  if (!candidateName) {
    showToast('⚠️ Please enter your Full Name first.');
    if (nameInput) nameInput.focus();
    return;
  }
  const btn = document.getElementById('score-btn');
  btn.disabled = true;
  btn.querySelector('.generate-btn-inner').textContent = '⏳ Analyzing…';
  const formData = new FormData();
  formData.append('file', selectedPDFFile);
  formData.append('candidate_name', candidateName);
  try {
    const response = await fetch(`${API_BASE}/process-pdf`, { method: 'POST', body: formData });
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || `Error ${response.status}`);
    showScoreResult(result);
  } catch (err) {
    showToast(`❌ ${err.message}`);
  } finally {
    btn.disabled = false;
    btn.querySelector('.generate-btn-inner').innerHTML = `
      <svg class="btn-icon" viewBox="0 0 20 20" fill="none"><path d="M10 3a7 7 0 100 14A7 7 0 0010 3zm0 2v5l3 3" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>
      Analyze Resume`;
  }
}

function showScoreResult(result) {
  const card = document.getElementById('score-result-card');
  card.style.display = 'block';
  card.style.animation = 'none'; void card.offsetWidth; card.style.animation = 'fadeUp .4s ease';
  const score = result.ats_score || 0;
  animateNumber(document.getElementById('score-number-2'), 0, score, 1200);
  setTimeout(() => { document.getElementById('ring-fill-2').style.strokeDashoffset = 314 - (score/100)*314; }, 100);
  const { grade, color } = getGrade(score);
  const gradeEl = document.getElementById('score-grade-2');
  gradeEl.textContent = grade; gradeEl.style.color = color;
  renderFeedback('feedback-section-2', result.ats_feedback || {});
}

/* ───────────────────────────────────────────────────────────
   LEADERBOARD
─────────────────────────────────────────────────────────── */
async function loadLeaderboard() {
  const body = document.getElementById('leaderboard-body');
  body.innerHTML = '<div class="lb-loading"><div class="mini-spinner"></div>Loading…</div>';
  try {
    const res  = await fetch(`${API_BASE}/leaderboard`);
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || `Error ${res.status}`);
    renderLeaderboard(data.leaderboard || []);
  } catch (err) {
    body.innerHTML = `<div class="lb-empty">⚠️ ${err.message}</div>`;
  }
}

function renderLeaderboard(rows) {
  const body = document.getElementById('leaderboard-body');
  if (!rows.length) { body.innerHTML = '<div class="lb-empty">No entries yet. Be the first!</div>'; return; }
  body.innerHTML = rows.map((row, i) => {
    const rank = i + 1;
    const rankClass = rank <= 3 ? `top-${rank}` : '';
    const displayName = (row.name || 'Anonymous').replace(/_/g, ' ');
    const pillCls = scorePillClass(row.ats_score);
    let pdfUrl = row.pdf_url || '';
    if (pdfUrl && !pdfUrl.startsWith('http')) {
      pdfUrl = `${API_BASE}${pdfUrl}`;
    }
    const safeUrl = pdfUrl.replace(/'/g, "\\'");
    const safeName = displayName.replace(/'/g, "\\'");
    const linkHtml = pdfUrl
      ? `<button class="view-link" onclick="openPdfModal('${safeUrl}','${safeName}')">View ↗</button>`
      : `<span style="color:var(--text-3);font-size:.78rem">—</span>`;
    return `
      <div class="lb-row">
        <div class="lb-col lb-rank ${rankClass}">${rank}</div>
        <div class="lb-col lb-name-cell">${displayName}</div>
        <div class="lb-col lb-score-cell"><span class="score-pill ${pillCls}">${row.ats_score}/100</span></div>
        <div class="lb-col lb-link-cell">${linkHtml}</div>
      </div>`;
  }).join('');
}

/* ───────────────────────────────────────────────────────────
   PDF PREVIEW MODAL  — inject HTML once
─────────────────────────────────────────────────────────── */
(function injectPdfModal() {
  const el = document.createElement('div');
  el.id = 'pdf-modal';
  el.innerHTML = `
    <div class="pdf-modal-backdrop" onclick="closePdfModal()"></div>
    <div class="pdf-modal-box">
      <div class="pdf-modal-header">
        <span class="pdf-modal-title" id="pdf-modal-title">PDF Preview</span>
        <div class="pdf-modal-actions">
          <a class="pdf-download-btn" id="pdf-modal-dl" href="#" target="_blank">⬇ Open / Download</a>
          <button class="pdf-modal-close" onclick="closePdfModal()">✕</button>
        </div>
      </div>
      <div class="pdf-modal-body" id="pdf-modal-body"></div>
    </div>`;
  document.body.appendChild(el);
})();

/* ── openPdfModal ─────────────────────────────────────────── */
async function openPdfModal(url, name) {
  const modal = document.getElementById('pdf-modal');
  const body  = document.getElementById('pdf-modal-body');
  const title = document.getElementById('pdf-modal-title');
  const dlBtn = document.getElementById('pdf-modal-dl');

  title.textContent = name + "'s Resume";
  dlBtn.href = url;

  // Show modal with spinner immediately
  body.innerHTML = `
    <div class="pdf-loading">
      <div class="pdf-spinner">
        <div class="spinner-ring"></div>
        <div class="spinner-ring delay1"></div>
      </div>
      <p class="pdf-loading-text">Loading PDF…</p>
    </div>`;
  modal.classList.add('open');
  document.body.style.overflow = 'hidden';

  if (_pdfBlobUrl) { URL.revokeObjectURL(_pdfBlobUrl); _pdfBlobUrl = null; }

  // Strategy 1: fetch → blob → embed  (works when CORS is open)
  try {
    const resp = await fetch(url, { cache: 'no-store' });
    if (!resp.ok) {
      if (resp.status === 401 || resp.status === 403) {
        throw new Error("UNAUTHORIZED");
      }
      throw new Error(`HTTP ${resp.status}`);
    }
    const buf  = await resp.arrayBuffer();
    const blob = new Blob([buf], { type: 'application/pdf' });
    _pdfBlobUrl = URL.createObjectURL(blob);
    body.innerHTML = `<embed src="${_pdfBlobUrl}" type="application/pdf" style="width:100%;height:100%;border:none;display:block;">`;
    return;
  } catch (e) {
    console.warn('[PDF Modal] fetch failed:', e.message);
    if (e.message === "UNAUTHORIZED" || url.includes("cloudinary.com")) {
      showCloudinaryFallback(body, url);
      return;
    }
  }

  // Strategy 2: direct embed  (Cloudinary raw URLs serve correct Content-Type now)
  body.innerHTML = `<embed src="${url}" type="application/pdf" style="width:100%;height:100%;border:none;display:block;">`;
}

function showCloudinaryFallback(body, url) {
  body.innerHTML = `
    <div class="pdf-fallback" style="display:flex; flex-direction:column; align-items:center; justify-content:center; text-align:center; padding: 2.5rem 1.5rem;">
      <div class="pdf-fallback-icon" style="font-size:3rem; margin-bottom:1rem; animation: pulse 2s infinite;">⚠️</div>
      <p style="color:var(--text-1);font-size:1.1rem;font-weight:700;margin:0 0 0.5rem 0;font-family:var(--font-display)">
        Cloudinary PDF Delivery Blocked
      </p>
      <p style="color:var(--text-2);font-size:.9rem;margin:0 0 1.5rem 0;max-width:380px;line-height:1.6">
        This historical resume PDF is hosted on Cloudinary, which restricts raw PDF delivery by default.<br><br>
        <strong>To fix this preview:</strong> Log in to your Cloudinary Console, navigate to <em>Settings -> Security</em>, scroll to <em>Restricted Media Types</em>, and check the box to <strong>"Allow delivery of PDF and ZIP files"</strong>.
      </p>
      <a href="${url}" target="_blank" download
         style="display:inline-block;padding:12px 28px;border-radius:12px;
                background:linear-gradient(135deg,var(--purple),#A855F7);color:#fff;
                font-weight:700;text-decoration:none;font-family:var(--font-display);font-size:.9rem;box-shadow: 0 4px 12px rgba(168,85,247,0.3)">
        ↗ Open PDF directly
      </a>
    </div>`;
}

/* ── Fallback when all preview strategies fail ─────────────── */
function showPdfFallback(body, url) {
  body.innerHTML = `
    <div class="pdf-fallback" style="display:flex">
      <div class="pdf-fallback-icon">📄</div>
      <p style="color:var(--text-2);font-size:.93rem;margin:0;max-width:320px;line-height:1.6">
        Inline preview is unavailable for this PDF.<br>Click below to open or download it.
      </p>
      <a href="${url}" target="_blank"
         style="margin-top:4px;display:inline-block;padding:13px 32px;border-radius:12px;
                background:linear-gradient(135deg,var(--purple),#A855F7);color:#fff;
                font-weight:700;text-decoration:none;font-family:var(--font-display);font-size:.95rem">
        ↗ Open PDF in New Tab
      </a>
    </div>`;
}

/* ── closePdfModal ────────────────────────────────────────── */
function closePdfModal() {
  const modal = document.getElementById('pdf-modal');
  const body  = document.getElementById('pdf-modal-body');
  modal.classList.remove('open');
  document.body.style.overflow = '';
  setTimeout(() => {
    body.innerHTML = '';
    if (_pdfBlobUrl) { URL.revokeObjectURL(_pdfBlobUrl); _pdfBlobUrl = null; }
  }, 300);
}

document.addEventListener('keydown', e => { if (e.key === 'Escape') closePdfModal(); });

/* ───────────────────────────────────────────────────────────
   TOAST
─────────────────────────────────────────────────────────── */
let toastTimeout;
function showToast(msg, duration = 3000) {
  const toast = document.getElementById('toast');
  toast.textContent = msg;
  toast.classList.add('show');
  clearTimeout(toastTimeout);
  toastTimeout = setTimeout(() => toast.classList.remove('show'), duration);
}

/* ───────────────────────────────────────────────────────────
   ANIMATE NUMBER
─────────────────────────────────────────────────────────── */
function animateNumber(el, from, to, duration) {
  const startTime = performance.now();
  function tick(now) {
    const elapsed = Math.min((now - startTime) / duration, 1);
    const eased   = 1 - Math.pow(1 - elapsed, 3);
    el.textContent = Math.round(from + (to - from) * eased);
    if (elapsed < 1) requestAnimationFrame(tick);
  }
  requestAnimationFrame(tick);
}

/* ───────────────────────────────────────────────────────────
   LOAD EXAMPLE DATA
─────────────────────────────────────────────────────────── */
function loadExampleData() {
  document.getElementById('name').value      = 'John Doe';
  document.getElementById('title').value     = 'Senior Software Engineer';
  document.getElementById('email').value     = 'john.doe@example.com';
  document.getElementById('phone').value     = '+1 (555) 123-4567';
  document.getElementById('location').value  = 'San Francisco, CA';
  document.getElementById('linkedin').value  = 'https://linkedin.com/in/johndoe';
  document.getElementById('github').value    = 'https://github.com/johndoe';
  document.getElementById('portfolio').value = 'https://johndoe.dev';
  document.getElementById('summary').value   = 'Experienced software engineer with 8+ years in full-stack development, specializing in Python, FastAPI, and cloud-native applications.';
  document.getElementById('achievements').value =
    'Employee of the Year 2022 at Tech Innovations Inc.\nPublished research paper at ACM Conference 2021\nOpen source contributor with 500+ GitHub stars';
  document.getElementById('additional_info').value =
    'Available for remote work. Fluent in English and Spanish.';

  skills = ['Python','FastAPI','JavaScript','React','AWS','Docker','PostgreSQL','MongoDB','Git','CI/CD'];
  renderSkills();

  addExperience({
    title: 'Senior Software Engineer', company: 'Tech Innovations Inc.',
    location: 'San Francisco, CA', start_date: '2020-03-01', end_date: 'Present',
    description: ['Led development of microservices serving 1M+ users','Implemented CI/CD pipeline reducing deployment time by 70%']
  });
  addEducation({ degree: 'M.Sc. Computer Science', institution: 'Stanford University', location: 'Stanford, CA', graduation_year: '2015', gpa: '3.8' });
  addProject({
    title: 'Resume Builder API', description: 'FastAPI service for processing resumes with structured data validation',
    technologies: 'Python, FastAPI, PyMuPDF, Pydantic', link: 'https://github.com/johndoe/resume-builder', date: '2024-01-15'
  });
  addCertification({ name: 'AWS Certified Solutions Architect', issuer: 'Amazon Web Services', date: '2022-11-15' });

  showToast('✅ Example data loaded!');
}

/* ───────────────────────────────────────────────────────────
   INIT
─────────────────────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  checkAPIStatus();
  setInterval(checkAPIStatus, 30000);
  document.addEventListener('keydown', e => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') generateResume();
  });
});
