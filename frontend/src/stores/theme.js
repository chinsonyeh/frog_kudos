import { defineStore } from 'pinia'
import { ref } from 'vue'

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

const STORAGE_KEY = 'frog_kudos_theme'

export const useThemeStore = defineStore('theme', () => {
  const currentTheme = ref('emerald')

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
    let saved = 'emerald'
    try {
      saved = localStorage.getItem(STORAGE_KEY) || 'emerald'
    } catch {
      saved = 'emerald'
    }
    applyTheme(saved)
  }

  return {
    themes: THEMES,
    currentTheme,
    setTheme,
    initTheme,
  }
})
