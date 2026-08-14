<script setup lang="ts">
import { RouterLink, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import Button from '@/components/ui/Button.vue'

const auth = useAuthStore()
const router = useRouter()

async function handleLogout() {
  await auth.logout()
  router.push({ name: 'login' })
}
</script>

<template>
  <div class="min-h-screen">
    <header class="border-b border-border bg-surface">
      <div class="mx-auto flex max-w-6xl items-center justify-between px-6 py-3">
        <div class="flex items-center gap-6">
          <span class="text-sm font-semibold tracking-tight">Zion-HQ</span>
          <nav class="flex gap-4 text-sm text-muted-foreground">
            <RouterLink to="/" class="hover:text-foreground" active-class="text-foreground font-medium"
              >Devices</RouterLink
            >
            <RouterLink to="/alarm-rules" class="hover:text-foreground" active-class="text-foreground font-medium"
              >Alarm Rules</RouterLink
            >
            <RouterLink
              v-if="auth.hasRole('admin')"
              to="/users"
              class="hover:text-foreground"
              active-class="text-foreground font-medium"
              >Users</RouterLink
            >
            <RouterLink
              v-if="auth.hasRole('admin')"
              to="/audit-log"
              class="hover:text-foreground"
              active-class="text-foreground font-medium"
              >Audit Log</RouterLink
            >
          </nav>
        </div>
        <div class="flex items-center gap-3">
          <span class="text-sm text-muted-foreground">{{ auth.user?.email }}</span>
          <Button variant="ghost" size="sm" @click="handleLogout">Log out</Button>
        </div>
      </div>
    </header>
    <main class="mx-auto max-w-6xl px-6 py-8">
      <slot />
    </main>
  </div>
</template>
