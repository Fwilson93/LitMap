function setLiveStatus(message, level = 'info') {
  const note = document.getElementById('activity-status-note');
  if (!note) return;
  note.textContent = message;
  note.className = 'status-note is-live status-' + level;
}

function setWorking(isWorking) {
  const pill = document.getElementById('htmx-status-pill');
  if (!pill) return;
  pill.classList.toggle('is-active', isWorking);
  pill.textContent = isWorking ? 'Working…' : 'Ready';
}

document.body.addEventListener('click', (event) => {
  const link = event.target.closest('.graph-link');
  if (!link) return;
  const workspaceUrl = link.getAttribute('data-workspace-url');
  if (!workspaceUrl || typeof htmx === 'undefined') return;
  event.preventDefault();
  setWorking(true);
  setLiveStatus('Loading linked paper from the map…', 'info');
  htmx.ajax('GET', workspaceUrl, '#workspace');
});

document.body.addEventListener('htmx:beforeRequest', (event) => {
  if (event.target && event.target.closest('#workspace, .sidebar')) {
    setWorking(true);
    setLiveStatus('Working…', 'info');
  }
});

document.body.addEventListener('htmx:afterSwap', (event) => {
  if (event.target && event.target.id === 'workspace') {
    setWorking(false);
  }
});

document.body.addEventListener('htmx:responseError', () => {
  setWorking(false);
  setLiveStatus('Something went wrong while updating the workspace.', 'error');
});

document.body.addEventListener('htmx:sendError', () => {
  setWorking(false);
  setLiveStatus('Network error while contacting the local app.', 'error');
});
