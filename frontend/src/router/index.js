import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

import QuickEntryView from '@/views/QuickEntryView.vue'
import LedgerView from '@/views/LedgerView.vue'
import RewardsView from '@/views/RewardsView.vue'
import RulesView from '@/views/RulesView.vue'
import GuideView from '@/views/GuideView.vue'

const routes = [
  {
    path: '/',
    redirect: () => {
      const auth = useAuthStore()
      return auth.isParent ? '/record' : '/ledger'
    },
  },
  {
    path: '/record',
    name: 'Record',
    component: QuickEntryView,
    meta: { requiresUnlock: true },
  },
  {
    path: '/ledger',
    name: 'Ledger',
    component: LedgerView,
  },
  {
    path: '/rewards',
    name: 'Rewards',
    component: RewardsView,
    meta: { requiresUnlock: true },
  },
  {
    path: '/rules',
    name: 'Rules',
    component: RulesView,
    meta: { requiresParent: true },
  },
  {
    path: '/guide',
    name: 'Guide',
    component: GuideView,
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/ledger',
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// 路由防護守衛 (訪客模式僅允許看榮譽存摺 /ledger，登記與商城需解鎖後方可進入)
router.beforeEach((to, from, next) => {
  const authStore = useAuthStore()
  if (to.meta.requiresParent && !authStore.isParent) {
    next('/ledger')
  } else if (to.meta.requiresUnlock && !authStore.isUnlocked) {
    next('/ledger')
  } else {
    next()
  }
})

export default router
