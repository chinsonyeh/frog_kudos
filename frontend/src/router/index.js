import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

import QuickEntryView from '@/views/QuickEntryView.vue'
import LedgerView from '@/views/LedgerView.vue'
import RewardsView from '@/views/RewardsView.vue'
import RulesView from '@/views/RulesView.vue'

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
    meta: { requiresParent: true },
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
  },
  {
    path: '/rules',
    name: 'Rules',
    component: RulesView,
    meta: { requiresParent: true },
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

// 路由防護守衛 (FR-13)
router.beforeEach((to, from, next) => {
  const authStore = useAuthStore()
  if (to.meta.requiresParent && !authStore.isParent) {
    next('/ledger')
  } else {
    next()
  }
})

export default router
