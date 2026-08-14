import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it } from 'vitest'
import { useAuthStore } from '../auth'

describe('useAuthStore.hasRole', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('returns false when no user is loaded', () => {
    const auth = useAuthStore()
    expect(auth.hasRole('viewer')).toBe(false)
  })

  it('ranks admin above operator above viewer', () => {
    const auth = useAuthStore()
    auth.user = { id: '1', email: 'a@example.com', role: 'operator', created_at: '' }
    expect(auth.hasRole('viewer')).toBe(true)
    expect(auth.hasRole('operator')).toBe(true)
    expect(auth.hasRole('admin')).toBe(false)
  })

  it('viewer cannot satisfy an operator requirement', () => {
    const auth = useAuthStore()
    auth.user = { id: '1', email: 'v@example.com', role: 'viewer', created_at: '' }
    expect(auth.hasRole('operator')).toBe(false)
  })
})
