<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '@/lib/api'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const error = ref('')

onMounted(async () => {
  const code = route.query.code as string | undefined
  const state = route.query.state as string | undefined
  if (!code || !state) {
    error.value = 'Missing authorization code from identity provider.'
    return
  }
  try {
    await api.auth.callback(code, state)
    await auth.fetchMe()
    router.replace((route.query.redirect as string) || '/')
  } catch {
    error.value = 'Sign-in failed. Please try again.'
  }
})
</script>

<template>
  <div class="flex min-h-screen items-center justify-center px-4 text-center">
    <div v-if="error" class="text-sm text-danger">{{ error }}</div>
    <div v-else class="text-sm text-muted-foreground">Signing you in…</div>
  </div>
</template>
