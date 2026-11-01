const root = document.documentElement;
const button = document.querySelector('[data-theme-toggle]');
const label = document.querySelector('[data-theme-label]');
const savedTheme = localStorage.getItem('typing-auto-theme');
if (savedTheme === 'light' || savedTheme === 'dark') root.dataset.theme = savedTheme;
function updateThemeControl() {
  if (label) label.textContent = root.dataset.theme === 'dark' ? 'Light' : 'Dark';
}
updateThemeControl();
if (button) {
  button.addEventListener('click', () => {
    root.dataset.theme = root.dataset.theme === 'dark' ? 'light' : 'dark';
    localStorage.setItem('typing-auto-theme', root.dataset.theme);
    updateThemeControl();
  });
}
