function showStartupError() {
  if (window.__appReady) return
  const splash = document.getElementById('site-splash')
  if (!splash) return
  splash.classList.add('is-error')
  splash.setAttribute('aria-busy', 'false')
}

window.addEventListener('error', showStartupError)
window.addEventListener('unhandledrejection', showStartupError)
window.setTimeout(showStartupError, 15000)
document.getElementById('site-splash-reload')?.addEventListener('click', () => location.reload())
