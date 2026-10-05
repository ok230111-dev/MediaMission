(function () {
  const section = document.getElementById("glossary");
  const list = document.getElementById("glossary-list");
  const input = document.getElementById("glossary-search");
  const inDefs = document.getElementById("glossary-in-defs");
  const count = document.getElementById("glossary-count");
  const empty = document.getElementById("glossary-empty");

  if (!section || !list || !input || !inDefs || !count || !empty) return;

  const JSON_URL = section.dataset.sourceUrl;
  const pageLanguage = document.documentElement.lang;
  const language = ["uk", "de", "en"].includes(pageLanguage) ? pageLanguage : "uk";
  const messages = {
    countAll: section.dataset.countAll,
    countFound: section.dataset.countFound,
    loadError: section.dataset.loadError
  };

  let items = [];

  function escapeHtml(s) {
    return s.replace(/[&<>"']/g, c => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
    }[c]));
  }

  function escapeRegExp(s) {
    return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  }

  function format(template, values) {
    return template.replace(/\{(\w+)\}/g, (_, key) => values[key] ?? "");
  }

  function highlight(text, query) {
    const safe = escapeHtml(text);
    if (!query) return safe;
    const re = new RegExp("(" + escapeRegExp(escapeHtml(query)) + ")", "gi");
    return safe.replace(re, "<mark>$1</mark>");
  }

  function render() {
    const q = input.value.trim().toLocaleLowerCase(language);
    const searchDefs = inDefs.checked;

    const found = items.filter(i =>
      !q ||
      i.term.toLocaleLowerCase(language).includes(q) ||
      (searchDefs && i.definition.toLocaleLowerCase(language).includes(q))
    );

    list.innerHTML = found.map(i => `
      <div class="col-12 col-md-6">
        <article class="term-card">
          <h3 class="term-title">${highlight(i.term, q)}</h3>
          <p class="term-text">${highlight(i.definition, searchDefs ? q : "")}</p>
        </article>
      </div>
    `).join("");

    empty.classList.toggle("d-none", found.length > 0);
    count.textContent = q
      ? format(messages.countFound, { found: found.length, total: items.length })
      : format(messages.countAll, { total: items.length });
  }

  async function init() {
    try {
      const res = await fetch(JSON_URL);
      if (!res.ok) throw new Error("HTTP " + res.status);
      const data = await res.json();
      const localizedGlossary = Array.isArray(data)
        ? data
        : Array.isArray(data.glossary)
          ? data.glossary
          : data.glossary?.[language] || data.glossary?.uk;
      if (!Array.isArray(localizedGlossary)) {
        throw new Error(`No glossary entries available for ${language}`);
      }

      items = localizedGlossary.slice().sort((a, b) =>
        a.term.replace(/[«»"]/g, "").localeCompare(b.term.replace(/[«»"]/g, ""), language)
      );
      render();
    } catch (err) {
      console.error("Не вдалося завантажити словник:", err);
      list.innerHTML = `<div class="alert alert-danger">${escapeHtml(messages.loadError)}</div>`;
    }
  }

  input.addEventListener("input", render);
  inDefs.addEventListener("change", render);
  init();
})();