(() => {
  "use strict";

  const root = document.getElementById("app");
  const dialogRoot = document.getElementById("dialog-root");
  const toastRegion = document.getElementById("toast-region");
  const liveRegion = document.getElementById("live-region");
  const nativeBridge = window.MedSalesApp;
  const isNative = Boolean(nativeBridge);
  const SUPPORTED_LOCALES = [
    ["zh-CN", "中文"],
    ["en", "English"],
    ["vi", "Tiếng Việt"],
    ["ms", "Bahasa Melayu"],
    ["id", "Bahasa Indonesia"],
    ["de", "Deutsch"],
    ["fr", "Français"],
  ];
  const LOCALE_INDEX = { en: 0, vi: 1, ms: 2, id: 3, de: 4, fr: 5 };
  let phrases = null;
  let translationObserver = null;
  const translatedText = new WeakMap();
  const translatedAttributes = new WeakMap();

  const STORAGE = {
    token: "medapp_access_token",
    username: "medapp_username",
    server: "medapp_server_url",
    locale: "medapp_locale",
    theme: "medapp_theme",
  };

  const state = {
    token: localStorage.getItem(STORAGE.token) || "",
    me: null,
    serverUrl: initialServerUrl(),
    route: currentRoute(),
    loginError: "",
    passwordVisible: false,
    home: null,
    sales: null,
    salesDetail: new Map(),
    inventory: null,
    compliance: null,
    options: new Map(),
    orderDraft: null,
    dialogClose: null,
    picker: null,
    locale: initialLocale(),
    theme: initialTheme(),
  };

  const pendingNativeRequests = new Map();
  let nativeRequestSequence = 0;

  window.appBridge = {
    onApiResponse(id, status, body) {
      const request = pendingNativeRequests.get(String(id));
      if (!request) return;
      pendingNativeRequests.delete(String(id));
      request.resolve({
        ok: status >= 200 && status < 300,
        status,
        text: body || "",
      });
    },
  };

  window.medappBack = () => {
    if (dialogRoot.firstElementChild) {
      closeDialog();
      return "handled";
    }
    if (!state.token || !state.me) return "exit";

    const rootName = routeRoot();
    if (state.route === "/home" || rootName === "/restricted") return "exit";
    if (rootName === "/sales" && state.route !== "/sales") {
      go("/sales", true);
      return "handled";
    }
    if (rootName === "/profile" && !navItems().some((item) => item.id !== "profile")) {
      return "exit";
    }
    go("/home", true);
    return "handled";
  };

  function initialServerUrl() {
    if (window.MedSalesApp) return window.MedSalesApp.getServerUrl();
    return localStorage.getItem(STORAGE.server) || "http://127.0.0.1:8001";
  }

  function initialLocale() {
    const stored = localStorage.getItem(STORAGE.locale);
    if (SUPPORTED_LOCALES.some(([code]) => code === stored)) return stored;
    // 中文继续作为既有用户的默认界面语言，可在登录页或“我的”中切换。
    return "zh-CN";
  }

  function initialTheme() {
    const stored = localStorage.getItem(STORAGE.theme);
    if (stored === "light" || stored === "dark") return stored;
    return window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }

  function intlLocale() {
    return state.locale;
  }

  function localeLabel(code = state.locale) {
    return SUPPORTED_LOCALES.find(([candidate]) => candidate === code)?.[1] || code;
  }

  function localeShortLabel() {
    return state.locale === "zh-CN" ? "中" : state.locale.toUpperCase();
  }

  function lookupPhrase(source) {
    if (state.locale === "zh-CN" || !phrases) return null;
    const entry = phrases[source];
    return Array.isArray(entry) ? entry[LOCALE_INDEX[state.locale]] || null : null;
  }

  function translateDynamic(core) {
    if (state.locale === "zh-CN") return null;
    const index = LOCALE_INDEX[state.locale];
    const patterns = [
      [/^请选择(.+)$/, ["Select {value}", "Chọn {value}", "Pilih {value}", "Pilih {value}", "{value} auswählen", "Sélectionner {value}"]],
      [/^请输入(.+)$/, ["Enter {value}", "Nhập {value}", "Masukkan {value}", "Masukkan {value}", "{value} eingeben", "Saisir {value}"]],
      [/^请填写(.+)$/, ["Enter {value}", "Nhập {value}", "Isi {value}", "Isi {value}", "{value} ausfüllen", "Renseigner {value}"]],
      [/^新增(.+)$/, ["Add {value}", "Thêm {value}", "Tambah {value}", "Tambah {value}", "{value} hinzufügen", "Ajouter {value}"]],
      [/^编辑(.+)$/, ["Edit {value}", "Sửa {value}", "Edit {value}", "Ubah {value}", "{value} bearbeiten", "Modifier {value}"]],
    ];
    for (const [pattern, templates] of patterns) {
      const match = core.match(pattern);
      if (!match) continue;
      const leaf = lookupPhrase(match[1].trim());
      if (!leaf) continue;
      return templates[index].replace("{value}", leaf);
    }
    const networkPatterns = [
      [/^无法连接服务器 (.+)。请检查后端是否运行、地址是否可从设备访问。$/, ["Cannot connect to {server}. Check that the backend is running and reachable.", "Không thể kết nối với {server}. Kiểm tra máy chủ đã chạy và có thể truy cập.", "Tidak dapat menyambung ke {server}. Pastikan backend berjalan dan boleh diakses.", "Tidak dapat terhubung ke {server}. Pastikan backend berjalan dan dapat diakses.", "{server} ist nicht erreichbar. Prüfen Sie, ob das Backend läuft und erreichbar ist.", "Connexion impossible à {server}. Vérifiez que le serveur fonctionne et est accessible."]],
      [/^请求失败（HTTP (.+)）$/, ["Request failed (HTTP {value})", "Yêu cầu thất bại (HTTP {value})", "Permintaan gagal (HTTP {value})", "Permintaan gagal (HTTP {value})", "Anfrage fehlgeschlagen (HTTP {value})", "Échec de la requête (HTTP {value})"]],
      [/^请求地址有误：(.+)$/, ["Invalid request address: {value}", "Địa chỉ yêu cầu không hợp lệ: {value}", "Alamat permintaan tidak sah: {value}", "Alamat permintaan tidak valid: {value}", "Ungültige Anfrageadresse: {value}", "Adresse de requête non valide : {value}"]],
      [/^请求失败：(.+)$/, ["Request failed: {value}", "Yêu cầu thất bại: {value}", "Permintaan gagal: {value}", "Permintaan gagal: {value}", "Anfrage fehlgeschlagen: {value}", "Échec de la requête : {value}"]],
    ];
    for (const [pattern, templates] of networkPatterns) {
      const match = core.match(pattern);
      if (match) return templates[index].replaceAll("{value}", match[1]).replace("{server}", match[1]);
    }
    return null;
  }

  function translateText(source) {
    if (state.locale === "zh-CN" || !/[\u3400-\u9fff]/.test(source)) return source;
    const leading = source.match(/^\s*/)?.[0] || "";
    const trailing = source.match(/\s*$/)?.[0] || "";
    const core = source.slice(leading.length, source.length - trailing.length);
    if (!core) return source;
    const exact = lookupPhrase(core) || translateDynamic(core);
    if (exact) return `${leading}${exact}${trailing}`;
    for (const prefix of ["角色：", "邮箱：", "电话："]) {
      if (!core.startsWith(prefix)) continue;
      const translatedPrefix = lookupPhrase(prefix);
      if (translatedPrefix) return `${leading}${translatedPrefix}${core.slice(prefix.length)}${trailing}`;
    }
    return source;
  }

  function applyTextNode(node) {
    const previous = translatedText.get(node);
    const source = previous && node.data === previous.target ? previous.source : node.data;
    const target = translateText(source);
    if (target !== source) translatedText.set(node, { source, target });
    if (node.data !== target) node.data = target;
  }

  function applyElement(node) {
    for (const attribute of ["placeholder", "title", "aria-label", "alt"]) {
      if (!node.hasAttribute(attribute)) continue;
      let sourceMap = translatedAttributes.get(node);
      if (!sourceMap) {
        sourceMap = new Map();
        translatedAttributes.set(node, sourceMap);
      }
      const current = node.getAttribute(attribute) || "";
      const previous = sourceMap.get(attribute);
      const source = previous && current === previous.target ? previous.source : current;
      const target = translateText(source);
      if (target !== source) sourceMap.set(attribute, { source, target });
      if (current !== target) node.setAttribute(attribute, target);
    }
  }

  function translateDom(rootNode = document.body) {
    if (!rootNode) return;
    if (rootNode.nodeType === Node.TEXT_NODE) {
      applyTextNode(rootNode);
      return;
    }
    if (rootNode.nodeType === Node.ELEMENT_NODE) applyElement(rootNode);
    const walker = document.createTreeWalker(rootNode, NodeFilter.SHOW_ELEMENT | NodeFilter.SHOW_TEXT);
    let node = walker.nextNode();
    while (node) {
      if (node.nodeType === Node.TEXT_NODE) applyTextNode(node);
      else applyElement(node);
      node = walker.nextNode();
    }
  }

  function installTranslations() {
    translateDom();
    translationObserver?.disconnect();
    translationObserver = new MutationObserver((mutations) => {
      for (const mutation of mutations) {
        if (mutation.type === "characterData") {
          applyTextNode(mutation.target);
        } else if (mutation.type === "attributes" && mutation.target.nodeType === Node.ELEMENT_NODE) {
          applyElement(mutation.target);
        } else {
          for (const node of mutation.addedNodes) translateDom(node);
        }
      }
    });
    translationObserver.observe(document.body, {
      subtree: true,
      childList: true,
      characterData: true,
      attributes: true,
      attributeFilter: ["placeholder", "title", "aria-label", "alt"],
    });
  }

  function applyTheme() {
    document.documentElement.dataset.theme = state.theme;
    document.documentElement.style.colorScheme = state.theme;
    try {
      nativeBridge?.setSystemBarsDark(state.theme === "dark");
    } catch {
      // System bar styling is an enhancement.
    }
  }

  function applyLocale() {
    document.documentElement.lang = state.locale;
    document.documentElement.dataset.locale = state.locale;
    translateDom();
  }

  function setLocale(locale) {
    if (!SUPPORTED_LOCALES.some(([code]) => code === locale)) return;
    state.locale = locale;
    localStorage.setItem(STORAGE.locale, locale);
    applyLocale();
  }

  function toggleTheme() {
    state.theme = state.theme === "dark" ? "light" : "dark";
    localStorage.setItem(STORAGE.theme, state.theme);
    applyTheme();
  }

  async function loadPhrases() {
    try {
      const response = await fetch("i18n-phrases.json", { cache: "no-store" });
      if (response.ok) phrases = await response.json();
    } catch {
      phrases = null;
    }
  }

  function currentRoute() {
    const route = window.location.hash.slice(1).trim();
    return route.startsWith("/") ? route : "/home";
  }

  function routeRoot(route = state.route) {
    return `/${route.split("/").filter(Boolean)[0] || "home"}`;
  }

  function go(route, replace = false) {
    const next = route.startsWith("/") ? route : `/${route}`;
    if (window.location.hash === `#${next}`) {
      handleRoute();
      return;
    }
    if (replace) {
      window.history.replaceState(
        null,
        "",
        `${window.location.pathname}${window.location.search}#${next}`,
      );
      handleRoute();
    } else {
      window.location.hash = next;
    }
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function icon(name, className = "") {
    return `<svg class="icon ${className}" aria-hidden="true"><use href="#i-${name}"></use></svg>`;
  }

  function number(value) {
    return Number(value || 0).toLocaleString(intlLocale(), { maximumFractionDigits: 2 });
  }

  function money(value, digits = 2) {
    return Number(value || 0).toLocaleString(intlLocale(), {
      minimumFractionDigits: digits,
      maximumFractionDigits: digits,
    });
  }

  function compactMoney(value) {
    const amount = Number(value || 0);
    return new Intl.NumberFormat(intlLocale(), {
      notation: "compact",
      maximumFractionDigits: 1,
    }).format(amount);
  }

  function fullDate(value) {
    if (!value) return "—";
    const date = new Date(`${String(value).slice(0, 10)}T00:00:00`);
    if (Number.isNaN(date.getTime())) return String(value);
    return new Intl.DateTimeFormat(intlLocale(), {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
    }).format(date);
  }

  function shortDate(value) {
    if (!value) return "—";
    const date = new Date(`${String(value).slice(0, 10)}T00:00:00`);
    if (Number.isNaN(date.getTime())) return String(value);
    return new Intl.DateTimeFormat(intlLocale(), {
      month: "numeric",
      day: "numeric",
    }).format(date);
  }

  function monthLabel(value) {
    if (!value) return "暂无数据";
    const date = new Date(`${String(value).slice(0, 7)}-01T00:00:00`);
    if (Number.isNaN(date.getTime())) return String(value);
    return new Intl.DateTimeFormat(intlLocale(), { year: "numeric", month: "long" }).format(date);
  }

  function monthShortLabel(value) {
    if (!value) return "";
    const date = new Date(`${String(value).slice(0, 7)}-01T00:00:00`);
    if (Number.isNaN(date.getTime())) return String(value);
    return new Intl.DateTimeFormat(intlLocale(), { month: "short" }).format(date);
  }

  function todayLabel() {
    return new Intl.DateTimeFormat(intlLocale(), {
      month: "long",
      day: "numeric",
      weekday: "long",
    }).format(new Date());
  }

  function todayISO() {
    const now = new Date();
    const offset = now.getTimezoneOffset() * 60000;
    return new Date(now.getTime() - offset).toISOString().slice(0, 10);
  }

  function initials(name) {
    const value = String(name || "M").trim();
    return escapeHtml(value.slice(-2).toUpperCase());
  }

  function hasPermission(code) {
    if (!code) return true;
    if (!state.me) return false;
    if (state.me.is_superuser || (state.me.permissions || []).includes("all")) return true;
    const codes = Array.isArray(code) ? code : [code];
    return codes.some((item) => (state.me.permissions || []).includes(item));
  }

  function statusClass(status) {
    if (["已完成", "库存充足", "有效", "已审核"].includes(status)) return "is-success";
    if (["已发货", "库存预警", "待审核", "待处理", "60天内", "90天内"].includes(status)) {
      return "is-warning";
    }
    if (["已取消", "库存不足", "已过期", "已驳回", "30天内"].includes(status)) return "is-danger";
    if (["待付款", "正常"].includes(status)) return "is-primary";
    return "";
  }

  function statusBadge(status) {
    return `<span class="status ${statusClass(status)}">${escapeHtml(status)}</span>`;
  }

  function setLive(message) {
    liveRegion.textContent = "";
    window.setTimeout(() => {
      liveRegion.textContent = message;
    }, 10);
  }

  function toast(message, type = "success") {
    const item = document.createElement("div");
    item.className = `toast${type === "error" ? " is-error" : ""}`;
    item.textContent = message;
    toastRegion.appendChild(item);
    window.setTimeout(() => item.remove(), type === "error" ? 4200 : 3000);
  }

  function nativeHaptic() {
    try {
      nativeBridge?.haptic();
    } catch {
      // Haptics are an enhancement.
    }
  }

  function setServerAddress(value) {
    const normalized = String(value || "").trim().replace(/\/+$/, "");
    if (!/^https?:\/\/[^/\s]+(?::\d+)?$/i.test(normalized)) {
      return false;
    }
    if (isNative && !nativeBridge.setServerUrl(normalized)) {
      return false;
    }
    state.serverUrl = normalized;
    localStorage.setItem(STORAGE.server, normalized);
    return true;
  }

  async function nativeRequest(method, path, body, token) {
    return new Promise((resolve) => {
      const id = `medapp-${++nativeRequestSequence}`;
      pendingNativeRequests.set(id, { resolve });
      try {
        nativeBridge.request(
          id,
          method,
          path,
          body == null ? null : JSON.stringify(body),
          token ? `Bearer ${token}` : null,
        );
      } catch (error) {
        pendingNativeRequests.delete(id);
        resolve({ ok: false, status: 0, text: JSON.stringify({ detail: String(error) }) });
      }
    });
  }

  function buildQuery(params = {}) {
    const query = new URLSearchParams();
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== null && value !== "") query.set(key, String(value));
    }
    const text = query.toString();
    return text ? `?${text}` : "";
  }

  async function api(path, options = {}) {
    const method = (options.method || "GET").toUpperCase();
    const token = options.token ?? state.token;
    const query = buildQuery(options.query || {});
    const apiPath = `/api${path}${query}`;
    let response;

    if (isNative && method !== "GET") {
      response = await nativeRequest(method, apiPath, options.body, token);
    } else {
      const url = isNative ? apiPath : `${state.serverUrl}${apiPath}`;
      try {
        const fetchResponse = await fetch(url, {
          method,
          headers: {
            Accept: "application/json",
            ...(options.body ? { "Content-Type": "application/json" } : {}),
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: options.body ? JSON.stringify(options.body) : undefined,
        });
        response = {
          ok: fetchResponse.ok,
          status: fetchResponse.status,
          text: await fetchResponse.text(),
        };
      } catch (error) {
        throw new Error(
          `无法连接服务器 ${state.serverUrl}。请检查后端是否运行、地址是否可从设备访问。`,
          { cause: error },
        );
      }
    }

    let data = null;
    if (response.text) {
      try {
        data = JSON.parse(response.text);
      } catch {
        data = response.text;
      }
    }

    if (!response.ok) {
      if (response.status === 401 && !options.keepSession) {
        clearSession();
        go("/login", true);
      }
      const detail = typeof data === "object" && data?.detail
        ? data.detail
        : `请求失败（HTTP ${response.status || "网络错误"}）`;
      throw new Error(detail);
    }
    return data;
  }

  function clearSession() {
    state.token = "";
    state.me = null;
    state.home = null;
    state.sales = null;
    state.salesDetail.clear();
    state.inventory = null;
    state.compliance = null;
    state.options.clear();
    state.orderDraft = null;
    localStorage.removeItem(STORAGE.token);
  }

  function navItems() {
    const candidates = [
      { id: "home", label: "首页", icon: "home", permission: ["dashboard:view", "report:view", "sales:view", "inventory:view", "gsp:view"] },
      { id: "sales", label: "销售", icon: "receipt", permission: "sales:view" },
      { id: "inventory", label: "库存", icon: "box", permission: "inventory:view" },
      { id: "compliance", label: "合规", icon: "shield", permission: "gsp:view" },
      { id: "profile", label: "我的", icon: "user", permission: null },
    ];
    const allowed = candidates.filter(
      (item) => item.id === "profile" || hasPermission(item.permission),
    );
    if (!allowed.some((item) => item.id === "profile")) {
      allowed.push(candidates[candidates.length - 1]);
    }
    return allowed;
  }

  function landingRoute() {
    const allowed = navItems().find((item) => item.id !== "profile");
    return allowed ? `/${allowed.id}` : "/restricted";
  }

  function pageMeta(route) {
    const rootName = routeRoot(route);
    if (route.startsWith("/sales/new")) return ["新建销售单", "客户、仓库与商品明细"];
    if (/^\/sales\/\d+/.test(route)) return ["订单详情", "查看明细与执行发货"];
    const mapping = {
      "/home": ["工作台", "经营概况与快捷入口"],
      "/sales": ["销售订单", "按状态与客户追踪订单"],
      "/inventory": ["库存查询", "仓库库存与安全库存预警"],
      "/compliance": ["GSP 合规", "证照与批次效期预警"],
      "/profile": ["我的", "账号、服务与安全设置"],
      "/restricted": ["访问受限", "当前账号没有业务权限"],
    };
    return mapping[rootName] || ["medapp", "移动销售工作台"];
  }

  function preferenceControlsHtml() {
    return `
      <button
        class="icon-button preference-locale"
        type="button"
        data-action="open-language"
        aria-label="切换语言"
        title="${escapeHtml(localeLabel())}"
        data-test="language-switcher"
      >
        ${icon("globe")}
        <span class="preference-locale-code" aria-hidden="true">${localeShortLabel()}</span>
      </button>
      <button
        class="icon-button"
        type="button"
        data-action="toggle-theme"
        aria-label="切换主题"
        title="${state.theme === "dark" ? "深色" : "浅色"}"
        data-test="theme-toggle"
      >
        ${icon(state.theme === "dark" ? "moon" : "sun")}
      </button>
    `;
  }

  function renderShell(pageHtml, route = state.route) {
    const [title, subtitle] = pageMeta(route);
    const active = routeRoot(route);
    const nav = navItems();
    const showRefresh = !route.startsWith("/profile") && route !== "/restricted";
    root.innerHTML = `
      <div class="app-frame">
        <header class="app-header">
          <div class="brand-lockup">
            <div class="brand-mark" aria-hidden="true"><span class="brand-cross"></span></div>
            <div class="header-copy">
              <h1 class="header-title">${escapeHtml(title)}</h1>
              <p class="header-subtitle">${escapeHtml(subtitle)}</p>
            </div>
          </div>
          <div class="header-actions">
            ${preferenceControlsHtml()}
            ${showRefresh ? `
              <button class="icon-button" type="button" data-action="refresh-page" aria-label="刷新当前页面">
                ${icon("refresh")}
              </button>
            ` : ""}
          </div>
        </header>
        <main class="page" id="main-content" tabindex="-1">${pageHtml}</main>
        <nav class="bottom-nav" aria-label="主导航">
          ${nav.map((item) => `
            <a
              class="nav-item${active === `/${item.id}` ? " is-active" : ""}"
              href="#/${item.id}"
              ${active === `/${item.id}` ? 'aria-current="page"' : ""}
            >
              <span class="nav-icon-wrap">${icon(item.icon)}</span>
              <span>${item.label}</span>
            </a>
          `).join("")}
        </nav>
      </div>
    `;
  }

  function pageHeading(title, description, back = false) {
    return `
      <div class="page-heading">
        ${back ? `
          <button class="icon-button back-button" type="button" data-action="go-back" aria-label="返回">
            ${icon("arrow-left")}
          </button>
        ` : ""}
        <div class="page-heading-copy">
          <h1>${escapeHtml(title)}</h1>
          <p>${escapeHtml(description)}</p>
        </div>
      </div>
    `;
  }

  function skeletonPage() {
    return `
      <div aria-busy="true" aria-label="正在加载">
        <div class="skeleton skeleton-hero"></div>
        <div class="skeleton-grid">
          <div class="skeleton skeleton-card"></div>
          <div class="skeleton skeleton-card"></div>
          <div class="skeleton skeleton-card"></div>
          <div class="skeleton skeleton-card"></div>
        </div>
        <div class="skeleton skeleton-row"></div>
        <div class="skeleton skeleton-row"></div>
      </div>
    `;
  }

  function errorState(message, retryAction = "refresh-page") {
    return `
      <div class="error-state">
        <div class="state-icon">${icon("alert", "icon-lg")}</div>
        <h2>暂时无法加载</h2>
        <p>${escapeHtml(message)}</p>
        <button class="button compact" type="button" data-action="${retryAction}">重新加载</button>
      </div>
    `;
  }

  function emptyState(title, message, actionHtml = "") {
    return `
      <div class="empty-state">
        <div class="state-icon">${icon("list", "icon-lg")}</div>
        <h2>${escapeHtml(title)}</h2>
        <p>${escapeHtml(message)}</p>
        ${actionHtml}
      </div>
    `;
  }

  function permissionState(message = "当前账号没有访问此模块的权限，如有业务需要请联系管理员。") {
    return `
      <div class="permission-state">
        <div class="state-icon">${icon("lock", "icon-lg")}</div>
        <h2>暂无访问权限</h2>
        <p>${escapeHtml(message)}</p>
        <a class="button secondary compact" href="#/profile">查看账号</a>
      </div>
    `;
  }

  function renderLogin() {
    const username = localStorage.getItem(STORAGE.username) || "";
    const error = state.loginError
      ? `<p class="inline-error" role="alert">${escapeHtml(state.loginError)}</p>`
      : "";
    root.innerHTML = `
      <div class="login-shell">
        <div class="login-content">
          <div class="login-preferences">${preferenceControlsHtml()}</div>
          <div class="login-brand">
            <div class="login-brand-row">
              <div class="login-mark" aria-hidden="true"><span class="brand-cross"></span></div>
              <div>
                <h1>medapp</h1>
                <p>医药销售移动工作台</p>
              </div>
            </div>
          </div>
          <h2 class="login-headline">登录工作台</h2>
          <p class="login-description">查看经营数据、销售订单、库存与 GSP 合规预警。</p>
          <form class="login-form" id="login-form" novalidate>
            <div class="field-group">
              <label for="login-username">用户名</label>
              <input
                class="field"
                id="login-username"
                name="username"
                value="${escapeHtml(username)}"
                autocomplete="username"
                autocapitalize="none"
                spellcheck="false"
                placeholder="请输入用户名"
                data-test="username"
              />
            </div>
            <div class="field-group">
              <label for="login-password">密码</label>
              <div class="password-field">
                <input
                  class="field"
                  id="login-password"
                  name="password"
                  type="${state.passwordVisible ? "text" : "password"}"
                  autocomplete="current-password"
                  placeholder="请输入密码"
                  data-test="password"
                />
                <button
                  class="password-toggle"
                  type="button"
                  data-action="toggle-password"
                  aria-label="${state.passwordVisible ? "隐藏密码" : "显示密码"}"
                >
                  ${icon(state.passwordVisible ? "eye-off" : "eye")}
                </button>
              </div>
            </div>
            ${error}
            <details class="server-details">
              <summary>服务器设置 · ${escapeHtml(state.serverUrl)}</summary>
              <div class="field-group">
                <label for="login-server">后端地址</label>
                <input
                  class="field"
                  id="login-server"
                  name="server"
                  type="url"
                  inputmode="url"
                  autocapitalize="none"
                  spellcheck="false"
                  value="${escapeHtml(state.serverUrl)}"
                  placeholder="http://192.168.1.10:8001"
                  data-test="server-url"
                />
                <p class="field-help">模拟器使用 http://10.0.2.2:8001；真机填写电脑局域网 IP。</p>
              </div>
            </details>
            <div class="form-actions">
              <button class="button block" type="submit" data-test="login-submit">
                登录
              </button>
            </div>
          </form>
          <p class="login-footer">medapp 1.0 · 数据来自 med-sales 服务端</p>
        </div>
      </div>
    `;
  }

  function render() {
    if (!state.token || !state.me) {
      renderLogin();
      return;
    }

    const route = state.route;
    if (route === "/login") {
      go(landingRoute(), true);
      return;
    }
    if (routeRoot(route) === "/home") renderHome();
    else if (routeRoot(route) === "/sales") renderSalesRoute();
    else if (routeRoot(route) === "/inventory") renderInventory();
    else if (routeRoot(route) === "/compliance") renderCompliance();
    else if (routeRoot(route) === "/profile") renderProfile();
    else if (routeRoot(route) === "/restricted") {
      renderShell(
        pageHeading("访问受限", "当前账号没有可用的业务模块") +
          permissionState("请联系管理员分配角色与业务权限。你仍可以在「我的」中查看账号信息或退出登录。"),
        route,
      );
    } else {
      go(landingRoute(), true);
    }
  }

  function actionLink(route, iconName, label) {
    return `
      <a class="quick-action" href="#${route}">
        <span class="action-icon">${icon(iconName)}</span>
        <span>${escapeHtml(label)}</span>
      </a>
    `;
  }

  function recentOrderRow(order) {
    return `
      <a class="list-row" href="#/sales/${order.id}">
        <div class="list-row-main">
          <p class="list-row-title">${escapeHtml(order.customer_name || `客户 ${order.customer_id}`)}</p>
          <p class="list-row-subtitle">${escapeHtml(order.order_no)} · ${shortDate(order.order_date)}</p>
        </div>
        <div class="list-row-end">
          <span class="money">¥${compactMoney(order.total_amount)}</span>
          ${statusBadge(order.status)}
        </div>
      </a>
    `;
  }

  function chartHtml(monthly) {
    const rows = [...monthly].reverse();
    const max = Math.max(...rows.map((row) => Number(row.total_amount || 0)), 1);
    const summary = rows
      .map((row) => `${monthLabel(row.month)}销售额${compactMoney(row.total_amount)}元`)
      .join("，");
    return `
      <div class="chart-card">
        <div class="section-heading">
          <div>
            <h2>近六个月销售趋势</h2>
            <p>单位：元，按销售汇总数据展示</p>
          </div>
          <span class="permission-badge">月度</span>
        </div>
        <div class="bar-chart" role="img" aria-label="近六个月销售趋势：${escapeHtml(summary)}">
          ${rows.map((row) => {
            const height = Math.max(4, Math.round((Number(row.total_amount || 0) / max) * 100));
            return `
              <div class="bar-column" title="${escapeHtml(monthLabel(row.month))}：¥${money(row.total_amount)}">
                <div class="bar-track">
                  <div class="bar-fill" style="height:${height}%"></div>
                </div>
                <span class="bar-label">${escapeHtml(monthShortLabel(row.month))}</span>
              </div>
            `;
          }).join("")}
        </div>
      </div>
    `;
  }

  function renderHome() {
    if (!hasPermission(["dashboard:view", "report:view", "sales:view", "inventory:view", "gsp:view"])) {
      renderShell(pageHeading("工作台", "当前账号暂无业务数据"), permissionState(), "/home");
      return;
    }

    const data = state.home;
    if (!data || (!data.loaded && !data.loading && !data.error)) {
      renderShell(pageHeading("工作台", `${todayLabel()} · ${state.me.display_name || state.me.username}`) + skeletonPage(), "/home");
      loadHome();
      return;
    }
    if (data.loading && !data.dashboard && !data.monthly) {
      renderShell(pageHeading("工作台", `${todayLabel()} · 经营概况`) + skeletonPage(), "/home");
      return;
    }
    if (data.error && !data.dashboard && !data.monthly) {
      renderShell(
        pageHeading("工作台", "经营概况与快捷入口") + errorState(data.error, "refresh-page"),
        "/home",
      );
      return;
    }

    const monthly = data.monthly || [];
    const latest = monthly[0];
    const dashboard = data.dashboard;
    const summary = data.gspSummary;
    const fallbackAmount = latest?.total_amount ?? dashboard?.month_sales_amount ?? 0;
    const fallbackOrders = latest?.order_count ?? dashboard?.month_order_count ?? 0;
    const growth = Number(latest?.amount_growth_rate);
    const growthValid = Number.isFinite(growth);
    const recentOrders = data.recentOrders || [];

    const content = `
      ${pageHeading("你好，" + (state.me.display_name || state.me.username), `${todayLabel()} · 经营概况`)}
      <section class="hero-card" aria-labelledby="business-hero-title">
        <div class="hero-topline">
          <p class="hero-kicker" id="business-hero-title">
            ${latest ? `最近月销售 · ${monthLabel(latest.month)}` : "本月销售额"}
          </p>
          ${growthValid ? `
            <span class="hero-badge${growth < 0 ? " is-negative" : ""}">
              ${growth >= 0 ? "↑" : "↓"} ${Math.abs(growth).toFixed(2)}%
            </span>
          ` : `<span class="hero-badge">经营概览</span>`}
        </div>
        <div class="hero-value">¥${compactMoney(fallbackAmount)}</div>
        <div class="hero-meta">
          <span>${icon("receipt", "icon-sm")} ${number(fallbackOrders)} 单</span>
          <span>${icon("trend", "icon-sm")} ${latest ? "销售额" : "当前月份"}</span>
        </div>
        <p class="hero-note">${latest ? `最近汇总月份：${monthLabel(latest.month)}，环比上月` : "实时数据来自销售汇总接口"}</p>
      </section>

      <section class="section" aria-labelledby="quick-actions-title">
        <div class="section-heading">
          <h2 id="quick-actions-title">快捷入口</h2>
        </div>
        <div class="action-grid">
          ${hasPermission("sales:view") ? actionLink("/sales", "receipt", "销售订单") : ""}
          ${hasPermission("inventory:view") ? actionLink("/inventory", "box", "库存查询") : ""}
          ${hasPermission("gsp:view") ? actionLink("/compliance", "shield", "GSP 预警") : ""}
          ${hasPermission("sales:manage") ? actionLink("/sales/new", "plus", "新建订单") : ""}
        </div>
      </section>

      <section class="section" aria-labelledby="watch-title">
        <div class="section-heading">
          <div>
            <h2 id="watch-title">经营关注</h2>
            <p>库存、退货、应收与合规风险</p>
          </div>
        </div>
        <div class="metric-grid">
          <article class="metric-card">
            <div class="metric-card-top">
              <span class="metric-icon is-warning">${icon("box", "icon-sm")}</span>
              库存不足
            </div>
            <div class="metric-value">${number(dashboard?.low_stock_count)} <span class="metric-unit">项</span></div>
          </article>
          <article class="metric-card">
            <div class="metric-card-top">
              <span class="metric-icon is-warning">${icon("rotate", "icon-sm")}</span>
              待处理退货
            </div>
            <div class="metric-value">${number(dashboard?.pending_return_count)} <span class="metric-unit">单</span></div>
          </article>
          <article class="metric-card">
            <div class="metric-card-top">
              <span class="metric-icon">${icon("wallet", "icon-sm")}</span>
              应收总额
            </div>
            <div class="metric-value">¥${compactMoney(dashboard?.total_receivable)}</div>
          </article>
          <article class="metric-card">
            <div class="metric-card-top">
              <span class="metric-icon ${summary?.expired || summary?.within_30 ? "is-warning" : "is-success"}">
                ${icon("shield", "icon-sm")}
              </span>
              GSP 风险
            </div>
            <div class="metric-value">${number((summary?.expired || 0) + (summary?.within_30 || 0))} <span class="metric-unit">项</span></div>
          </article>
        </div>
      </section>

      ${monthly.length ? `<section class="section" id="sales-trend">${chartHtml(monthly)}</section>` : ""}

      <section class="section" aria-labelledby="recent-orders-title">
        <div class="section-heading">
          <div>
            <h2 id="recent-orders-title">最近订单</h2>
            <p>按下单时间展示最新记录</p>
          </div>
          ${hasPermission("sales:view") ? `<a class="text-button" href="#/sales">全部 ${icon("chevron-right", "icon-sm")}</a>` : ""}
        </div>
        ${recentOrders.length ? `
          <div class="list-card">
            ${recentOrders.map(recentOrderRow).join("")}
          </div>
        ` : emptyState("暂无最近订单", "有新的销售订单后，会在这里显示。")}
      </section>
    `;
    renderShell(content, "/home");
  }

  async function loadHome(force = false) {
    if (!state.home) state.home = { loading: false, loaded: false, error: "" };
    if (state.home.loading) return;
    if (state.home.loaded && !force) return;
    state.home.loading = true;
    state.home.error = "";

    const tasks = [
      hasPermission("dashboard:view")
        ? api("/reports/dashboard").catch((error) => ({ __error: error }))
        : Promise.resolve(null),
      hasPermission("report:view")
        ? api("/reports/sales-monthly", { query: { page: 1, size: 6 } }).catch((error) => ({ __error: error }))
        : Promise.resolve(null),
      hasPermission("gsp:view")
        ? api("/gsp/alerts/summary").catch((error) => ({ __error: error }))
        : Promise.resolve(null),
      hasPermission("sales:view")
        ? api("/sales-orders", { query: { page: 1, size: 3 } }).catch((error) => ({ __error: error }))
        : Promise.resolve(null),
    ];
    const [dashboard, monthlyPage, gspSummary, ordersPage] = await Promise.all(tasks);
    state.home.loading = false;
    state.home.loaded = true;
    state.home.dashboard = dashboard?.__error ? null : dashboard;
    state.home.monthly = monthlyPage?.__error ? null : monthlyPage?.items;
    state.home.gspSummary = gspSummary?.__error ? null : gspSummary;
    state.home.recentOrders = ordersPage?.__error ? null : ordersPage?.items;
    const errors = [dashboard, monthlyPage, gspSummary, ordersPage]
      .filter((item) => item?.__error)
      .map((item) => item.__error.message);
    state.home.error = errors.length ? errors[0] : "";
    if (state.route === "/home" || state.route === "/home/sales-trend") render();
  }

  function salesState() {
    if (!state.sales) {
      state.sales = {
        loading: false,
        loaded: false,
        error: "",
        page: 1,
        size: 20,
        total: 0,
        rows: [],
        filters: { status: "", order_no: "", customer_id: "", customerLabel: "" },
      };
    }
    return state.sales;
  }

  function orderCard(order) {
    return `
      <button class="order-card" type="button" data-action="open-order" data-id="${order.id}">
        <div class="card-topline">
          <span class="card-code">${escapeHtml(order.order_no)}</span>
          ${statusBadge(order.status)}
        </div>
        <h2 class="card-title">${escapeHtml(order.customer_name || `客户 ${order.customer_id}`)}</h2>
        <p class="card-subtitle">${escapeHtml(order.employee_name || "未分配销售员")} · ${escapeHtml(order.warehouse_name || "仓库待定")}</p>
        <div class="card-meta-row">
          <div class="card-meta">
            <span>${icon("calendar", "icon-sm")} ${fullDate(order.order_date)}</span>
            <span>${order.item_count || 0} 项 · ${number(order.total_quantity)} 件</span>
          </div>
          <span class="card-amount">¥${money(order.total_amount)}</span>
        </div>
      </button>
    `;
  }

  function paginationHtml(data, context) {
    if (!data) return "";
    const pages = Math.max(1, Math.ceil(Number(data.total || 0) / Number(data.size || 20)));
    return `
      <div class="pagination" aria-label="分页">
        <select class="select pager-size" data-action="page-size" data-context="${context}" aria-label="每页条数">
          ${[10, 20, 50, 100].map((size) => `
            <option value="${size}" ${Number(data.size) === size ? "selected" : ""}>每页 ${size}</option>
          `).join("")}
        </select>
        <span class="pager-total">共 ${number(data.total)} 条</span>
        <button class="pager-button" type="button" data-action="page-prev" data-context="${context}" aria-label="上一页" ${data.page <= 1 ? "disabled" : ""}>
          ${icon("arrow-left", "icon-sm")}
        </button>
        <span class="pager-page" aria-label="第 ${data.page} 页，共 ${pages} 页">${data.page}/${pages}</span>
        <button class="pager-button" type="button" data-action="page-next" data-context="${context}" aria-label="下一页" ${data.page >= pages ? "disabled" : ""}>
          ${icon("chevron-right", "icon-sm")}
        </button>
      </div>
    `;
  }

  function renderSalesRoute() {
    if (!hasPermission("sales:view")) {
      renderShell(pageHeading("销售订单", "按状态与客户追踪订单") + permissionState(), state.route);
      return;
    }
    if (state.route === "/sales/new") {
      renderCreateOrder();
      return;
    }
    if (/^\/sales\/\d+$/.test(state.route)) {
      renderSalesDetail();
      return;
    }
    renderSalesList();
  }

  function renderSalesList() {
    const sales = salesState();
    const filters = sales.filters;
    const content = `
      ${pageHeading(
        "销售订单",
        `${number(sales.loaded ? sales.total : 0)} 张订单 · 服务端分页`,
      )}
      <div class="toolbar-card">
        <form class="search-row" id="sales-search-form">
          <div class="search-field">
            ${icon("search")}
            <input
              class="field"
              id="sales-order-no"
              name="order_no"
              value="${escapeHtml(filters.order_no)}"
              placeholder="订单号，可输入片段"
              autocomplete="off"
              aria-label="订单号"
              data-test="filter-order-no"
            />
          </div>
          <button class="button compact" type="submit" data-test="btn-search">查询</button>
        </form>
        <div class="chip-row" role="group" aria-label="订单状态">
          ${["", "待付款", "已发货", "已完成", "已取消"].map((value) => `
            <button
              class="chip${filters.status === value ? " is-active" : ""}"
              type="button"
              data-action="sales-status"
              data-value="${escapeHtml(value)}"
            >${value || "全部"}</button>
          `).join("")}
        </div>
        <div class="filter-summary">
          <span class="filter-pill">
            客户：${escapeHtml(filters.customerLabel || "全部")}
            ${filters.customer_id ? `
              <button type="button" data-action="clear-sales-customer" aria-label="清除客户筛选">
                ${icon("x", "icon-sm")}
              </button>
            ` : ""}
          </span>
          <button class="chip" type="button" data-action="pick-sales-customer">
            ${icon("filter", "icon-sm")} 选择客户
          </button>
        </div>
      </div>
      ${hasPermission("sales:manage") ? `
        <div class="section-heading" style="margin-top:20px">
          <div><h2>订单列表</h2><p>点击订单查看明细与发货操作</p></div>
          <a class="button compact" href="#/sales/new">${icon("plus", "icon-sm")} 新建</a>
        </div>
      ` : ""}
      <div class="result-summary" aria-live="polite">
        ${sales.loading ? "正在加载订单…" : `共 ${number(sales.total)} 张订单`}
      </div>
      ${sales.error ? errorState(sales.error, "refresh-sales") : ""}
      ${!sales.error && sales.loading && !sales.rows.length ? skeletonPage() : ""}
      ${!sales.error && !sales.loading && !sales.rows.length ? emptyState(
        "没有匹配的订单",
        "调整订单号、状态或客户筛选后再试。",
        `<button class="button secondary compact" type="button" data-action="clear-sales-filters">清除筛选</button>`,
      ) : ""}
      ${sales.rows.length ? `<div class="order-list">${sales.rows.map(orderCard).join("")}</div>` : ""}
      ${paginationHtml(sales.loaded ? sales : null, "sales")}
    `;
    renderShell(content, "/sales");
    if (!sales.loaded && !sales.loading && !sales.error) loadSales();
  }

  async function loadSales() {
    const sales = salesState();
    if (sales.loading) return;
    sales.loading = true;
    sales.error = "";
    if (state.route === "/sales") render();
    try {
      const data = await api("/sales-orders", {
        query: {
          page: sales.page,
          size: sales.size,
          status: sales.filters.status,
          order_no: sales.filters.order_no.trim(),
          customer_id: sales.filters.customer_id,
        },
      });
      sales.rows = data.items || [];
      sales.total = data.total || 0;
      sales.page = data.page || sales.page;
      sales.size = data.size || sales.size;
      sales.loaded = true;
    } catch (error) {
      sales.error = error.message;
    } finally {
      sales.loading = false;
      if (state.route === "/sales") render();
    }
  }

  function renderSalesDetail() {
    if (!hasPermission("sales:view")) {
      renderShell(pageHeading("订单详情", "查看明细与执行发货", true) + permissionState(), state.route);
      return;
    }
    const match = state.route.match(/^\/sales\/(\d+)$/);
    if (!match) {
      go("/sales", true);
      return;
    }
    const orderId = Number(match[1]);
    const cached = state.salesDetail.get(orderId);
    if (!cached || (!cached.loaded && !cached.loading && !cached.error)) {
      renderShell(pageHeading("订单详情", "查看明细与执行发货", true) + skeletonPage(), state.route);
      loadSalesDetail(orderId);
      return;
    }
    if (cached.error) {
      renderShell(pageHeading("订单详情", "查看明细与执行发货", true) + errorState(cached.error, "retry-order"), state.route);
      return;
    }
    const order = cached.order;
    if (!order) return;
    const canManage = hasPermission("sales:manage");
    const canShip = canManage && !order.delivery_date && !["已取消", "已完成"].includes(order.status);
    const canCancel = canManage && canShip;
    const canDelete = canManage && order.status === "待付款" && !order.delivery_date;
    const content = `
      ${pageHeading("订单详情", order.order_no, true)}
      <article class="detail-hero">
        <div class="card-topline">
          <span class="permission-badge">${escapeHtml(order.status)}</span>
          <span class="muted small">${fullDate(order.order_date)}</span>
        </div>
        <h2 class="card-title" style="font-size:20px">${escapeHtml(order.customer_name || `客户 ${order.customer_id}`)}</h2>
        <div class="detail-amount">¥${money(order.total_amount)}</div>
        <div class="detail-grid">
          <div class="detail-item">
            <div class="label">已收金额</div>
            <div class="value money">¥${money(order.paid_amount)}</div>
          </div>
          <div class="detail-item">
            <div class="label">销售员</div>
            <div class="value">${escapeHtml(order.employee_name || "—")}</div>
          </div>
          <div class="detail-item">
            <div class="label">发货仓库</div>
            <div class="value">${escapeHtml(order.warehouse_name || "—")}</div>
          </div>
          <div class="detail-item">
            <div class="label">发货日期</div>
            <div class="value">${order.delivery_date ? fullDate(order.delivery_date) : "尚未发货"}</div>
          </div>
        </div>
        ${canShip || canCancel || canDelete ? `
          <div class="action-row">
            ${canShip ? `<button class="button" type="button" data-action="ship-order" data-id="${order.id}">${icon("truck", "icon-sm")} 发货</button>` : ""}
            ${canCancel ? `<button class="button secondary" type="button" data-action="cancel-order" data-id="${order.id}">取消订单</button>` : ""}
            ${canDelete ? `<button class="button secondary" type="button" data-action="delete-order" data-id="${order.id}">删除</button>` : ""}
          </div>
        ` : ""}
      </article>

      <section class="detail-card">
        <h2>订单明细</h2>
        ${(order.items || []).map((item) => `
          <div class="line-item">
            <div class="line-item-top">
              <div>
                <h3>${escapeHtml(item.product?.name || `商品 ${item.product_id}`)}</h3>
                <p>${escapeHtml(item.product?.sku || "")} · ${escapeHtml(item.product?.specification || "")}</p>
              </div>
              <span class="money">¥${money(item.amount)}</span>
            </div>
            <p>${number(item.quantity)} 件 × ¥${money(item.unit_price)} · 折扣 ${(Number(item.discount_rate || 0) * 100).toFixed(1)}%</p>
          </div>
        `).join("") || `<p class="muted">暂无明细</p>`}
      </section>

      <section class="detail-card">
        <h2>交付与结算</h2>
        <div class="detail-grid">
          <div class="detail-item"><div class="label">结算方式</div><div class="value">${escapeHtml(order.settlement_method)}</div></div>
          <div class="detail-item"><div class="label">开票类型</div><div class="value">${escapeHtml(order.invoice_type)}</div></div>
          <div class="detail-item"><div class="label">配送方式</div><div class="value">${escapeHtml(order.delivery_type)}</div></div>
          <div class="detail-item"><div class="label">优惠金额</div><div class="value money">¥${money(order.discount_amount)}</div></div>
        </div>
        <div class="field-group">
          <div class="field-label">收货地址</div>
          <p class="muted">${escapeHtml(order.shipping_address || "未填写")}</p>
        </div>
        ${order.remark ? `<div class="field-group"><div class="field-label">备注</div><p class="muted">${escapeHtml(order.remark)}</p></div>` : ""}
      </section>
    `;
    renderShell(content, state.route);
  }

  async function loadSalesDetail(orderId, force = false) {
    const existing = state.salesDetail.get(orderId);
    if (existing?.loading) return;
    if (existing?.loaded && !force) return;
    state.salesDetail.set(orderId, { loading: true, loaded: false, error: "", order: existing?.order });
    if (/^\/sales\/\d+$/.test(state.route)) render();
    try {
      const order = await api(`/sales-orders/${orderId}`);
      state.salesDetail.set(orderId, { loading: false, loaded: true, error: "", order });
    } catch (error) {
      state.salesDetail.set(orderId, { loading: false, loaded: true, error: error.message, order: null });
    }
    if (state.route === `/sales/${orderId}`) render();
  }

  function renderCreateOrder() {
    if (!hasPermission("sales:manage")) {
      renderShell(pageHeading("新建销售单", "客户、仓库与商品明细", true) + permissionState(), state.route);
      return;
    }
    const draft = ensureOrderDraft();
    const content = `
      ${pageHeading("新建销售单", "提交前请核对客户与商品资质", true)}
      <form id="create-order-form" novalidate>
        <div class="toolbar-card">
          <div class="field-label">基本信息</div>
          <div class="field-group">
            <label>客户 <span class="required" aria-hidden="true">*</span></label>
            <button class="select-like${draft.customer ? "" : " is-placeholder"}" type="button" data-action="pick-order-customer">
              <span>${escapeHtml(draft.customer?.name || "选择客户")}</span>
              ${icon("chevron-right", "icon-sm")}
            </button>
          </div>
          <div class="form-grid">
            <div class="field-group">
              <label>销售员 <span class="required" aria-hidden="true">*</span></label>
              <button class="select-like${draft.employee ? "" : " is-placeholder"}" type="button" data-action="pick-order-employee">
                <span>${escapeHtml(draft.employee?.name || "选择销售员")}</span>
                ${icon("chevron-right", "icon-sm")}
              </button>
            </div>
            <div class="field-group">
              <label>发货仓库 <span class="required" aria-hidden="true">*</span></label>
              <button class="select-like${draft.warehouse ? "" : " is-placeholder"}" type="button" data-action="pick-order-warehouse">
                <span>${escapeHtml(draft.warehouse?.name || "选择仓库")}</span>
                ${icon("chevron-right", "icon-sm")}
              </button>
            </div>
            <div class="field-group">
              <label for="order-date">下单日期 <span class="required" aria-hidden="true">*</span></label>
              <input class="field" id="order-date" type="date" value="${escapeHtml(draft.order_date)}" data-field="order_date" required />
            </div>
            <div class="field-group">
              <label for="settlement-method">结算方式</label>
              <select class="select" id="settlement-method" data-field="settlement_method">
                ${["现款", "月结30天", "月结60天", "月结90天"].map((value) => `<option ${draft.settlement_method === value ? "selected" : ""}>${value}</option>`).join("")}
              </select>
            </div>
            <div class="field-group">
              <label for="invoice-type">开票类型</label>
              <select class="select" id="invoice-type" data-field="invoice_type">
                ${["增值税专用发票", "增值税普通发票", "不开发票"].map((value) => `<option ${draft.invoice_type === value ? "selected" : ""}>${value}</option>`).join("")}
              </select>
            </div>
            <div class="field-group">
              <label for="delivery-type">配送方式</label>
              <select class="select" id="delivery-type" data-field="delivery_type">
                ${["常温运输", "冷链运输", "客户自提"].map((value) => `<option ${draft.delivery_type === value ? "selected" : ""}>${value}</option>`).join("")}
              </select>
            </div>
          </div>
        </div>

        <section class="section">
          <div class="section-heading">
            <div><h2>商品明细</h2><p>金额与库存由服务端校验</p></div>
            <button class="text-button" type="button" data-action="add-order-line">${icon("plus", "icon-sm")} 添加</button>
          </div>
          <div id="order-lines">
            ${draft.lines.map((line, index) => renderOrderLine(line, index)).join("")}
          </div>
        </section>

        <div class="toolbar-card">
          <div class="field-group">
            <label for="shipping-address">收货地址</label>
            <input class="field" id="shipping-address" value="${escapeHtml(draft.shipping_address)}" data-field="shipping_address" placeholder="请输入收货地址" />
          </div>
          <div class="field-group">
            <label for="order-remark">备注</label>
            <textarea class="field" id="order-remark" rows="3" data-field="remark" placeholder="选填">${escapeHtml(draft.remark)}</textarea>
          </div>
          <div class="notice">
            ${icon("shield", "is-hide")}
            <span>下单和发货时，服务端会再次校验客户、商品资质及库存。资质不合规时订单将被阻止。</span>
          </div>
          <p class="inline-error" id="create-order-error" role="alert"></p>
          <div class="form-actions">
            <button class="button secondary" type="button" data-action="go-back">取消</button>
            <button class="button" type="submit" data-test="create-order-submit">提交订单</button>
          </div>
        </div>
      </form>
    `;
    renderShell(content, "/sales/new");
  }

  function ensureOrderDraft() {
    if (!state.orderDraft) {
      state.orderDraft = {
        customer: null,
        employee: null,
        warehouse: null,
        order_date: todayISO(),
        settlement_method: "现款",
        invoice_type: "增值税专用发票",
        delivery_type: "常温运输",
        shipping_address: "",
        remark: "",
        lines: [{ product: null, quantity: 1, discount_rate: 0 }],
      };
    }
    return state.orderDraft;
  }

  function renderOrderLine(line, index) {
    return `
      <div class="create-line" data-line-index="${index}">
        <div class="create-line-top">
          <span class="create-line-index">商品 ${index + 1}</span>
          ${state.orderDraft.lines.length > 1 ? `
            <button class="icon-button" type="button" data-action="remove-order-line" data-index="${index}" aria-label="移除商品 ${index + 1}">
              ${icon("x", "icon-sm")}
            </button>
          ` : ""}
        </div>
        <div class="field-group">
          <button class="select-like${line.product ? "" : " is-placeholder"}" type="button" data-action="pick-order-product" data-index="${index}">
            <span>${escapeHtml(line.product?.name || "选择商品")}</span>
            ${icon("chevron-right", "icon-sm")}
          </button>
        </div>
        <div class="create-line-fields">
          <div>
            <label class="field-label" for="line-quantity-${index}">数量</label>
            <input class="field" id="line-quantity-${index}" type="number" min="1" step="1" value="${escapeHtml(line.quantity)}" data-line-quantity="${index}" />
          </div>
          <div>
            <label class="field-label" for="line-discount-${index}">折扣率</label>
            <input class="field" id="line-discount-${index}" type="number" min="0" max="100" step="0.1" value="${(Number(line.discount_rate || 0) * 100).toFixed(1)}" data-line-discount="${index}" />
          </div>
        </div>
        <p class="field-help">折扣率按百分比填写，例如 5 表示优惠 5%。</p>
      </div>
    `;
  }

  function inventoryState() {
    if (!state.inventory) {
      state.inventory = {
        loading: false,
        loaded: false,
        error: "",
        page: 1,
        size: 20,
        total: 0,
        rows: [],
        filters: {
          status: "",
          product_id: "",
          productLabel: "",
          warehouse_id: "",
          warehouseLabel: "",
        },
      };
    }
    return state.inventory;
  }

  function inventoryCard(row) {
    const warning = row.stock_status === "库存不足"
      ? "is-danger"
      : row.stock_status === "库存预警"
        ? "is-warning"
        : "";
    const ratio = Math.min(
      100,
      Math.max(2, Math.round((Number(row.quantity || 0) / Math.max(Number(row.safety_stock || 1) * 2, 1)) * 100)),
    );
    return `
      <article class="inventory-card">
        <div class="card-topline">
          <span class="card-code">${escapeHtml(row.sku || "未设置 SKU")}</span>
          ${statusBadge(row.stock_status || "库存状态")}
        </div>
        <h2 class="card-title">${escapeHtml(row.product_name || `商品 ${row.product_id}`)}</h2>
        <p class="card-subtitle">${escapeHtml(row.warehouse_name || "未命名仓库")} · ${escapeHtml(row.category_name || "未分类")}</p>
        <div class="quantity-line">
          <div>
            <div class="quantity-value">${number(row.quantity)} <small>件</small></div>
            <div class="safety-line">安全库存 ${number(row.safety_stock)} 件</div>
          </div>
          <div class="card-meta">库存价值<br /><span class="money">¥${compactMoney(row.stock_value)}</span></div>
        </div>
        <div class="stock-bar ${warning}" aria-hidden="true"><span style="width:${ratio}%"></span></div>
      </article>
    `;
  }

  function renderInventory() {
    if (!hasPermission("inventory:view")) {
      renderShell(pageHeading("库存查询", "仓库库存与安全库存预警") + permissionState(), "/inventory");
      return;
    }
    const inventory = inventoryState();
    const content = `
      ${pageHeading("库存查询", `${number(inventory.total)} 条仓库商品库存`)}
      <div class="toolbar-card">
        <div class="chip-row" role="group" aria-label="库存状态">
          ${["", "库存不足", "库存预警", "库存充足"].map((value) => `
            <button class="chip${inventory.filters.status === value ? " is-active" : ""}" type="button" data-action="inventory-status" data-value="${escapeHtml(value)}">
              ${value || "全部"}
            </button>
          `).join("")}
        </div>
        <div class="filter-summary">
          <button class="chip" type="button" data-action="pick-inventory-product">${icon("box", "icon-sm")} 商品：${escapeHtml(inventory.filters.productLabel || "全部")}</button>
          <button class="chip" type="button" data-action="pick-inventory-warehouse">${icon("warehouse", "icon-sm")} 仓库：${escapeHtml(inventory.filters.warehouseLabel || "全部")}</button>
          ${(inventory.filters.product_id || inventory.filters.warehouse_id || inventory.filters.status) ? `
            <button class="chip" type="button" data-action="clear-inventory-filters">${icon("x", "icon-sm")} 清除</button>
          ` : ""}
        </div>
      </div>
      <div class="result-summary" aria-live="polite">${inventory.loading ? "正在加载库存…" : `共 ${number(inventory.total)} 条库存记录`}</div>
      ${inventory.error ? errorState(inventory.error, "refresh-inventory") : ""}
      ${!inventory.error && inventory.loading && !inventory.rows.length ? skeletonPage() : ""}
      ${!inventory.error && !inventory.loading && !inventory.rows.length ? emptyState("没有匹配的库存", "调整商品、仓库或库存状态后再试。") : ""}
      ${inventory.rows.length ? `<div class="inventory-list">${inventory.rows.map(inventoryCard).join("")}</div>` : ""}
      ${paginationHtml(inventory.loaded ? inventory : null, "inventory")}
    `;
    renderShell(content, "/inventory");
    if (!inventory.loaded && !inventory.loading && !inventory.error) loadInventory();
  }

  async function loadInventory() {
    const inventory = inventoryState();
    if (inventory.loading) return;
    inventory.loading = true;
    inventory.error = "";
    if (state.route === "/inventory") render();
    try {
      const data = await api("/inventory", {
        query: {
          page: inventory.page,
          size: inventory.size,
          status: inventory.filters.status,
          product_id: inventory.filters.product_id,
          warehouse_id: inventory.filters.warehouse_id,
        },
      });
      inventory.rows = data.items || [];
      inventory.total = data.total || 0;
      inventory.page = data.page || inventory.page;
      inventory.size = data.size || inventory.size;
      inventory.loaded = true;
    } catch (error) {
      inventory.error = error.message;
    } finally {
      inventory.loading = false;
      if (state.route === "/inventory") render();
    }
  }

  function complianceState() {
    if (!state.compliance) {
      state.compliance = {
        loading: false,
        loaded: false,
        error: "",
        summaryLoading: false,
        page: 1,
        size: 20,
        total: 0,
        rows: [],
        summary: null,
        category: "all",
        level: "all",
      };
    }
    return state.compliance;
  }

  function alertCard(alert) {
    const remaining = Number(alert.days_left);
    return `
      <article class="alert-card">
        <div class="card-topline">
          <span class="status ${alert.category === "certificate" ? "is-primary" : "is-success"}">
            ${alert.category === "certificate" ? "证照" : "批次"}
          </span>
          ${statusBadge(alert.level)}
        </div>
        <h2 class="card-title">${escapeHtml(alert.title)}</h2>
        <p class="card-subtitle">${escapeHtml(alert.subject)}</p>
        <div class="quantity-line">
          <div class="card-meta">
            <span>${icon("calendar", "icon-sm")} ${fullDate(alert.valid_to)}</span>
          </div>
          <span class="status ${remaining < 0 ? "is-danger" : remaining <= 30 ? "is-warning" : ""}">
            ${remaining < 0 ? `已过期 ${Math.abs(remaining)} 天` : `剩余 ${remaining} 天`}
          </span>
        </div>
      </article>
    `;
  }

  function renderCompliance() {
    if (!hasPermission("gsp:view")) {
      renderShell(pageHeading("GSP 合规", "证照与批次效期预警") + permissionState(), "/compliance");
      return;
    }
    const compliance = complianceState();
    const summary = compliance.summary;
    const totalRisks = summary
      ? summary.expired + summary.within_30 + summary.within_60 + summary.within_90
      : 0;
    const stat = (level, label, value) => `
      <button class="compliance-stat" type="button" data-action="gsp-level" data-value="${level}">
        <span class="value">${number(value)}</span>
        <span class="label">${label}</span>
      </button>
    `;
    const content = `
      ${pageHeading("GSP 合规", "统一查看证照与批次效期风险")}
      <section class="compliance-hero">
        <div class="compliance-score">
          <div class="compliance-emblem">${icon(summary ? "shield" : "clock", "icon-lg")}</div>
          <div>
            <h2>${summary ? (totalRisks ? "有项目需要跟进" : "当前未发现到期风险") : "正在读取合规概况"}</h2>
            <p>${summary ? `90 天内预警 ${number(totalRisks)} 项 · 待审核 ${number(summary.pending_review)} 项` : "请稍候"}</p>
          </div>
        </div>
        <div class="compliance-grid">
          ${stat("已过期", "已过期", summary?.expired)}
          ${stat("30天内", "30 天内", summary?.within_30)}
          ${stat("60天内", "31–60 天", summary?.within_60)}
          ${stat("90天内", "61–90 天", summary?.within_90)}
        </div>
        ${summary && !totalRisks ? `
          <div class="notice" style="background:var(--success-soft);color:var(--success)">
            ${icon("check")}
            <span>当前证照与批次均在预警窗口外，继续保持有效管理与定期复核。</span>
          </div>
        ` : ""}
      </section>

      <section class="section">
        <div class="section-heading">
          <div><h2>预警明细</h2><p>点击上方统计可快速切换到期区间</p></div>
        </div>
        <div class="toolbar-card">
          <div class="chip-row" role="group" aria-label="预警类别">
            ${[["all", "全部"], ["certificate", "证照"], ["batch", "批次"]].map(([value, label]) => `
              <button class="chip${compliance.category === value ? " is-active" : ""}" type="button" data-action="gsp-category" data-value="${value}">${label}</button>
            `).join("")}
            ${compliance.level !== "all" ? `<button class="chip is-active" type="button" data-action="gsp-level" data-value="all">${escapeHtml(compliance.level)} ×</button>` : ""}
          </div>
        </div>
        <div class="result-summary" aria-live="polite">${compliance.loading ? "正在加载预警…" : `共 ${number(compliance.total)} 条预警`}</div>
        ${compliance.error ? errorState(compliance.error, "refresh-compliance") : ""}
        ${!compliance.error && compliance.loading && !compliance.rows.length ? skeletonPage() : ""}
        ${!compliance.error && !compliance.loading && !compliance.rows.length ? emptyState("暂无预警", "当前的证照与批次没有落入所选到期区间。") : ""}
        ${compliance.rows.length ? `<div class="alert-list">${compliance.rows.map(alertCard).join("")}</div>` : ""}
        ${paginationHtml(compliance.loaded ? compliance : null, "compliance")}
      </section>
    `;
    renderShell(content, "/compliance");
    if (!compliance.loaded && !compliance.loading && !compliance.error) loadCompliance();
    if (!compliance.summary && !compliance.summaryLoading) loadComplianceSummary();
  }

  async function loadCompliance() {
    const compliance = complianceState();
    if (compliance.loading) return;
    compliance.loading = true;
    compliance.error = "";
    if (state.route === "/compliance") render();
    try {
      const data = await api("/gsp/alerts", {
        query: {
          page: compliance.page,
          size: compliance.size,
          category: compliance.category,
          level: compliance.level,
        },
      });
      compliance.rows = data.items || [];
      compliance.total = data.total || 0;
      compliance.page = data.page || compliance.page;
      compliance.size = data.size || compliance.size;
      compliance.loaded = true;
    } catch (error) {
      compliance.error = error.message;
    } finally {
      compliance.loading = false;
      if (state.route === "/compliance") render();
    }
  }

  async function loadComplianceSummary() {
    const compliance = complianceState();
    if (compliance.summaryLoading) return;
    compliance.summaryLoading = true;
    try {
      compliance.summary = await api("/gsp/alerts/summary");
    } catch {
      compliance.summary = null;
    } finally {
      compliance.summaryLoading = false;
      if (state.route === "/compliance") render();
    }
  }

  function renderProfile() {
    const me = state.me;
    const roles = (me.roles || []).map((role) => role.name).join(" · ") || "未分配角色";
    const content = `
      <section class="profile-card">
        <div class="profile-avatar" aria-hidden="true">${initials(me.display_name || me.username)}</div>
        <div class="profile-copy">
          <h1>${escapeHtml(me.display_name || me.username)}</h1>
          <p>@${escapeHtml(me.username)} · ${escapeHtml(roles)}</p>
        </div>
      </section>

      <section class="section">
        <div class="section-heading">
          <div><h2>账号信息</h2><p>当前身份的权限与联系方式</p></div>
        </div>
        <div class="metric-grid">
          <article class="metric-card">
            <div class="metric-card-top"><span class="metric-icon">${icon("shield", "icon-sm")}</span>权限范围</div>
            <div class="metric-value">${me.is_superuser || (me.permissions || []).includes("all") ? "全部" : number((me.permissions || []).length)} <span class="metric-unit">${me.is_superuser ? "管理员" : "项"}</span></div>
          </article>
          <article class="metric-card">
            <div class="metric-card-top"><span class="metric-icon is-success">${icon("user", "icon-sm")}</span>账号状态</div>
            <div class="metric-value" style="font-size:19px">${me.is_active ? "正常使用" : "已停用"}</div>
          </article>
        </div>
        <div class="detail-card">
          <div class="detail-grid">
            <div class="detail-item"><div class="label">电话</div><div class="value">${escapeHtml(me.phone || "未填写")}</div></div>
            <div class="detail-item"><div class="label">邮箱</div><div class="value">${escapeHtml(me.email || "未填写")}</div></div>
          </div>
        </div>
      </section>

      <section class="section">
        <div class="section-heading"><h2>设置</h2></div>
        <div class="settings-list">
          <button class="settings-row" type="button" data-action="open-language">
            <span class="leading-icon">${icon("globe", "icon-sm")}</span>
            <span class="settings-copy">
              <span class="settings-title">语言</span>
              <span class="settings-value">${escapeHtml(localeLabel())}</span>
            </span>
            ${icon("chevron-right", "icon-sm")}
          </button>
          <button class="settings-row" type="button" data-action="toggle-theme">
            <span class="leading-icon">${icon(state.theme === "dark" ? "moon" : "sun", "icon-sm")}</span>
            <span class="settings-copy">
              <span class="settings-title">主题</span>
              <span class="settings-value">${state.theme === "dark" ? "深色" : "浅色"}</span>
            </span>
            ${icon("chevron-right", "icon-sm")}
          </button>
          <button class="settings-row" type="button" data-action="edit-profile">
            <span class="leading-icon">${icon("edit", "icon-sm")}</span>
            <span class="settings-copy">
              <span class="settings-title">编辑个人资料</span>
              <span class="settings-value">显示名称、电话与邮箱</span>
            </span>
            ${icon("chevron-right", "icon-sm")}
          </button>
          <button class="settings-row" type="button" data-action="change-password">
            <span class="leading-icon">${icon("lock", "icon-sm")}</span>
            <span class="settings-copy">
              <span class="settings-title">修改密码</span>
              <span class="settings-value">需要验证当前密码</span>
            </span>
            ${icon("chevron-right", "icon-sm")}
          </button>
          <button class="settings-row" type="button" data-action="server-settings">
            <span class="leading-icon">${icon("server", "icon-sm")}</span>
            <span class="settings-copy">
              <span class="settings-title">服务器地址</span>
              <span class="settings-value">${escapeHtml(state.serverUrl)}</span>
            </span>
            ${icon("chevron-right", "icon-sm")}
          </button>
          <button class="settings-row" type="button" data-action="reload-permissions">
            <span class="leading-icon">${icon("refresh", "icon-sm")}</span>
            <span class="settings-copy">
              <span class="settings-title">刷新账号权限</span>
              <span class="settings-value">管理员调整角色后使用</span>
            </span>
            ${icon("chevron-right", "icon-sm")}
          </button>
        </div>
      </section>

      <section class="section">
        <div class="settings-list">
          <button class="settings-row is-danger" type="button" data-action="logout">
            <span class="leading-icon">${icon("logout", "icon-sm")}</span>
            <span class="settings-copy">
              <span class="settings-title">退出登录</span>
              <span class="settings-value">清除本机保存的登录令牌</span>
            </span>
          </button>
        </div>
        <p class="login-footer">medapp 1.0.0 · 医药销售移动工作台</p>
      </section>
    `;
    renderShell(content, "/profile");
  }

  function showDialog({
    title,
    description = "",
    body = "",
    confirmText = "确定",
    cancelText = "取消",
    danger = false,
    onConfirm,
    onClose,
  }) {
    closeDialog(false);
    state.dialogClose = onClose || null;
    dialogRoot.innerHTML = `
      <div class="dialog-backdrop" data-action="dialog-backdrop">
        <section class="dialog" role="dialog" aria-modal="true" aria-labelledby="dialog-title" aria-describedby="dialog-description">
          <div class="dialog-header">
            <div class="dialog-header-copy">
              <h2 id="dialog-title">${escapeHtml(title)}</h2>
              <p id="dialog-description">${escapeHtml(description)}</p>
            </div>
            <button class="icon-button" type="button" data-action="dialog-close" aria-label="关闭">${icon("x")}</button>
          </div>
          <div class="dialog-body">
            ${body}
            <p class="inline-error" id="dialog-error" role="alert"></p>
          </div>
          <div class="dialog-footer">
            <button class="button secondary" type="button" data-action="dialog-close">${escapeHtml(cancelText)}</button>
            <button class="button${danger ? " danger" : ""}" type="button" data-action="dialog-confirm">${escapeHtml(confirmText)}</button>
          </div>
        </section>
      </div>
    `;
    state.dialogConfirm = onConfirm;
    const target = dialogRoot.querySelector("input, textarea, button[data-action='dialog-confirm']");
    window.setTimeout(() => target?.focus(), 40);
  }

  function closeDialog(notify = true) {
    if (!dialogRoot.firstElementChild) return;
    dialogRoot.innerHTML = "";
    const callback = state.dialogClose;
    state.dialogClose = null;
    state.dialogConfirm = null;
    if (notify) callback?.(false);
    const main = document.getElementById("main-content");
    main?.focus({ preventScroll: true });
  }

  async function handleDialogConfirm(button) {
    if (!state.dialogConfirm) {
      closeDialog();
      return;
    }
    const errorNode = document.getElementById("dialog-error");
    const originalLabel = button.textContent;
    button.disabled = true;
    button.innerHTML = `<span class="button-spinner" aria-hidden="true"></span><span>处理中</span>`;
    errorNode.textContent = "";
    try {
      const shouldClose = await state.dialogConfirm(button);
      if (shouldClose !== false) closeDialog(false);
    } catch (error) {
      errorNode.textContent = error.message || "操作失败，请重试";
    } finally {
      button.disabled = false;
      button.textContent = originalLabel;
    }
  }

  function askConfirm({ title, description, confirmText = "确定", danger = false }) {
    return new Promise((resolve) => {
      let settled = false;
      const finish = (value) => {
        if (settled) return;
        settled = true;
        resolve(value);
      };
      showDialog({
        title,
        description,
        confirmText,
        danger,
        onConfirm: async () => {
          finish(true);
          return true;
        },
        onClose: finish,
      });
    });
  }

  async function openEntityPicker({ entity, title, description, onSelect }) {
    state.picker = { entity, onSelect, options: [] };
    showDialog({
      title,
      description,
      confirmText: "关闭",
      cancelText: "返回",
      body: `
        <div class="search-field">
          ${icon("search")}
          <input class="field" id="picker-search" placeholder="输入名称或编码检索" autocomplete="off" aria-label="检索${escapeHtml(title)}" />
        </div>
        <div class="picker-list" id="picker-list">
          <div class="skeleton skeleton-row"></div>
          <div class="skeleton skeleton-row"></div>
          <div class="skeleton skeleton-row"></div>
        </div>
      `,
      onConfirm: async () => true,
    });
    try {
      const cached = state.options.get(entity);
      const options = cached || await api(`/options/${entity}`);
      if (!cached) state.options.set(entity, options || []);
      state.picker.options = options || [];
      renderPickerOptions("");
      const input = document.getElementById("picker-search");
      window.setTimeout(() => input?.focus(), 50);
    } catch (error) {
      const list = document.getElementById("picker-list");
      if (list) list.innerHTML = `<p class="inline-error">${escapeHtml(error.message)}</p>`;
    }
  }

  function renderPickerOptions(keyword) {
    const list = document.getElementById("picker-list");
    if (!list || !state.picker) return;
    const needle = keyword.trim().toLowerCase();
    const matches = state.picker.options
      .filter((option) => {
        if (!needle) return true;
        return `${option.code || ""} ${option.name || ""}`.toLowerCase().includes(needle);
      })
      .slice(0, 60);
    list.innerHTML = matches.length
      ? matches.map((option) => `
          <button class="picker-option" type="button" data-action="pick-option" data-id="${option.id}">
            <span class="picker-code">${escapeHtml(option.code || "—")}</span>
            <span class="picker-name">${escapeHtml(option.name)}</span>
            ${icon("chevron-right", "icon-sm")}
          </button>
        `).join("")
      : `<p class="muted" style="padding:20px 4px">没有匹配的候选数据，请调整关键词。</p>`;
  }

  function choosePickerOption(id) {
    const option = state.picker?.options.find((item) => Number(item.id) === Number(id));
    if (!option) return;
    const callback = state.picker.onSelect;
    state.picker = null;
    closeDialog(false);
    callback?.(option);
  }

  async function handleLogin(form) {
    const button = form.querySelector("[type='submit']");
    const errorNode = form.querySelector(".inline-error");
    const formData = new FormData(form);
    const username = String(formData.get("username") || "").trim();
    const password = String(formData.get("password") || "");
    const server = String(formData.get("server") || "").trim();
    state.loginError = "";
    if (errorNode) errorNode.textContent = "";
    if (!username || !password) {
      state.loginError = "请输入用户名和密码。";
      renderLogin();
      document.getElementById("login-username")?.focus();
      return;
    }
    if (!setServerAddress(server)) {
      state.loginError = "服务器地址格式不正确，请填写包含 http:// 或 https:// 的根地址。";
      renderLogin();
      document.getElementById("login-server")?.focus();
      return;
    }
    button.disabled = true;
    button.innerHTML = `<span class="button-spinner" aria-hidden="true"></span><span>登录中</span>`;
    try {
      const tokenData = await api("/auth/login", {
        method: "POST",
        body: { username, password },
        token: "",
        keepSession: true,
      });
      state.token = tokenData.access_token;
      localStorage.setItem(STORAGE.token, state.token);
      localStorage.setItem(STORAGE.username, username);
      const me = await api("/auth/me", { token: state.token, keepSession: true });
      state.me = me;
      state.loginError = "";
      setLive(`登录成功，欢迎 ${me.display_name || me.username}`);
      go(landingRoute(), true);
    } catch (error) {
      state.token = "";
      localStorage.removeItem(STORAGE.token);
      state.loginError = error.message;
      renderLogin();
      document.getElementById("login-password")?.focus();
    }
  }

  async function refreshMe(showSuccess = false) {
    try {
      state.me = await api("/auth/me", { keepSession: true });
      if (showSuccess) toast("账号权限已刷新");
      render();
    } catch (error) {
      toast(error.message, "error");
    }
  }

  function openShipDialog(orderId) {
    showDialog({
      title: "确认发货",
      description: "发货后库存将扣减，订单状态同步更新。",
      confirmText: "确认发货",
      body: `
        <div class="field-group">
          <label for="ship-date">发货日期</label>
          <input class="field" id="ship-date" type="date" value="${todayISO()}" required />
        </div>
      `,
      onConfirm: async () => {
        const deliveryDate = document.getElementById("ship-date")?.value;
        if (!deliveryDate) throw new Error("请选择发货日期");
        await api(`/sales-orders/${orderId}/ship`, {
          method: "POST",
          body: { delivery_date: deliveryDate },
        });
        nativeHaptic();
        toast("发货成功");
        state.sales = null;
        state.salesDetail.delete(orderId);
        render();
        await loadSalesDetail(orderId, true);
        return true;
      },
    });
  }

  async function cancelOrder(orderId) {
    const confirmed = await askConfirm({
      title: "取消该订单？",
      description: "取消后订单不可继续发货。已发货订单请通过退货流程处理。",
      confirmText: "取消订单",
      danger: true,
    });
    if (!confirmed) return;
    try {
      await api(`/sales-orders/${orderId}/cancel`, { method: "POST" });
      toast("订单已取消");
      state.sales = null;
      state.salesDetail.delete(orderId);
      render();
      await loadSalesDetail(orderId, true);
    } catch (error) {
      toast(error.message, "error");
    }
  }

  async function deleteOrder(orderId) {
    const confirmed = await askConfirm({
      title: "删除该订单？",
      description: "仅待付款且未发货的订单可以删除，操作完成后不可恢复。",
      confirmText: "删除订单",
      danger: true,
    });
    if (!confirmed) return;
    try {
      await api(`/sales-orders/${orderId}`, { method: "DELETE" });
      state.sales = null;
      state.salesDetail.delete(orderId);
      state.home = null;
      toast("订单已删除");
      go("/sales", true);
    } catch (error) {
      toast(error.message, "error");
    }
  }

  async function submitCreateOrder(form) {
    const draft = ensureOrderDraft();
    const errorNode = document.getElementById("create-order-error");
    const button = form.querySelector("[type='submit']");
    errorNode.textContent = "";
    if (!draft.customer || !draft.employee || !draft.warehouse || !draft.order_date) {
      errorNode.textContent = "请选择客户、销售员、发货仓库并填写下单日期。";
      return;
    }
    if (!draft.lines.length || draft.lines.some((line) => !line.product || Number(line.quantity) <= 0)) {
      errorNode.textContent = "请为每条明细选择商品并填写有效数量。";
      return;
    }
    button.disabled = true;
    button.innerHTML = `<span class="button-spinner" aria-hidden="true"></span><span>提交中</span>`;
    try {
      const order = await api("/sales-orders", {
        method: "POST",
        body: {
          customer_id: draft.customer.id,
          employee_id: draft.employee.id,
          warehouse_id: draft.warehouse.id,
          order_date: draft.order_date,
          shipping_address: draft.shipping_address || null,
          invoice_type: draft.invoice_type,
          settlement_method: draft.settlement_method,
          delivery_type: draft.delivery_type,
          remark: draft.remark || null,
          items: draft.lines.map((line) => ({
            product_id: line.product.id,
            quantity: Number(line.quantity),
            discount_rate: Number(line.discount_rate || 0),
          })),
        },
      });
      state.orderDraft = null;
      state.sales = null;
      state.home = null;
      nativeHaptic();
      toast(`订单 ${order.order_no} 已创建`);
      go(`/sales/${order.id}`, true);
    } catch (error) {
      errorNode.textContent = error.message;
    } finally {
      button.disabled = false;
      button.textContent = "提交订单";
    }
  }

  function handlePageChange(context, direction) {
    if (context === "sales") {
      const sales = salesState();
      sales.page += direction;
      loadSales();
    } else if (context === "inventory") {
      const inventory = inventoryState();
      inventory.page += direction;
      loadInventory();
    } else if (context === "compliance") {
      const compliance = complianceState();
      compliance.page += direction;
      loadCompliance();
    }
  }

  function resetSalesAndLoad() {
    const sales = salesState();
    sales.page = 1;
    sales.loaded = false;
    loadSales();
  }

  function resetInventoryAndLoad() {
    const inventory = inventoryState();
    inventory.page = 1;
    inventory.loaded = false;
    loadInventory();
  }

  function resetComplianceAndLoad() {
    const compliance = complianceState();
    compliance.page = 1;
    compliance.loaded = false;
    loadCompliance();
  }

  async function handleClick(event) {
    const actionNode = event.target.closest("[data-action]");
    if (!actionNode) return;
    const action = actionNode.dataset.action;
    const value = actionNode.dataset.value || "";

    if (action === "dialog-backdrop" && event.target === actionNode) closeDialog();
    else if (action === "dialog-close") closeDialog();
    else if (action === "dialog-confirm") await handleDialogConfirm(actionNode);
    else if (action === "open-language") openLanguageSettings();
    else if (action === "set-locale") {
      setLocale(value);
      closeDialog();
      render();
    } else if (action === "toggle-theme") {
      toggleTheme();
      render();
    } else if (action === "pick-option") choosePickerOption(actionNode.dataset.id);
    else if (action === "toggle-password") {
      state.passwordVisible = !state.passwordVisible;
      const input = document.getElementById("login-password");
      if (input) {
        input.type = state.passwordVisible ? "text" : "password";
        actionNode.innerHTML = icon(state.passwordVisible ? "eye-off" : "eye");
        actionNode.setAttribute("aria-label", state.passwordVisible ? "隐藏密码" : "显示密码");
        input.focus();
      }
    } else if (action === "go-back") {
      if (window.history.length > 1) window.history.back();
      else go("/home", true);
    } else if (action === "logout") {
      clearSession();
      state.loginError = "";
      go("/login", true);
      toast("已退出登录");
    } else if (action === "refresh-page") {
      const route = state.route;
      if (routeRoot(route) === "/home") await loadHome(true);
      else if (routeRoot(route) === "/sales") {
        state.sales = null;
        render();
      } else if (routeRoot(route) === "/inventory") {
        state.inventory = null;
        render();
      } else if (routeRoot(route) === "/compliance") {
        state.compliance = null;
        render();
      }
    } else if (action === "refresh-sales") {
      resetSalesAndLoad();
    } else if (action === "refresh-inventory") {
      resetInventoryAndLoad();
    } else if (action === "refresh-compliance") {
      resetComplianceAndLoad();
      loadComplianceSummary();
    } else if (action === "retry-order") {
      const orderId = Number(state.route.split("/").pop());
      state.salesDetail.delete(orderId);
      render();
    } else if (action === "open-order") {
      go(`/sales/${actionNode.dataset.id}`);
    } else if (action === "sales-status") {
      salesState().filters.status = value;
      resetSalesAndLoad();
    } else if (action === "clear-sales-customer") {
      const filters = salesState().filters;
      filters.customer_id = "";
      filters.customerLabel = "";
      resetSalesAndLoad();
    } else if (action === "clear-sales-filters") {
      const sales = salesState();
      sales.filters = { status: "", order_no: "", customer_id: "", customerLabel: "" };
      resetSalesAndLoad();
    } else if (action === "pick-sales-customer") {
      openEntityPicker({
        entity: "customer",
        title: "选择客户",
        description: "按名称或客户编码检索",
        onSelect: (option) => {
          const filters = salesState().filters;
          filters.customer_id = option.id;
          filters.customerLabel = option.name;
          resetSalesAndLoad();
        },
      });
    } else if (action === "ship-order") {
      openShipDialog(Number(actionNode.dataset.id));
    } else if (action === "cancel-order") {
      await cancelOrder(Number(actionNode.dataset.id));
    } else if (action === "delete-order") {
      await deleteOrder(Number(actionNode.dataset.id));
    } else if (action === "pick-order-customer" || action === "pick-order-employee" || action === "pick-order-warehouse") {
      const mapping = {
        "pick-order-customer": ["customer", "选择客户", "customer"],
        "pick-order-employee": ["employee", "选择销售员", "employee"],
        "pick-order-warehouse": ["warehouse", "选择发货仓库", "warehouse"],
      };
      const [entity, title, field] = mapping[action];
      openEntityPicker({
        entity,
        title,
        description: `选择本次订单使用的${title.replace("选择", "")}`,
        onSelect: (option) => {
          ensureOrderDraft()[field] = option;
          render();
        },
      });
    } else if (action === "pick-order-product") {
      const index = Number(actionNode.dataset.index);
      openEntityPicker({
        entity: "product",
        title: "选择商品",
        description: "按商品名称或 SKU 检索",
        onSelect: (option) => {
          ensureOrderDraft().lines[index].product = option;
          render();
        },
      });
    } else if (action === "add-order-line") {
      ensureOrderDraft().lines.push({ product: null, quantity: 1, discount_rate: 0 });
      render();
    } else if (action === "remove-order-line") {
      const index = Number(actionNode.dataset.index);
      ensureOrderDraft().lines.splice(index, 1);
      render();
    } else if (action === "pick-inventory-product" || action === "pick-inventory-warehouse") {
      const isProduct = action === "pick-inventory-product";
      openEntityPicker({
        entity: isProduct ? "product" : "warehouse",
        title: isProduct ? "选择商品" : "选择仓库",
        description: "按名称或编码检索",
        onSelect: (option) => {
          const filters = inventoryState().filters;
          if (isProduct) {
            filters.product_id = option.id;
            filters.productLabel = option.name;
          } else {
            filters.warehouse_id = option.id;
            filters.warehouseLabel = option.name;
          }
          resetInventoryAndLoad();
        },
      });
    } else if (action === "inventory-status") {
      inventoryState().filters.status = value;
      resetInventoryAndLoad();
    } else if (action === "clear-inventory-filters") {
      const inventory = inventoryState();
      inventory.filters = {
        status: "",
        product_id: "",
        productLabel: "",
        warehouse_id: "",
        warehouseLabel: "",
      };
      resetInventoryAndLoad();
    } else if (action === "gsp-level") {
      complianceState().level = value;
      resetComplianceAndLoad();
    } else if (action === "gsp-category") {
      complianceState().category = value;
      resetComplianceAndLoad();
    } else if (action === "page-prev") {
      handlePageChange(actionNode.dataset.context, -1);
    } else if (action === "page-next") {
      handlePageChange(actionNode.dataset.context, 1);
    } else if (action === "edit-profile") {
      openEditProfile();
    } else if (action === "change-password") {
      openChangePassword();
    } else if (action === "server-settings") {
      openServerSettings();
    } else if (action === "reload-permissions") {
      await refreshMe(true);
    }
  }

  function openLanguageSettings() {
    showDialog({
      title: "语言",
      description: "选择应用界面语言，设置会保存在本机。",
      confirmText: "完成",
      cancelText: "关闭",
      body: `
        <div class="language-options">
          ${SUPPORTED_LOCALES.map(([code, label]) => `
            <button
              class="language-option${state.locale === code ? " is-active" : ""}"
              type="button"
              data-action="set-locale"
              data-value="${code}"
              lang="${code}"
              data-test="locale-${code}"
            >
              <span>${escapeHtml(label)}</span>
              ${state.locale === code ? `<span class="language-check" aria-hidden="true">${icon("check", "icon-sm")}</span>` : ""}
            </button>
          `).join("")}
        </div>
      `,
      onConfirm: () => true,
    });
  }

  function openEditProfile() {
    showDialog({
      title: "编辑个人资料",
      description: "用户名不可修改，资料保存后立即生效。",
      confirmText: "保存",
      body: `
        <div class="field-group">
          <label for="profile-display-name">显示名称</label>
          <input class="field" id="profile-display-name" value="${escapeHtml(state.me.display_name || "")}" autocomplete="name" />
        </div>
        <div class="field-group">
          <label for="profile-phone">电话</label>
          <input class="field" id="profile-phone" type="tel" value="${escapeHtml(state.me.phone || "")}" autocomplete="tel" />
        </div>
        <div class="field-group">
          <label for="profile-email">邮箱</label>
          <input class="field" id="profile-email" type="email" value="${escapeHtml(state.me.email || "")}" autocomplete="email" />
        </div>
      `,
      onConfirm: async () => {
        const displayName = document.getElementById("profile-display-name").value.trim();
        if (!displayName) throw new Error("显示名称不能为空");
        state.me = await api("/auth/me", {
          method: "PUT",
          body: {
            display_name: displayName,
            phone: document.getElementById("profile-phone").value.trim() || null,
            email: document.getElementById("profile-email").value.trim() || null,
          },
        });
        toast("个人资料已更新");
        render();
        return true;
      },
    });
  }

  function openChangePassword() {
    showDialog({
      title: "修改密码",
      description: "新密码需与当前密码不同。",
      confirmText: "修改密码",
      body: `
        <div class="field-group">
          <label for="old-password">当前密码</label>
          <input class="field" id="old-password" type="password" autocomplete="current-password" />
        </div>
        <div class="field-group">
          <label for="new-password">新密码</label>
          <input class="field" id="new-password" type="password" autocomplete="new-password" />
        </div>
        <div class="field-group">
          <label for="confirm-password">确认新密码</label>
          <input class="field" id="confirm-password" type="password" autocomplete="new-password" />
        </div>
      `,
      onConfirm: async () => {
        const oldPassword = document.getElementById("old-password").value;
        const newPassword = document.getElementById("new-password").value;
        const confirmPassword = document.getElementById("confirm-password").value;
        if (!oldPassword || !newPassword) throw new Error("请完整填写当前密码与新密码");
        if (newPassword !== confirmPassword) throw new Error("两次输入的新密码不一致");
        await api("/auth/me/password", {
          method: "PUT",
          body: {
            old_password: oldPassword,
            new_password: newPassword,
            confirm_password: confirmPassword,
          },
        });
        toast("密码已修改，请妥善保管");
        return true;
      },
    });
  }

  function openServerSettings() {
    showDialog({
      title: "服务器地址",
      description: "修改后需要重新登录当前服务器。",
      confirmText: "保存并重新登录",
      body: `
        <div class="field-group">
          <label for="profile-server-url">后端根地址</label>
          <input class="field" id="profile-server-url" type="url" inputmode="url" autocapitalize="none" spellcheck="false" value="${escapeHtml(state.serverUrl)}" />
          <p class="field-help">模拟器可用 http://10.0.2.2:8001；真机填写后端所在电脑的局域网 IP。</p>
        </div>
      `,
      onConfirm: async () => {
        const input = document.getElementById("profile-server-url");
        const next = input.value.trim();
        if (!setServerAddress(next)) {
          input.focus();
          throw new Error("地址格式不正确，请填写 http:// 或 https:// 根地址");
        }
        clearSession();
        go("/login", true);
        toast("服务器地址已更新，请重新登录");
        return true;
      },
    });
  }

  async function handleSubmit(event) {
    if (event.target.id === "login-form") {
      event.preventDefault();
      await handleLogin(event.target);
      return;
    }
    if (event.target.id === "sales-search-form") {
      event.preventDefault();
      const sales = salesState();
      sales.filters.order_no = event.target.elements.order_no.value.trim();
      resetSalesAndLoad();
      return;
    }
    if (event.target.id === "create-order-form") {
      event.preventDefault();
      await submitCreateOrder(event.target);
    }
  }

  function handleInput(event) {
    if (event.target.id === "picker-search") {
      renderPickerOptions(event.target.value);
      return;
    }
    if (event.target.dataset.field && state.orderDraft) {
      state.orderDraft[event.target.dataset.field] = event.target.value;
    } else if (event.target.dataset.lineQuantity !== undefined && state.orderDraft) {
      const index = Number(event.target.dataset.lineQuantity);
      state.orderDraft.lines[index].quantity = event.target.value;
    } else if (event.target.dataset.lineDiscount !== undefined && state.orderDraft) {
      const index = Number(event.target.dataset.lineDiscount);
      state.orderDraft.lines[index].discount_rate = Number(event.target.value || 0) / 100;
    }
  }

  function handleChange(event) {
    if (event.target.dataset.action === "page-size") {
      const context = event.target.dataset.context;
      const size = Number(event.target.value);
      if (context === "sales") {
        const sales = salesState();
        sales.size = size;
        sales.page = 1;
        resetSalesAndLoad();
      } else if (context === "inventory") {
        const inventory = inventoryState();
        inventory.size = size;
        inventory.page = 1;
        resetInventoryAndLoad();
      } else if (context === "compliance") {
        const compliance = complianceState();
        compliance.size = size;
        compliance.page = 1;
        resetComplianceAndLoad();
      }
      return;
    }
    if (event.target.dataset.field && state.orderDraft) {
      state.orderDraft[event.target.dataset.field] = event.target.value;
    }
  }

  function handleKeydown(event) {
    if (event.key === "Escape" && dialogRoot.firstElementChild) {
      event.preventDefault();
      closeDialog();
      return;
    }
    if (event.key === "Tab" && dialogRoot.firstElementChild) {
      const focusable = [...dialogRoot.querySelectorAll(
        "button:not(:disabled), input:not(:disabled), textarea:not(:disabled), select:not(:disabled), a[href]",
      )];
      if (!focusable.length) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }
  }

  function handleRoute() {
    state.route = currentRoute();
    closeDialog(false);
    if (!state.token || !state.me) {
      renderLogin();
      return;
    }
    render();
    window.setTimeout(() => {
      document.getElementById("main-content")?.focus({ preventScroll: true });
      window.scrollTo({ top: 0, behavior: "instant" });
    }, 0);
  }

  async function boot() {
    applyTheme();
    installTranslations();
    await loadPhrases();
    applyLocale();
    document.addEventListener("click", (event) => {
      handleClick(event).catch((error) => toast(error.message, "error"));
    });
    document.addEventListener("submit", (event) => {
      handleSubmit(event).catch((error) => toast(error.message, "error"));
    });
    document.addEventListener("input", handleInput);
    document.addEventListener("change", handleChange);
    document.addEventListener("keydown", handleKeydown);
    window.addEventListener("hashchange", handleRoute);

    if (!state.token) {
      renderLogin();
      return;
    }
    try {
      state.me = await api("/auth/me", { keepSession: true });
      const route = currentRoute();
      state.route = route === "/" || route === "/login" ? landingRoute() : route;
      if (window.location.hash !== `#${state.route}`) {
        window.history.replaceState(
          null,
          "",
          `${window.location.pathname}${window.location.search}#${state.route}`,
        );
      }
      render();
    } catch {
      clearSession();
      state.loginError = "登录状态已失效，请重新登录。";
      renderLogin();
    }
  }

  boot();
})();
