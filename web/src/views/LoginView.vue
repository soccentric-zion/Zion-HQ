<script setup lang="ts">
import { ref } from 'vue'
import { useAuthStore } from '@/stores/auth'
import Button from '@/components/ui/Button.vue'
import Card from '@/components/ui/Card.vue'

const auth = useAuthStore()
const loading = ref(false)
const error = ref('')

async function handleLogin() {
  loading.value = true
  error.value = ''
  try {
    await auth.login()
  } catch {
    error.value = 'Could not reach the identity provider. Try again shortly.'
    loading.value = false
  }
}
</script>

<template>
  <div class="flex min-h-screen items-center justify-center bg-surface-muted px-4">
    <Card class="w-full max-w-sm p-8">
      <h1 class="text-lg font-semibold">Zion-HQ</h1>
      <p class="mt-1 text-sm text-muted-foreground">Sign in to manage your device fleet.</p>
      <Button class="mt-6 w-full" :disabled="loading" @click="handleLogin">
        {{ loading ? 'Redirecting…' : 'Sign in with SSO' }}
      </Button>
      <p v-if="error" class="mt-3 text-sm text-danger">{{ error }}</p>
    </Card>
  </div>
</template>
