// function toggleTheme() {
//     const html = document.documentElement;
//     const currentTheme = html.getAttribute('data-theme');
//     const newTheme = currentTheme === 'dark' ? 'light' : 'dark';

//     html.setAttribute('data-theme', newTheme);
//     localStorage.setItem('theme', newTheme);
//     updateThemeIcon(newTheme);
// }

// function updateThemeIcons(theme) {
//   const iconClass = theme === "dark" ? "bi-sun-fill" : "bi-moon-fill";

//   const iconDesktop = document.getElementById("themeIcon");
//   if (iconDesktop) iconDesktop.className = `bi ${iconClass}`;

//   const iconMobile = document.getElementById("themeIconMobile");
//   if (iconMobile) iconMobile.className = `bi ${iconClass}`;
// }

// function loadTheme() {
//     const savedTheme = localStorage.getItem('theme') || 'light';
//     document.documentElement.setAttribute('data-theme', savedTheme);
//     updateThemeIcon(savedTheme);
// }

// document.addEventListener('DOMContentLoaded', loadTheme);

function setThemeIcon(theme) {
  const icon = document.getElementById("themeIcon");
  if (!icon) return;

  if (theme === "dark") {
    icon.classList.remove("bi-moon-fill");
    icon.classList.add("bi-sun-fill");
  } else {
    icon.classList.remove("bi-sun-fill");
    icon.classList.add("bi-moon-fill");
  }
}

function toggleTheme() {
  const html = document.documentElement;
  const current = html.getAttribute("data-theme") || "light";
  const next = current === "dark" ? "light" : "dark";

  html.setAttribute("data-theme", next);
  localStorage.setItem("theme", next);
  setThemeIcon(next);
}

// Виставляємо правильну іконку одразу при завантаженні сторінки
document.addEventListener("DOMContentLoaded", () => {
  const current = document.documentElement.getAttribute("data-theme") || "light";
  setThemeIcon(current);
});