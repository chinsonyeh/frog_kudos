import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const THEMES = [
  {
    id: 'emerald',
    name: '經典翡翠',
    emoji: '🐸',
    tag: '招牌推薦',
    description: '生機盎然的原生經典青蛙配色，清新自然、活力充沛',
    primaryHex: '#10B981',
    palette: ['#ecfdf5', '#10b981', '#047857'],
  },
  {
    id: 'ocean',
    name: '海洋微風',
    emoji: '🐬',
    tag: '沉著專注',
    description: '湛藍天空與蔚藍深海的靜謐配色，沉著冷靜、適合學習',
    primaryHex: '#0EA5E9',
    palette: ['#f0f9ff', '#0ea5e9', '#0369a1'],
  },
  {
    id: 'sakura',
    name: '粉櫻甜莓',
    emoji: '🌸',
    tag: '甜美童趣',
    description: '草莓軟糖與浪漫粉櫻的粉嫩配色，溫柔甜美、女孩最愛',
    primaryHex: '#F43F5E',
    palette: ['#fff1f2', '#f43f5e', '#be123c'],
  },
  {
    id: 'amber',
    name: '暖陽金橙',
    emoji: '🌅',
    tag: '朝氣蓬勃',
    description: '日出晨光與蜜柑金橙的溫暖配色，朝氣昂揚、積極向上',
    primaryHex: '#F59E0B',
    palette: ['#fffbeb', '#f59e0b', '#b45309'],
  },
  {
    id: 'violet',
    name: '星夜薰衣',
    emoji: '🌌',
    tag: '奇幻優雅',
    description: '夢幻星雲與薰衣草丁香的魔法配色，高雅放鬆、充滿想像',
    primaryHex: '#8B5CF6',
    palette: ['#f5f3ff', '#8b5cf6', '#6d28d9'],
  },
  {
    id: 'mint',
    name: '薄荷青檸',
    emoji: '🍃',
    tag: '清爽舒緩',
    description: '微風青檸與冰晶薄荷的輕快配色，涼爽無負擔、舒緩用眼',
    primaryHex: '#14B8A6',
    palette: ['#f0fdfa', '#14b8a6', '#0f766e'],
  },
  {
    id: 'gold',
    name: '榮耀王者',
    emoji: '👑',
    tag: '王者成就',
    description: '璀璨金冠與香檳琥珀的尊爵配色，象徵點數皇冠與最高榮耀',
    primaryHex: '#EAB308',
    palette: ['#fefce8', '#eab308', '#a16207'],
  },
  {
    id: 'crimson',
    name: '熱血赤焰',
    emoji: '🔥',
    tag: '熱血破關',
    description: '熱情如火的緋紅珊瑚烈焰配色，適合體育挑戰與過關闖將',
    primaryHex: '#EF4444',
    palette: ['#fef2f2', '#ef4444', '#b91c1c'],
  },
  {
    id: 'latte',
    name: '暖心奶茶',
    emoji: '🧸',
    tag: '溫馨日系',
    description: '焦糖奶茶與溫暖燕麥大地色系，營造溫馨療癒的家庭時光',
    primaryHex: '#D97732',
    palette: ['#fff8f0', '#d97732', '#9a491c'],
  },
  {
    id: 'aurora',
    name: '極光霓虹',
    emoji: '⚡',
    tag: '現代極客',
    description: '電光紫藍與極光深空的酷炫配色，帥氣現代、充滿未來科技感',
    primaryHex: '#6366F1',
    palette: ['#eef2ff', '#6366f1', '#4338ca'],
  },
]

export const LOGO_ICONS = [
  {
    id: '1',
    name: '經典萌眼蛙',
    subtitle: 'Classic 3D',
    tag: '招牌推薦',
    description: '圓潤大眼、親切溫暖的元祖招牌 3D 黏土青蛙',
    src: '/icons/gallery/icon_1_classic.jpg',
    emoji: '🐸',
  },
  {
    id: '2',
    name: '榮譽金冠蛙',
    subtitle: 'Crown Kudos',
    tag: '榮譽王者',
    description: '頭戴精緻閃耀金冠，象徵累積積分與榮譽桂冠',
    src: '/icons/gallery/icon_2_crown.jpg',
    emoji: '👑',
  },
  {
    id: '3',
    name: '幸運嫩芽蛙',
    subtitle: 'Lucky Sprout',
    tag: '成長茁壯',
    description: '頭頂四葉草與陽光綠芽，象徵好習慣每日成長',
    src: '/icons/gallery/icon_3_sprout.jpg',
    emoji: '🌱',
  },
  {
    id: '4',
    name: '幾何極簡蛙',
    subtitle: 'Modern Vector',
    tag: '預設推薦',
    description: 'Apple 極簡風格俐落向量線條，乾淨純粹',
    src: '/icons/gallery/icon_4_vector.jpg',
    emoji: '🍏',
  },
  {
    id: '5',
    name: '智慧博士蛙',
    subtitle: 'Scholar Frog',
    tag: '認真學習',
    description: '戴學士帽與小圓眼鏡，象徵用功學習與金榜題名',
    src: '/icons/gallery/icon_5_scholar.jpg',
    emoji: '🎓',
  },
  {
    id: '6',
    name: '超人英雄蛙',
    subtitle: 'Superhero Frog',
    tag: '勇敢自信',
    description: '手叉腰繫紅披風與星章，象徵自信勇敢、樂於助人',
    src: '/icons/gallery/icon_6_superhero.jpg',
    emoji: '🦸',
  },
  {
    id: '7',
    name: '奇幻魔法蛙',
    subtitle: 'Magic Wizard',
    tag: '夢想奇幻',
    description: '戴星空巫師帽揮舞仙女星杖，充滿夢想與驚喜',
    src: '/icons/gallery/icon_7_wizard.jpg',
    emoji: '🪄',
  },
  {
    id: '8',
    name: '太空探險蛙',
    subtitle: 'Astronaut Frog',
    tag: '勇於探索',
    description: '身穿太空裝漫遊星雲，象徵勇於探索新知識',
    src: '/icons/gallery/icon_8_astronaut.jpg',
    emoji: '🚀',
  },
  {
    id: '9',
    name: '派對歡慶蛙',
    subtitle: 'Party Celebration',
    tag: '歡慶達標',
    description: '繽紛派對帽與飄落彩紙，歡慶每一次達標',
    src: '/icons/gallery/icon_9_party.jpg',
    emoji: '🎉',
  },
  {
    id: '10',
    name: '酷炫墨鏡蛙',
    subtitle: 'Cool Shades',
    tag: '陽光活力',
    description: '頭頂酷炫小墨鏡眨眼比讚，散發夏日活力與自信',
    src: '/icons/gallery/icon_10_cool.jpg',
    emoji: '🕶️',
  },
]

const STORAGE_KEY = 'frog_kudos_theme'
const STORAGE_ICON_KEY = 'frog_kudos_logo_icon'
const STORAGE_TOP_INSET_KEY = 'frog_kudos_top_inset'

const TOP_INSET_PRESETS = {
  auto: 0,
  notch: 48,
  island: 60,
}
const HEURISTIC_FALLBACK_PX = 59

let safeAreaListenersBound = false

function clampTopInsetPx(val) {
  const n = Math.round(Number(val))
  if (!Number.isFinite(n)) return 0
  return Math.max(0, Math.min(120, n))
}

function parseStoredTopInset(raw) {
  if (raw === 'notch') return { mode: 'notch', customPx: 59 }
  if (raw === 'island') return { mode: 'island', customPx: 59 }
  if (typeof raw === 'string' && raw.startsWith('custom:')) {
    const n = parseInt(raw.slice(7), 10)
    if (!Number.isNaN(n) && n >= 0 && n <= 120) {
      return { mode: 'custom', customPx: n }
    }
  }
  return { mode: 'auto', customPx: 59 }
}

function measureSystemSafeTop() {
  if (typeof window === 'undefined' || typeof document === 'undefined' || !document.body) {
    return 0
  }
  let probe = document.getElementById('frog-safe-area-probe')
  if (!probe) {
    probe = document.createElement('div')
    probe.id = 'frog-safe-area-probe'
    probe.setAttribute('aria-hidden', 'true')
    probe.style.cssText =
      'position:fixed;top:0;left:0;width:0;height:0;padding-top:env(safe-area-inset-top, 0px);visibility:hidden;pointer-events:none;'
    document.body.appendChild(probe)
  }
  const px = parseFloat(window.getComputedStyle(probe).paddingTop)
  return Number.isFinite(px) ? Math.max(0, Math.round(px)) : 0
}

function detectFullscreenIphoneHeuristic(measuredTop) {
  if (typeof window === 'undefined' || typeof navigator === 'undefined') return 0
  const isIphone = /iPhone/i.test(navigator.userAgent || '')
  if (!isIphone || measuredTop > 0) return 0

  const isPortrait = window.innerHeight > window.innerWidth
  if (!isPortrait) return 0

  const sw = window.screen?.width || 0
  const sh = window.screen?.height || 0
  const screenMax = Math.max(sw, sh)
  const screenMin = Math.min(sw, sh)
  if (screenMin <= 0 || screenMax <= 0) return 0

  const isFullHeight = window.innerHeight >= screenMax - 20
  const aspectRatio = screenMax / screenMin
  if (isFullHeight && aspectRatio >= 2.0) {
    return HEURISTIC_FALLBACK_PX
  }
  return 0
}

export const useThemeStore = defineStore('theme', () => {
  const currentTheme = ref('emerald')
  const currentLogoId = ref('4')

  // 裝置頂部安全距離 / 動態島避讓狀態 (本機裝置獨立設定)
  const topInsetMode = ref('auto') // 'auto' | 'notch' | 'island' | 'custom'
  const customTopInset = ref(59)
  const detectedSafeAreaTop = ref(0)
  const isLandscape = ref(false)
  const heuristicActive = ref(false)
  const topInsetUrlSource = ref(null) // 'custom' | 'auto' | null

  const currentLogo = computed(() => {
    return LOGO_ICONS.find((i) => i.id === currentLogoId.value) || LOGO_ICONS.find((i) => i.id === '4') || LOGO_ICONS[0]
  })

  const configuredOverridePx = computed(() => {
    if (topInsetMode.value === 'notch') return TOP_INSET_PRESETS.notch
    if (topInsetMode.value === 'island') return TOP_INSET_PRESETS.island
    if (topInsetMode.value === 'custom') return clampTopInsetPx(customTopInset.value)
    return heuristicActive.value ? HEURISTIC_FALLBACK_PX : 0
  })

  const effectiveSafeTopPx = computed(() => {
    if (isLandscape.value) return detectedSafeAreaTop.value
    return Math.max(detectedSafeAreaTop.value, configuredOverridePx.value)
  })

  const topInsetSourceLabel = computed(() => {
    if (isLandscape.value) {
      return `橫向模式（沿用系統安全區 ${detectedSafeAreaTop.value}px）`
    }
    if (topInsetMode.value === 'custom') {
      if (topInsetUrlSource.value === 'custom') {
        return `由啟動網址參數套用 (?top_inset=${clampTopInsetPx(customTopInset.value)})`
      }
      return `自訂頂部安全距離 (${clampTopInsetPx(customTopInset.value)}px)`
    }
    if (topInsetMode.value === 'island') {
      return '預設：iPhone 動態島 (60px)'
    }
    if (topInsetMode.value === 'notch') {
      return '預設：iPhone 瀏海 (48px)'
    }
    if (heuristicActive.value) {
      return `滿版啟發式備援 (${HEURISTIC_FALLBACK_PX}px，僅暫態不寫入儲存)`
    }
    if (topInsetUrlSource.value === 'auto') {
      return '已透過網址參數重置為系統自動偵測'
    }
    return detectedSafeAreaTop.value > 0
      ? `系統自動偵測 env() (${detectedSafeAreaTop.value}px)`
      : '系統自動偵測 (一般視窗無須額外留白)'
  })

  function syncTopInsetCssVar() {
    if (typeof document === 'undefined') return
    const px = clampTopInsetPx(configuredOverridePx.value)
    // 一律帶 px 單位，歸零必為 '0px'，防止 WebKit max() 解析失效
    document.documentElement.style.setProperty('--top-inset-override', `${px}px`)
  }

  function refreshSafeAreaMetrics() {
    if (typeof window === 'undefined') return
    isLandscape.value = window.innerWidth > window.innerHeight
    const measured = measureSystemSafeTop()
    detectedSafeAreaTop.value = measured
    heuristicActive.value = topInsetMode.value === 'auto' && detectFullscreenIphoneHeuristic(measured) > 0
    syncTopInsetCssVar()
  }

  function persistTopInsetSetting() {
    let serialized = 'auto'
    if (topInsetMode.value === 'notch') {
      serialized = 'notch'
    } else if (topInsetMode.value === 'island') {
      serialized = 'island'
    } else if (topInsetMode.value === 'custom') {
      serialized = `custom:${clampTopInsetPx(customTopInset.value)}`
    }
    try {
      localStorage.setItem(STORAGE_TOP_INSET_KEY, serialized)
    } catch {
      // 容錯處理
    }
  }

  function setTopInsetMode(mode) {
    const valid = ['auto', 'notch', 'island', 'custom'].includes(mode) ? mode : 'auto'
    topInsetMode.value = valid
    topInsetUrlSource.value = null
    persistTopInsetSetting()
    refreshSafeAreaMetrics()
  }

  function setCustomTopInset(px) {
    customTopInset.value = clampTopInsetPx(px)
    topInsetMode.value = 'custom'
    topInsetUrlSource.value = null
    persistTopInsetSetting()
    refreshSafeAreaMetrics()
  }

  function bindSafeAreaListeners() {
    if (typeof window === 'undefined' || safeAreaListenersBound) return
    safeAreaListenersBound = true
    const scheduleRefresh = () => {
      window.requestAnimationFrame(() => {
        refreshSafeAreaMetrics()
      })
    }
    window.addEventListener('resize', scheduleRefresh, { passive: true })
    window.addEventListener('orientationchange', () => {
      window.requestAnimationFrame(() => {
        window.requestAnimationFrame(refreshSafeAreaMetrics)
      })
    })
  }

  function updateFavicon(src) {
    if (typeof document === 'undefined') return
    let link = document.querySelector("link[rel*='icon']")
    if (!link) {
      link = document.createElement('link')
      link.rel = 'shortcut icon'
      document.getElementsByTagName('head')[0].appendChild(link)
    }
    link.type = 'image/jpeg'
    link.href = src
  }

  function applyLogoIcon(iconId) {
    const validIcon = LOGO_ICONS.find((i) => i.id === iconId)
    const activeId = validIcon ? validIcon.id : '4'
    currentLogoId.value = activeId

    try {
      localStorage.setItem(STORAGE_ICON_KEY, activeId)
    } catch {
      // 容錯處理
    }

    if (validIcon) {
      updateFavicon(validIcon.src)
    }
  }

  function setLogoIcon(iconId) {
    applyLogoIcon(iconId)
  }

  function applyTheme(themeId) {
    const validTheme = THEMES.find((t) => t.id === themeId)
    const activeId = validTheme ? validTheme.id : 'emerald'
    currentTheme.value = activeId

    // 1. 套用至 DOM
    if (typeof document !== 'undefined') {
      document.documentElement.setAttribute('data-theme', activeId)

      // 2. 更新行動端頂部導航 theme-color
      const metaThemeColor = document.querySelector('meta[name="theme-color"]')
      if (metaThemeColor && validTheme) {
        metaThemeColor.setAttribute('content', validTheme.primaryHex)
      }
    }

    // 3. 獨立儲存至當前瀏覽器 localStorage
    try {
      localStorage.setItem(STORAGE_KEY, activeId)
    } catch {
      // 容錯處理 (無痕模式或限制時)
    }
  }

  function setTheme(themeId) {
    applyTheme(themeId)
  }

  function initTheme() {
    let savedTheme = 'emerald'
    let savedLogo = '4'
    let savedTopInset = 'auto'
    try {
      savedTheme = localStorage.getItem(STORAGE_KEY) || 'emerald'
      savedLogo = localStorage.getItem(STORAGE_ICON_KEY) || '4'
      savedTopInset = localStorage.getItem(STORAGE_TOP_INSET_KEY) || 'auto'
    } catch {
      savedTheme = 'emerald'
      savedLogo = '4'
      savedTopInset = 'auto'
    }
    applyTheme(savedTheme)
    applyLogoIcon(savedLogo)

    // 同步由 index.html preloader 解析完成的本機安全區設定（相容受限環境無法寫入 localStorage 之情境）
    const preloadedValue =
      typeof window !== 'undefined' && typeof window.__FROG_KUDOS_TOP_INSET_VALUE__ === 'string'
        ? window.__FROG_KUDOS_TOP_INSET_VALUE__
        : null
    const effectiveStoredTopInset =
      (typeof window !== 'undefined' && window.__FROG_KUDOS_TOP_INSET_FROM_URL__ && preloadedValue) ||
      savedTopInset ||
      preloadedValue ||
      'auto'
    const parsed = parseStoredTopInset(effectiveStoredTopInset)
    topInsetMode.value = parsed.mode
    customTopInset.value = parsed.customPx
    if (typeof window !== 'undefined') {
      topInsetUrlSource.value = window.__FROG_KUDOS_TOP_INSET_FROM_URL__ || null
      isLandscape.value = window.innerWidth > window.innerHeight
    }
    syncTopInsetCssVar()

    // 等待首幀版面完成後再以隱藏探針量測 env(safe-area-inset-top)，避免 WKWebView 冷啟動誤判
    if (typeof window !== 'undefined') {
      bindSafeAreaListeners()
      window.requestAnimationFrame(() => {
        window.requestAnimationFrame(() => {
          refreshSafeAreaMetrics()
        })
      })
    }
  }

  return {
    themes: THEMES,
    currentTheme,
    setTheme,
    initTheme,
    logoIcons: LOGO_ICONS,
    currentLogoId,
    currentLogo,
    setLogoIcon,
    topInsetMode,
    customTopInset,
    detectedSafeAreaTop,
    isLandscape,
    heuristicActive,
    topInsetUrlSource,
    effectiveSafeTopPx,
    topInsetSourceLabel,
    setTopInsetMode,
    setCustomTopInset,
    refreshSafeAreaMetrics,
  }
})
