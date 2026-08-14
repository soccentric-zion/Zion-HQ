<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { api, ApiError } from '@/lib/api'
import { connectDeviceStatusSocket } from '@/lib/deviceStatusSocket'
import type { Device } from '@/lib/types'
import { useAuthStore } from '@/stores/auth'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Card from '@/components/ui/Card.vue'
import Dialog from '@/components/ui/Dialog.vue'
import Input from '@/components/ui/Input.vue'
import Table from '@/components/ui/Table.vue'

const auth = useAuthStore()
const devices = ref<Device[]>([])
const q = ref('')
const loading = ref(true)
const error = ref('')

const addOpen = ref(false)
const newName = ref('')
const creating = ref(false)
const createError = ref('')
const pairingToken = ref<string | null>(null)

async function load() {
  loading.value = true
  error.value = ''
  try {
    const res = await api.devices.list({ q: q.value || undefined })
    devices.value = res.items
  } catch {
    error.value = 'Could not load devices.'
  } finally {
    loading.value = false
  }
}

async function handleCreate() {
  if (!newName.value.trim()) return
  creating.value = true
  createError.value = ''
  try {
    const res = await api.devices.create(newName.value.trim())
    pairingToken.value = res.pairing_token
    newName.value = ''
    await load()
    if (!res.pairing_token) addOpen.value = false
  } catch (e) {
    createError.value = e instanceof ApiError ? e.message : 'Could not create device.'
  } finally {
    creating.value = false
  }
}

function closeAddDialog() {
  addOpen.value = false
  pairingToken.value = null
  createError.value = ''
}

let closeSocket: (() => void) | null = null

onMounted(() => {
  load()
  closeSocket = connectDeviceStatusSocket((event) => {
    const device = devices.value.find((d) => d.id === event.device_id)
    if (device) {
      device.online = event.online
      device.last_seen_at = event.last_seen_at
    }
  })
})

onUnmounted(() => closeSocket?.())
</script>

<template>
  <div>
    <div class="mb-6 flex items-center justify-between">
      <h1 class="text-xl font-semibold">Devices</h1>
      <Button v-if="auth.hasRole('operator')" @click="addOpen = true">Add device</Button>
    </div>

    <Input v-model="q" placeholder="Search by name…" class="mb-4 max-w-xs" @keyup.enter="load" />

    <Card v-if="loading" class="p-6 text-sm text-muted-foreground">Loading…</Card>
    <Card v-else-if="error" class="p-6 text-sm text-danger">{{ error }}</Card>
    <Card v-else-if="devices.length === 0" class="p-6 text-sm text-muted-foreground">
      No devices yet.
    </Card>
    <Table v-else>
      <thead class="border-b border-border bg-surface-muted text-xs uppercase text-muted-foreground">
        <tr>
          <th class="px-4 py-2 font-medium">Name</th>
          <th class="px-4 py-2 font-medium">Status</th>
          <th class="px-4 py-2 font-medium">Pairing</th>
          <th class="px-4 py-2 font-medium">Last seen</th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="d in devices"
          :key="d.id"
          class="cursor-pointer border-b border-border last:border-0 hover:bg-surface-muted"
        >
          <td class="px-4 py-2">
            <RouterLink :to="{ name: 'device-detail', params: { id: d.id } }" class="font-medium">
              {{ d.name }}
            </RouterLink>
          </td>
          <td class="px-4 py-2">
            <Badge :tone="d.online ? 'success' : 'neutral'">{{ d.online ? 'Online' : 'Offline' }}</Badge>
          </td>
          <td class="px-4 py-2">
            <Badge :tone="d.pairing_state === 'authorized' ? 'accent' : 'neutral'">{{
              d.pairing_state
            }}</Badge>
          </td>
          <td class="px-4 py-2 text-muted-foreground">
            {{ d.last_seen_at ? new Date(d.last_seen_at).toLocaleString() : '—' }}
          </td>
        </tr>
      </tbody>
    </Table>

    <Dialog v-model:open="addOpen">
      <template #default="{ close }">
        <div v-if="pairingToken">
          <h2 class="text-base font-semibold">Pairing token</h2>
          <p class="mt-1 text-sm text-muted-foreground">
            Enter this into the device's WebConfig HQ section. It will not be shown again.
          </p>
          <code class="mt-3 block break-all rounded-md bg-surface-muted p-3 text-sm">{{ pairingToken }}</code>
          <Button class="mt-4 w-full" @click="closeAddDialog(); close()">Done</Button>
        </div>
        <div v-else>
          <h2 class="text-base font-semibold">Add device</h2>
          <Input v-model="newName" placeholder="Device name" class="mt-4" @keyup.enter="handleCreate" />
          <p v-if="createError" class="mt-2 text-sm text-danger">{{ createError }}</p>
          <div class="mt-4 flex justify-end gap-2">
            <Button variant="secondary" @click="close">Cancel</Button>
            <Button :disabled="creating" @click="handleCreate">{{ creating ? 'Creating…' : 'Create' }}</Button>
          </div>
        </div>
      </template>
    </Dialog>
  </div>
</template>
