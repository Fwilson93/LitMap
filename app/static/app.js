function setLiveStatus(message, level = 'info') {
  const note = document.getElementById('activity-status-note');
  if (!note) return;

  note.textContent = message;
  note.className = 'status-note is-live status-' + level;
}

function setWorking(isWorking) {
  const pill = document.getElementById('htmx-status-pill');
  if (!pill) return;

  pill.textContent = isWorking ? 'Working…' : 'Ready';
}

document.body.addEventListener('htmx:beforeRequest', () => {
  setWorking(true);
});

document.body.addEventListener('htmx:afterSwap', () => {
  setWorking(false);
});

document.body.addEventListener('htmx:responseError', () => {
  setWorking(false);
  setLiveStatus('Error updating workspace', 'error');
});
