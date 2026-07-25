const themeStorageKey = "monitor-comunitario:theme";
const themeSelector = document.querySelector("#theme-selector");
const systemDarkQuery = window.matchMedia("(prefers-color-scheme: dark)");

function storedThemePreference() {
  const storedValue = window.localStorage.getItem(themeStorageKey);
  return ["light", "dark", "system"].includes(storedValue) ? storedValue : "system";
}

function resolvedTheme(themePreference) {
  if (themePreference === "system") {
    return systemDarkQuery.matches ? "dark" : "light";
  }

  return themePreference;
}

function applyTheme(themePreference) {
  const preference = ["light", "dark", "system"].includes(themePreference)
    ? themePreference
    : "system";

  document.documentElement.dataset.themePreference = preference;
  document.documentElement.dataset.theme = resolvedTheme(preference);

  if (themeSelector) {
    themeSelector.value = preference;
  }
}

function persistThemePreference(themePreference) {
  window.localStorage.setItem(themeStorageKey, themePreference);
  applyTheme(themePreference);
}

applyTheme(storedThemePreference());

themeSelector?.addEventListener("change", (event) => {
  persistThemePreference(event.target.value);
});

systemDarkQuery.addEventListener("change", () => {
  if (storedThemePreference() === "system") {
    applyTheme("system");
  }
});
