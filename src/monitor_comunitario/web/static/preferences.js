const themeStorageKey = "monitor-comunitario:theme";
const languageStorageKey = "monitor-comunitario:language";
const themeSelector = document.querySelector("#theme-selector");
const languageSelector = document.querySelector("#language-selector");
const systemDarkQuery = window.matchMedia("(prefers-color-scheme: dark)");
const supportedLanguages = ["pt", "en", "es", "zh", "fr"];

const languageDictionaries = {
  pt: {
    "common.theme": "Tema",
    "common.theme.system": "Sistema",
    "common.theme.light": "Claro",
    "common.theme.dark": "Escuro",
    "common.language": "Idioma",
    "common.language.pt": "Português",
    "common.language.en": "English",
    "common.language.es": "Español",
    "common.language.zh": "简体中文",
    "common.language.fr": "Français",
    "nav.register": "Cadastrar endereço",
    "nav.member": "Área do morador",
    "nav.public": "Cadastro público",
    "nav.public_site": "Site público",
    "button.register_now": "Cadastrar agora",
    "button.member_area": "Acessar área do morador",
    "button.save_session": "Salvar nesta sessão",
    "button.clear_key": "Limpar chave",
    "button.refresh_dashboard": "Atualizar painel",
    "button.run_monitoring": "Rodar coleta manual",
    "button.access_panel": "Acessar painel",
    "button.clear_session": "Limpar sessão",
    "button.copy_code": "Copiar código",
  },
  en: {
    "common.theme": "Theme",
    "common.theme.system": "System",
    "common.theme.light": "Light",
    "common.theme.dark": "Dark",
    "common.language": "Language",
    "common.language.pt": "Português",
    "common.language.en": "English",
    "common.language.es": "Español",
    "common.language.zh": "简体中文",
    "common.language.fr": "Français",
    "nav.register": "Register address",
    "nav.member": "Member area",
    "nav.public": "Public signup",
    "nav.public_site": "Public site",
    "button.register_now": "Register now",
    "button.member_area": "Open member area",
    "button.save_session": "Save for this session",
    "button.clear_key": "Clear key",
    "button.refresh_dashboard": "Refresh dashboard",
    "button.run_monitoring": "Run manual collection",
    "button.access_panel": "Access panel",
    "button.clear_session": "Clear session",
    "button.copy_code": "Copy code",
  },
  es: {
    "common.theme": "Tema",
    "common.theme.system": "Sistema",
    "common.theme.light": "Claro",
    "common.theme.dark": "Oscuro",
    "common.language": "Idioma",
    "common.language.pt": "Português",
    "common.language.en": "English",
    "common.language.es": "Español",
    "common.language.zh": "简体中文",
    "common.language.fr": "Français",
    "nav.register": "Registrar dirección",
    "nav.member": "Área del residente",
    "nav.public": "Registro público",
    "nav.public_site": "Sitio público",
    "button.register_now": "Registrar ahora",
    "button.member_area": "Abrir área del residente",
    "button.save_session": "Guardar en esta sesión",
    "button.clear_key": "Borrar clave",
    "button.refresh_dashboard": "Actualizar panel",
    "button.run_monitoring": "Ejecutar colecta manual",
    "button.access_panel": "Acceder al panel",
    "button.clear_session": "Borrar sesión",
    "button.copy_code": "Copiar código",
  },
  zh: {
    "common.theme": "主题",
    "common.theme.system": "系统",
    "common.theme.light": "浅色",
    "common.theme.dark": "深色",
    "common.language": "语言",
    "common.language.pt": "Português",
    "common.language.en": "English",
    "common.language.es": "Español",
    "common.language.zh": "简体中文",
    "common.language.fr": "Français",
    "nav.register": "登记地址",
    "nav.member": "居民区域",
    "nav.public": "公开登记",
    "nav.public_site": "公开网站",
    "button.register_now": "立即登记",
    "button.member_area": "进入居民区域",
    "button.save_session": "保存到本次会话",
    "button.clear_key": "清除密钥",
    "button.refresh_dashboard": "刷新面板",
    "button.run_monitoring": "运行手动采集",
    "button.access_panel": "进入面板",
    "button.clear_session": "清除会话",
    "button.copy_code": "复制代码",
  },
  fr: {
    "common.theme": "Thème",
    "common.theme.system": "Système",
    "common.theme.light": "Clair",
    "common.theme.dark": "Sombre",
    "common.language": "Langue",
    "common.language.pt": "Português",
    "common.language.en": "English",
    "common.language.es": "Español",
    "common.language.zh": "简体中文",
    "common.language.fr": "Français",
    "nav.register": "Inscrire une adresse",
    "nav.member": "Espace résident",
    "nav.public": "Inscription publique",
    "nav.public_site": "Site public",
    "button.register_now": "Inscrire maintenant",
    "button.member_area": "Ouvrir l'espace résident",
    "button.save_session": "Enregistrer pour cette session",
    "button.clear_key": "Effacer la clé",
    "button.refresh_dashboard": "Actualiser le tableau",
    "button.run_monitoring": "Lancer la collecte manuelle",
    "button.access_panel": "Accéder au panneau",
    "button.clear_session": "Effacer la session",
    "button.copy_code": "Copier le code",
  },
};

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

function storedLanguagePreference() {
  const storedValue = window.localStorage.getItem(languageStorageKey);
  return supportedLanguages.includes(storedValue) ? storedValue : "pt";
}

function applyLanguage(languagePreference) {
  const language = supportedLanguages.includes(languagePreference) ? languagePreference : "pt";
  const dictionary = languageDictionaries[language];

  document.documentElement.lang = language === "zh" ? "zh-CN" : language;
  document.documentElement.dataset.language = language;

  if (languageSelector) {
    languageSelector.value = language;
  }

  document.querySelectorAll("[data-i18n]").forEach((element) => {
    const key = element.dataset.i18n;
    const translatedText = dictionary[key] || languageDictionaries.pt[key];

    if (translatedText) {
      element.textContent = translatedText;
    }
  });
}

function persistLanguagePreference(languagePreference) {
  window.localStorage.setItem(languageStorageKey, languagePreference);
  applyLanguage(languagePreference);
}

applyTheme(storedThemePreference());
applyLanguage(storedLanguagePreference());

themeSelector?.addEventListener("change", (event) => {
  persistThemePreference(event.target.value);
});

languageSelector?.addEventListener("change", (event) => {
  persistLanguagePreference(event.target.value);
});

systemDarkQuery.addEventListener("change", () => {
  if (storedThemePreference() === "system") {
    applyTheme("system");
  }
});
