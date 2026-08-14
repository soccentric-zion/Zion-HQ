import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api, ApiError } from '@/lib/api'
import type { User } from '@/lib/types'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const status = ref<'unknown' | 'authenticated' | 'unauthenticated'>('unknown')

  async function fetchMe(): Promise<void> {
    try {
      user.value = await api.auth.me()
      status.value = 'authenticated'
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) {
        user.value = null
        status.value = 'unauthenticated'
      } else {
        throw e
      }
    }
  }

  async function login(): Promise<void> {
    const { authorization_url } = await api.auth.loginUrl()
    window.location.href = authorization_url
  }

  async function logout(): Promise<void> {
    await api.auth.logout()
    user.value = null
    status.value = 'unauthenticated'
  }

  function hasRole(minimum: 'viewer' | 'operator' | 'admin'): boolean {
    const rank = { viewer: 0, operator: 1, admin: 2 }
    if (!user.value) return false
    return rank[user.value.role] >= rank[minimum]
  }

  return { user, status, fetchMe, login, logout, hasRole }
})
