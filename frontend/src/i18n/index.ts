import { readonly, ref, watch } from 'vue'

import phrases from './phrases.json'

export const SUPPORTED_LOCALES = [
  { code: 'zh-CN', label: '中文', intl: 'zh-CN', htmlLang: 'zh-CN' },
  { code: 'en', label: 'English', intl: 'en', htmlLang: 'en' },
  { code: 'vi', label: 'Tiếng Việt', intl: 'vi', htmlLang: 'vi' },
  { code: 'ms', label: 'Bahasa Melayu', intl: 'ms', htmlLang: 'ms' },
  { code: 'id', label: 'Bahasa Indonesia', intl: 'id', htmlLang: 'id' },
  { code: 'de', label: 'Deutsch', intl: 'de', htmlLang: 'de' },
  { code: 'fr', label: 'Français', intl: 'fr', htmlLang: 'fr' },
] as const

export type AppLocale = (typeof SUPPORTED_LOCALES)[number]['code']
export type AppTheme = 'light' | 'dark'

const LOCALE_STORAGE_KEY = 'medsales_locale'
const THEME_STORAGE_KEY = 'medsales_theme'
const LOCALE_INDEX: Record<Exclude<AppLocale, 'zh-CN'>, number> = {
  en: 0,
  vi: 1,
  ms: 2,
  id: 3,
  de: 4,
  fr: 5,
}
const ATTRIBUTES = ['placeholder', 'title', 'aria-label', 'alt'] as const
const translatedAttributes = new WeakMap<Element, Map<string, { source: string; target: string }>>()
const translatedText = new WeakMap<Text, { source: string; target: string }>()

function isAppLocale(value: string | null): value is AppLocale {
  return SUPPORTED_LOCALES.some((item) => item.code === value)
}

function initialLocale(): AppLocale {
  const stored = localStorage.getItem(LOCALE_STORAGE_KEY)
  if (isAppLocale(stored)) return stored
  // 中文是既有部署的默认语言；用户可在登录页或顶栏明确切换。
  return 'zh-CN'
}

function initialTheme(): AppTheme {
  const stored = localStorage.getItem(THEME_STORAGE_KEY)
  if (stored === 'light' || stored === 'dark') return stored
  return window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

export const appLocale = ref<AppLocale>(initialLocale())
export const appTheme = ref<AppTheme>(initialTheme())
let observer: MutationObserver | null = null
let applying = false

export function activeLocale(): AppLocale {
  return appLocale.value
}

export function intlLocale(): string {
  return SUPPORTED_LOCALES.find((item) => item.code === appLocale.value)?.intl ?? 'zh-CN'
}

export function localeLabel(code: AppLocale): string {
  return SUPPORTED_LOCALES.find((item) => item.code === code)?.label ?? code
}

function translateDynamic(source: string): string | null {
  const locale = appLocale.value
  if (locale === 'zh-CN') return null
  const index = LOCALE_INDEX[locale]
  const prefixRules: [RegExp, number][] = [
    [/^请选择(.+)$/, 1],
    [/^请输入(.+)$/, 1],
    [/^请填写(.+)$/, 1],
    [/^新增(.+)$/, 2],
    [/^编辑(.+)$/, 3],
    [/^分配权限 - (.+)$/, 4],
  ]
  for (const [pattern, kind] of prefixRules) {
    const match = source.match(pattern)
    if (!match) continue
    const leaf = lookupPhrase(match[1].trim(), index)
    if (!leaf) continue
    const templates = [
      ['Select {value}', 'Chọn {value}', 'Pilih {value}', 'Pilih {value}', '{value} auswählen', 'Sélectionner {value}'],
      ['Enter {value}', 'Nhập {value}', 'Masukkan {value}', 'Masukkan {value}', '{value} eingeben', 'Saisir {value}'],
      ['Enter {value}', 'Nhập {value}', 'Isi {value}', 'Isi {value}', '{value} ausfüllen', 'Renseigner {value}'],
      ['Add {value}', 'Thêm {value}', 'Tambah {value}', 'Tambah {value}', '{value} hinzufügen', 'Ajouter {value}'],
      ['Edit {value}', 'Sửa {value}', 'Edit {value}', 'Ubah {value}', '{value} bearbeiten', 'Modifier {value}'],
      ['Assign permissions - {value}', 'Phân quyền - {value}', 'Tetapkan kebenaran - {value}', 'Tetapkan izin - {value}', 'Berechtigungen zuweisen – {value}', 'Attribuer les autorisations – {value}'],
    ]
    return templates[kind][index].replace('{value}', leaf)
  }
  const networkPatterns: [RegExp, string[]][] = [
    [
      /^无法连接服务器 (.+)。请检查后端是否运行、地址是否可从设备访问。$/,
      [
        'Cannot connect to {server}. Check that the backend is running and reachable.',
        'Không thể kết nối với {server}. Kiểm tra máy chủ đã chạy và có thể truy cập.',
        'Tidak dapat menyambung ke {server}. Pastikan backend berjalan dan boleh diakses.',
        'Tidak dapat terhubung ke {server}. Pastikan backend berjalan dan dapat diakses.',
        '{server} ist nicht erreichbar. Prüfen Sie, ob das Backend läuft und erreichbar ist.',
        'Connexion impossible à {server}. Vérifiez que le serveur fonctionne et est accessible.',
      ],
    ],
    [
      /^请求失败（HTTP (.+)）$/,
      [
        'Request failed (HTTP {value})',
        'Yêu cầu thất bại (HTTP {value})',
        'Permintaan gagal (HTTP {value})',
        'Permintaan gagal (HTTP {value})',
        'Anfrage fehlgeschlagen (HTTP {value})',
        'Échec de la requête (HTTP {value})',
      ],
    ],
    [
      /^请求地址有误：(.+)$/,
      [
        'Invalid request address: {value}',
        'Địa chỉ yêu cầu không hợp lệ: {value}',
        'Alamat permintaan tidak sah: {value}',
        'Alamat permintaan tidak valid: {value}',
        'Ungültige Anfrageadresse: {value}',
        'Adresse de requête non valide : {value}',
      ],
    ],
    [
      /^请求失败：(.+)$/,
      [
        'Request failed: {value}',
        'Yêu cầu thất bại: {value}',
        'Permintaan gagal: {value}',
        'Permintaan gagal: {value}',
        'Anfrage fehlgeschlagen: {value}',
        'Échec de la requête : {value}',
      ],
    ],
  ]
  for (const [pattern, templates] of networkPatterns) {
    const match = source.match(pattern)
    if (match) return templates[index].replaceAll('{value}', match[1]).replace('{server}', match[1])
  }
  return null
}

function lookupPhrase(source: string, index: number): string | null {
  const entry = (phrases as Record<string, string[] | string>)[source]
  return Array.isArray(entry) ? entry[index] ?? null : null
}

export function translateText(source: string): string {
  if (appLocale.value === 'zh-CN' || !/[\u3400-\u9fff]/.test(source)) return source
  const leading = source.match(/^\s*/)?.[0] ?? ''
  const trailing = source.match(/\s*$/)?.[0] ?? ''
  const core = source.slice(leading.length, source.length - trailing.length)
  if (!core) return source
  const exact = lookupPhrase(core, LOCALE_INDEX[appLocale.value])
  if (exact) return `${leading}${exact}${trailing}`

  const dynamic = translateDynamic(core)
  if (dynamic) return `${leading}${dynamic}${trailing}`

  for (const [prefix, index] of [
    ['角色：', 1],
    ['邮箱：', 2],
    ['电话：', 3],
  ] as const) {
    if (!core.startsWith(prefix)) continue
    const translatedPrefix = lookupPhrase(prefix, LOCALE_INDEX[appLocale.value])
    if (translatedPrefix) return `${leading}${translatedPrefix}${core.slice(prefix.length)}${trailing}`
  }
  return source
}

function applyTextNode(node: Text) {
  const previous = translatedText.get(node)
  const source = previous && node.data === previous.target ? previous.source : node.data
  const target = translateText(source)
  if (target !== source) translatedText.set(node, { source, target })
  if (node.data !== target) node.data = target
}

function applyElement(node: Element) {
  for (const attribute of ATTRIBUTES) {
    if (!node.hasAttribute(attribute)) continue
    const current = node.getAttribute(attribute) ?? ''
    let sourceMap = translatedAttributes.get(node)
    if (!sourceMap) {
      sourceMap = new Map()
      translatedAttributes.set(node, sourceMap)
    }
    const previous = sourceMap.get(attribute)
    const source = previous && current === previous.target ? previous.source : current
    const target = translateText(source)
    if (target !== source) sourceMap.set(attribute, { source, target })
    if (current !== target) node.setAttribute(attribute, target)
  }
}

function applyTree(root: Node) {
  if (root.nodeType === Node.TEXT_NODE) {
    applyTextNode(root as Text)
    return
  }
  if (!(root instanceof Element) && root.nodeType !== Node.DOCUMENT_NODE) return
  if (root instanceof Element) applyElement(root)
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_ELEMENT | NodeFilter.SHOW_TEXT)
  let node = walker.nextNode()
  while (node) {
    if (node.nodeType === Node.TEXT_NODE) applyTextNode(node as Text)
    else applyElement(node as Element)
    node = walker.nextNode()
  }
}

function applyEnvironment() {
  if (applying) return
  applying = true
  try {
    const locale = SUPPORTED_LOCALES.find((item) => item.code === appLocale.value)
    document.documentElement.lang = locale?.htmlLang ?? 'zh-CN'
    document.documentElement.dataset.locale = appLocale.value
    document.documentElement.classList.toggle('dark', appTheme.value === 'dark')
    document.documentElement.dataset.theme = appTheme.value
    document.documentElement.style.colorScheme = appTheme.value
    const meta = document.querySelector<HTMLMetaElement>('meta[name="theme-color"]')
    if (meta) meta.content = appTheme.value === 'dark' ? '#07151c' : '#1f6feb'
    applyTree(document.body)
  } finally {
    applying = false
  }
}

export function setLocale(locale: AppLocale) {
  appLocale.value = locale
  localStorage.setItem(LOCALE_STORAGE_KEY, locale)
}

export function setTheme(theme: AppTheme) {
  appTheme.value = theme
  localStorage.setItem(THEME_STORAGE_KEY, theme)
}

export function toggleTheme() {
  setTheme(appTheme.value === 'dark' ? 'light' : 'dark')
}

export function installI18n() {
  applyEnvironment()
  watch([appLocale, appTheme], applyEnvironment, { flush: 'post' })
  observer?.disconnect()
  observer = new MutationObserver((mutations) => {
    if (applying) return
    applying = true
    try {
      for (const mutation of mutations) {
        if (mutation.type === 'characterData') {
          applyTextNode(mutation.target as Text)
          continue
        }
        if (mutation.type === 'attributes' && mutation.target instanceof Element) {
          applyElement(mutation.target)
          continue
        }
        for (const node of mutation.addedNodes) applyTree(node)
      }
    } finally {
      applying = false
    }
  })
  observer.observe(document.body, {
    subtree: true,
    childList: true,
    characterData: true,
    attributes: true,
    attributeFilter: [...ATTRIBUTES],
  })
}

export function useAppPreferences() {
  return {
    locale: readonly(appLocale),
    theme: readonly(appTheme),
    localeLabel,
    setLocale,
    setTheme,
    toggleTheme,
  }
}

