function toggleSection(header) {
  header.classList.toggle('collapsed');
  const body = header.nextElementSibling;
  body.classList.toggle('hidden');
}

function toggleDraft(btn) {
  const body = btn.nextElementSibling;
  const open = body.classList.toggle('open');
  btn.textContent = open ? 'Hide cancellation draft' : 'View cancellation draft';
}

function copyDraft(btn) {
  const text = btn.parentElement.textContent.replace('Copy', '').trim();
  navigator.clipboard.writeText(text).then(() => {
    btn.textContent = 'Copied!';
    setTimeout(() => { btn.textContent = 'Copy'; }, 1500);
  });
}

let pollTimer = null;

async function rerunAudit() {
  const btn = document.getElementById('rerun-btn');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span> Running audit...';

  const res = await fetch('/api/audit/run', { method: 'POST' });
  if (!res.ok) {
    btn.disabled = false;
    btn.textContent = 'Re-run audit';
    alert('Could not start audit');
    return;
  }

  pollTimer = setInterval(async () => {
    const status = await fetch('/api/audit/status').then(r => r.json());
    if (status.running) return;
    clearInterval(pollTimer);
    btn.disabled = false;
    btn.textContent = 'Re-run audit';
    if (status.error) {
      alert('Audit failed: ' + status.error);
    } else {
      location.reload();
    }
  }, 2000);
}

document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.section-header.collapsible').forEach(h => {
    if (h.dataset.collapsed === 'true') {
      h.classList.add('collapsed');
      h.nextElementSibling.classList.add('hidden');
    }
  });
});
