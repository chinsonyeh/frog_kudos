import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import { useThemeStore } from './stores/theme'
import './style.css'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)

// 初始化當前瀏覽器專屬之佈景主題 (從 localStorage 讀取)
const themeStore = useThemeStore()
themeStore.initTheme()

app.mount('#app')
