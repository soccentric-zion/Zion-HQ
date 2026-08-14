<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api, ApiError } from '@/lib/api'
import type { AlarmRule } from '@/lib/types'
import { useAuthStore } from '@/stores/auth'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Card from '@/components/ui/Card.vue'
import Dialog from '@/components/ui/Dialog.vue'
import Input from '@/components/ui/Input.vue'
import Table from '@/components/ui/Table.vue'

const auth = useAuthStore()
const rules = ref<AlarmRule[]>([])
const loading = ref(true)

const createOpen = ref(false)
const name = ref('')
const kind = ref<'fault_code' | 'telemetry_threshold'>('fault_code')
const severity = ref('critical')
const metric = ref('cpu_temp')
const op = ref('>')
const value = ref('85')
const creating = ref(false)
const createError = ref('')

async function load() {
  loading.value = true
  rules.value = await api.alarmRules.list()
  loading.value = false
}

async function create() {
  if (!name.value.trim()) return
  creating.value = true
  createError.value = ''
  try {
    const condition =
      kind.value === 'fault_code'
        ? { kind: 'fault_code', severity: severity.value }
        : { kind: 'telemetry_threshold', metric: metric.value, op: op.value, value: Number(value.value) }
    await api.alarmRules.create(name.value.trim(), condition)
    name.value = ''
    createOpen.value = false
    await load()
  } catch (e) {
    createError.value = e instanceof ApiError ? e.message : 'Could not create alarm rule.'
  } finally {
    creating.value = false
  }
}

onMounted(load)
</script>

<template>
  <div>
    <div class="mb-6 flex items-center justify-between">
      <h1 class="text-xl font-semibold">Alarm rules</h1>
      <Button v-if="auth.hasRole('operator')" @click="createOpen = true">New rule</Button>
    </div>
    <p class="mb-4 text-sm text-muted-foreground">
      A fault existing does not automatically raise an alarm -- rules decide what's worth surfacing.
    </p>

    <Card v-if="loading" class="p-6 text-sm text-muted-foreground">Loading…</Card>
    <Card v-else-if="rules.length === 0" class="p-6 text-sm text-muted-foreground">
      No alarm rules configured yet.
    </Card>
    <Table v-else>
      <thead class="border-b border-border bg-surface-muted text-xs uppercase text-muted-foreground">
        <tr>
          <th class="px-4 py-2 font-medium">Name</th>
          <th class="px-4 py-2 font-medium">Condition</th>
          <th class="px-4 py-2 font-medium">Status</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="r in rules" :key="r.id" class="border-b border-border last:border-0">
          <td class="px-4 py-2 font-medium">{{ r.name }}</td>
          <td class="px-4 py-2"><code class="text-xs">{{ JSON.stringify(r.condition) }}</code></td>
          <td class="px-4 py-2">
            <Badge :tone="r.enabled ? 'success' : 'neutral'">{{ r.enabled ? 'Enabled' : 'Disabled' }}</Badge>
          </td>
        </tr>
      </tbody>
    </Table>

    <Dialog v-model:open="createOpen">
      <template #default="{ close }">
        <h2 class="text-base font-semibold">New alarm rule</h2>
        <Input v-model="name" placeholder="Rule name" class="mt-4" />
        <select v-model="kind" class="mt-3 h-9 w-full rounded-md border border-border bg-surface px-3 text-sm">
          <option value="fault_code">Fault severity match</option>
          <option value="telemetry_threshold">Telemetry threshold</option>
        </select>

        <div v-if="kind === 'fault_code'" class="mt-3">
          <select v-model="severity" class="h-9 w-full rounded-md border border-border bg-surface px-3 text-sm">
            <option value="info">info</option>
            <option value="warn">warn</option>
            <option value="critical">critical</option>
          </select>
        </div>
        <div v-else class="mt-3 grid grid-cols-3 gap-2">
          <Input v-model="metric" placeholder="metric" />
          <select v-model="op" class="h-9 rounded-md border border-border bg-surface px-2 text-sm">
            <option value=">">&gt;</option>
            <option value="<">&lt;</option>
          </select>
          <Input v-model="value" placeholder="threshold" inputmode="decimal" />
        </div>

        <p v-if="createError" class="mt-2 text-sm text-danger">{{ createError }}</p>
        <div class="mt-4 flex justify-end gap-2">
          <Button variant="secondary" @click="close">Cancel</Button>
          <Button :disabled="creating" @click="create">{{ creating ? 'Creating…' : 'Create' }}</Button>
        </div>
      </template>
    </Dialog>
  </div>
</template>
