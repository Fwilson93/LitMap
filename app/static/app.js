document.body.addEventListener('htmx:afterSwap', (event) => {
  if (event.target && event.target.id === 'workspace') {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }
});
