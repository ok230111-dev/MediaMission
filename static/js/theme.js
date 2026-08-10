function toggleTheme() {
    const html = document.documentElement;
    const currentTheme = html.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';

    html.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
    updateThemeIcon(newTheme);
}

function updateThemeIcons(theme) {
  const iconClass = theme === "dark" ? "bi-sun-fill" : "bi-moon-fill";

  const iconDesktop = document.getElementById("themeIcon");
  if (iconDesktop) iconDesktop.className = `bi ${iconClass}`;

  const iconMobile = document.getElementById("themeIconMobile");
  if (iconMobile) iconMobile.className = `bi ${iconClass}`;
}

function loadTheme() {
    const savedTheme = localStorage.getItem('theme') || 'light';
    document.documentElement.setAttribute('data-theme', savedTheme);
    updateThemeIcon(savedTheme);
}

document.addEventListener('DOMContentLoaded', loadTheme);