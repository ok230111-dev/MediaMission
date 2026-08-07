from translations import TRANSLATIONS

all_keys = {
    lang: set(TRANSLATIONS[lang].keys())
    for lang in TRANSLATIONS
}

reference_lang = "uk"  # мова, яку вважаємо повною/еталонною
reference_keys = all_keys[reference_lang]

any_issues = False

for lang, keys in all_keys.items():
    if lang == reference_lang:
        continue
    missing = reference_keys - keys
    extra = keys - reference_keys
    if missing:
        any_issues = True
        print(f"❌ {lang}: відсутні ключі ({len(missing)}):")
        for key in sorted(missing):
            print(f"   - {key}")
    if extra:
        any_issues = True
        print(f"⚠️  {lang}: зайві ключі, яких немає в {reference_lang} ({len(extra)}):")
        for key in sorted(extra):
            print(f"   - {key}")

if not any_issues:
    print("✅ Усі мови мають однаковий набір ключів")