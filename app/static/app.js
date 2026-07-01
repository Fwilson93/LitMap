document.body.addEventListener('htmx:beforeSwap', (event) => {
  if (event.target && event.target.id === 'workspace') {
    document.documentElement.classList.add('workspace-updating');
  }
});

document.body.addEventListener('htmx:afterSwap', (event) => {
  if (event.target && event.target.id === 'workspace') {
    document.documentElement.classList.remove('workspace-updating');
  }
});
