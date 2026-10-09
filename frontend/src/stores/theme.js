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
    tag: '現代扁平',
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

export const useThemeStore = defineStore('theme', () => {
  const currentTheme = ref('emerald')
  const currentLogoId = ref('1')

  const currentLogo = computed(() => {
    return LOGO_ICONS.find((i) => i.id === currentLogoId.value) || LOGO_ICONS[0]
  })

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
    const activeId = validIcon ? validIcon.id : '1'
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
    let savedLogo = '1'
    try {
      savedTheme = localStorage.getItem(STORAGE_KEY) || 'emerald'
      savedLogo = localStorage.getItem(STORAGE_ICON_KEY) || '1'
    } catch {
      savedTheme = 'emerald'
      savedLogo = '1'
    }
    applyTheme(savedTheme)
    applyLogoIcon(savedLogo)
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
  }
})
