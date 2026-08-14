<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api, ApiError } from '@/lib/api'
import type { User, UserRole } from '@/lib/types'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Card from '@/components/ui/Card.vue'
import Dialog from '@/components/ui/Dialog.vue'
import Input from '@/components/ui/Input.vue'
import Table from '@/components/ui/Table.vue'

const users = ref<User[]>([])
const loading = ref(true)

const inviteOpen = ref(false)
const email = ref('')
const role = ref<UserRole>('viewer')
const inviting = ref(false)
const inviteError = ref('')

async function load() {
  loading.value = true
  users.value = await api.users.list()
  loading.value = false
}

async function invite() {
  if (!email.value.trim()) return
  inviting.value = true
  inviteError.value = ''
  try {
    await api.users.invite(email.value.trim(), role.value)
    email.value = ''
    role.value = 'viewer'
    inviteOpen.value = false
    await load()
  } catch (e) {
    inviteError.value = e instanceof ApiError ? e.message : 'Could not invite user.'
  } finally {
    inviting.value = false
  }
}

onMounted(load)
</script>

<template>
  <div>
    <div class="mb-6 flex items-center justify-between">
      <h1 class="text-xl font-semibold">Users</h1>
      <Button @click="inviteOpen = true">Invite user</Button>
    </div>

    <Card v-if="loading" class="p-6 text-sm text-muted-foreground">Loading…</Card>
    <Table v-else>
      <thead class="border-b border-border bg-surface-muted text-xs uppercase text-muted-foreground">
        <tr>
          <th class="px-4 py-2 font-medium">Email</th>
          <th class="px-4 py-2 font-medium">Role</th>
          <th class="px-4 py-2 font-medium">Joined</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="u in users" :key="u.id" class="border-b border-border last:border-0">
          <td class="px-4 py-2">{{ u.email }}</td>
          <td class="px-4 py-2"><Badge tone="accent">{{ u.role }}</Badge></td>
          <td class="px-4 py-2 text-muted-foreground">{{ new Date(u.created_at).toLocaleDateString() }}</td>
        </tr>
      </tbody>
    </Table>

    <Dialog v-model:open="inviteOpen">
      <template #default="{ close }">
        <h2 class="text-base font-semibold">Invite user</h2>
        <Input v-model="email" placeholder="email@example.com" class="mt-4" />
        <select v-model="role" class="mt-3 h-9 w-full rounded-md border border-border bg-surface px-3 text-sm">
          <option value="viewer">Viewer</option>
          <option value="operator">Operator</option>
          <option value="admin">Admin</option>
        </select>
        <p v-if="inviteError" class="mt-2 text-sm text-danger">{{ inviteError }}</p>
        <div class="mt-4 flex justify-end gap-2">
          <Button variant="secondary" @click="close">Cancel</Button>
          <Button :disabled="inviting" @click="invite">{{ inviting ? 'Inviting…' : 'Invite' }}</Button>
        </div>
      </template>
    </Dialog>
  </div>
</template>
