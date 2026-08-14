<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '@/lib/api'
import type { AuditLogEntry } from '@/lib/types'
import Card from '@/components/ui/Card.vue'
import Table from '@/components/ui/Table.vue'

const entries = ref<AuditLogEntry[]>([])
const loading = ref(true)

onMounted(async () => {
  const res = await api.auditLog.list({ limit: 100 })
  entries.value = res.items
  loading.value = false
})
</script>

<template>
  <div>
    <h1 class="mb-6 text-xl font-semibold">Audit log</h1>
    <Card v-if="loading" class="p-6 text-sm text-muted-foreground">Loading…</Card>
    <Card v-else-if="entries.length === 0" class="p-6 text-sm text-muted-foreground">No activity yet.</Card>
    <Table v-else>
      <thead class="border-b border-border bg-surface-muted text-xs uppercase text-muted-foreground">
        <tr>
          <th class="px-4 py-2 font-medium">Time</th>
          <th class="px-4 py-2 font-medium">Action</th>
          <th class="px-4 py-2 font-medium">Details</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="e in entries" :key="e.id" class="border-b border-border last:border-0 align-top">
          <td class="whitespace-nowrap px-4 py-2 text-muted-foreground">
            {{ new Date(e.created_at).toLocaleString() }}
          </td>
          <td class="px-4 py-2 font-medium">{{ e.action }}</td>
          <td class="px-4 py-2 text-muted-foreground">
            <code class="text-xs">{{ JSON.stringify(e.payload) }}</code>
          </td>
        </tr>
      </tbody>
    </Table>
  </div>
</template>
