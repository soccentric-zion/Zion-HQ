import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/LoginView.vue'),
      meta: { public: true },
    },
    {
      path: '/auth/callback',
      name: 'auth-callback',
      component: () => import('@/views/AuthCallbackView.vue'),
      meta: { public: true },
    },
    { path: '/', name: 'devices', component: () => import('@/views/DeviceListView.vue') },
    {
      path: '/devices/:id',
      name: 'device-detail',
      component: () => import('@/views/DeviceDetailView.vue'),
      props: true,
    },
    {
      path: '/alarm-rules',
      name: 'alarm-rules',
      component: () => import('@/views/AlarmRulesView.vue'),
      meta: { requiresRole: 'viewer' },
    },
    {
      path: '/users',
      name: 'users',
      component: () => import('@/views/UsersView.vue'),
      meta: { requiresRole: 'admin' },
    },
    {
      path: '/audit-log',
      name: 'audit-log',
      component: () => import('@/views/AuditLogView.vue'),
      meta: { requiresRole: 'admin' },
    },
  ],
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  if (auth.status === 'unknown') {
    try {
      await auth.fetchMe()
    } catch {
      // Transient network/API failure -- treat as unauthenticated rather
      // than throwing out of the guard, which would otherwise wedge the
      // router (VUE_ROUTER_R0011) for the rest of the session.
      auth.status = 'unauthenticated'
    }
  }

  if (to.meta.public) {
    return true
  }
  if (auth.status !== 'authenticated') {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  const requiresRole = to.meta.requiresRole as 'viewer' | 'operator' | 'admin' | undefined
  if (requiresRole && !auth.hasRole(requiresRole)) {
    return { name: 'devices' }
  }
  return true
})

export default router
