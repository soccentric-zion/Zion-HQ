<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { api } from '@/lib/api'
import type { LogBundle } from '@/lib/types'
import Button from '@/components/ui/Button.vue'
import Card from '@/components/ui/Card.vue'
import Table from '@/components/ui/Table.vue'

const props = defineProps<{ deviceId: string }>()
const bundles = ref<LogBundle[]>([])
const loading = ref(true)
const error = ref('')

async function load() {
  loading.value = true
  error.value = ''
  try {
    const res = await api.logs.list(props.deviceId)
    bundles.value = res.items
  } catch {
    error.value = 'Could not load log bundles.'
  } finally {
    loading.value = false
  }
}

async function download(id: string) {
  const { download_url } = await api.logs.downloadUrl(props.deviceId, id)
  window.open(download_url, '_blank')
}

function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  return `${(n / 1024 / 1024).toFixed(1)} MB`
}

watch(() => props.deviceId, load)
onMounted(load)
</script>

<template>
  <div v-if="loading" class="text-sm text-muted-foreground">Loading…</div>
  <Card v-else-if="error" class="p-6 text-sm text-danger">{{ error }}</Card>
  <Card v-else-if="bundles.length === 0" class="p-6 text-sm text-muted-foreground">
    No log bundles uploaded yet.
  </Card>
  <Table v-else>
    <thead class="border-b border-border bg-surface-muted text-xs uppercase text-muted-foreground">
      <tr>
        <th class="px-4 py-2 font-medium">Time range</th>
        <th class="px-4 py-2 font-medium">Uploaded</th>
        <th class="px-4 py-2 font-medium">Size</th>
        <th class="px-4 py-2 font-medium"></th>
      </tr>
    </thead>
    <tbody>
      <tr v-for="b in bundles" :key="b.id" class="border-b border-border last:border-0">
        <td class="px-4 py-2">
          {{ new Date(b.time_range_start).toLocaleString() }} &ndash;
          {{ new Date(b.time_range_end).toLocaleString() }}
        </td>
        <td class="px-4 py-2 text-muted-foreground">{{ new Date(b.uploaded_at).toLocaleString() }}</td>
        <td class="px-4 py-2 text-muted-foreground">{{ formatBytes(b.size_bytes) }}</td>
        <td class="px-4 py-2 text-right">
          <Button size="sm" variant="secondary" @click="download(b.id)">Download</Button>
        </td>
      </tr>
    </tbody>
  </Table>
</template>
