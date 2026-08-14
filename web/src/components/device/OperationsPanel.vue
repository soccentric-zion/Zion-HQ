<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { api, ApiError } from '@/lib/api'
import type { Backup, Device } from '@/lib/types'
import { useAuthStore } from '@/stores/auth'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Card from '@/components/ui/Card.vue'
import Dialog from '@/components/ui/Dialog.vue'
import Table from '@/components/ui/Table.vue'

const props = defineProps<{ device: Device }>()
const emit = defineEmits<{ updated: [Device] }>()
const auth = useAuthStore()

const backups = ref<Backup[]>([])
const busy = ref(false)
const message = ref('')
const confirmKind = ref<'reset' | 'disable' | null>(null)

async function loadBackups() {
  try {
    const res = await api.backups.list(props.device.id)
    backups.value = res.items
  } catch {
    message.value = 'Could not load backups.'
  }
}

async function takeBackup() {
  busy.value = true
  try {
    await api.backups.takeNow(props.device.id)
    message.value = 'Backup requested.'
    await loadBackups()
  } catch (e) {
    message.value = e instanceof ApiError ? e.message : 'Backup request failed.'
  } finally {
    busy.value = false
  }
}

async function restore(backupId: string) {
  busy.value = true
  try {
    await api.backups.restore(props.device.id, backupId)
    message.value = 'Restore requested.'
  } catch (e) {
    message.value = e instanceof ApiError ? e.message : 'Restore request failed.'
  } finally {
    busy.value = false
  }
}

async function confirmAction() {
  if (!confirmKind.value) return
  busy.value = true
  try {
    if (confirmKind.value === 'reset') {
      await api.devices.factoryReset(props.device.id)
      message.value = 'Factory reset requested.'
    } else {
      const updated = await api.devices.disable(props.device.id)
      emit('updated', updated)
      message.value = 'Device disabled.'
    }
  } catch (e) {
    message.value = e instanceof ApiError ? e.message : 'Action failed.'
  } finally {
    busy.value = false
    confirmKind.value = null
  }
}

watch(() => props.device.id, loadBackups)
onMounted(loadBackups)
</script>

<template>
  <div class="space-y-6">
    <p v-if="message" class="text-sm text-muted-foreground">{{ message }}</p>

    <Card class="p-4">
      <div class="flex items-center justify-between">
        <div>
          <h3 class="text-sm font-semibold">Backup &amp; restore</h3>
          <p class="text-sm text-muted-foreground">Trigger an on-demand backup, or restore a prior one.</p>
        </div>
        <Button v-if="auth.hasRole('operator')" size="sm" :disabled="busy" @click="takeBackup"
          >Take backup now</Button
        >
      </div>
      <Table v-if="backups.length" class="mt-4">
        <thead class="border-b border-border bg-surface-muted text-xs uppercase text-muted-foreground">
          <tr>
            <th class="px-4 py-2 font-medium">Created</th>
            <th class="px-4 py-2 font-medium">Restored</th>
            <th class="px-4 py-2 font-medium"></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="b in backups" :key="b.id" class="border-b border-border last:border-0">
            <td class="px-4 py-2">{{ new Date(b.created_at).toLocaleString() }}</td>
            <td class="px-4 py-2 text-muted-foreground">
              {{ b.restored_at ? new Date(b.restored_at).toLocaleString() : '—' }}
            </td>
            <td class="px-4 py-2 text-right">
              <Button v-if="auth.hasRole('admin')" size="sm" variant="secondary" :disabled="busy" @click="restore(b.id)"
                >Restore</Button
              >
            </td>
          </tr>
        </tbody>
      </Table>
    </Card>

    <Card v-if="auth.hasRole('admin')" class="p-4">
      <h3 class="text-sm font-semibold">Danger zone</h3>
      <p class="mt-1 text-sm text-muted-foreground">
        These actions are logged to the audit log and cannot be undone by HQ.
      </p>
      <div class="mt-3 flex gap-2">
        <Button variant="destructive" size="sm" @click="confirmKind = 'reset'">Factory reset</Button>
        <Button
          variant="destructive"
          size="sm"
          :disabled="device.pairing_state === 'disabled'"
          @click="confirmKind = 'disable'"
          >Disable device</Button
        >
      </div>
      <Badge v-if="device.pairing_state === 'disabled'" tone="danger" class="mt-3">Currently disabled</Badge>
    </Card>

    <Dialog :open="confirmKind !== null" @update:open="(v) => !v && (confirmKind = null)">
      <template #default="{ close }">
        <h2 class="text-base font-semibold">
          {{ confirmKind === 'reset' ? 'Factory reset this device?' : 'Disable this device?' }}
        </h2>
        <p class="mt-2 text-sm text-muted-foreground">
          {{
            confirmKind === 'reset'
              ? 'The device will wipe local state and require re-pairing.'
              : 'HQ will refuse this device\'s connection immediately, even with a valid credential.'
          }}
        </p>
        <div class="mt-4 flex justify-end gap-2">
          <Button variant="secondary" @click="close(); confirmKind = null">Cancel</Button>
          <Button variant="destructive" :disabled="busy" @click="confirmAction(); close()">Confirm</Button>
        </div>
      </template>
    </Dialog>
  </div>
</template>
