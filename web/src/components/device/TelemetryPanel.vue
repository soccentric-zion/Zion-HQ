<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { api } from '@/lib/api'
import Card from '@/components/ui/Card.vue'

const props = defineProps<{ deviceId: string }>()

interface Point {
  recorded_at: string
  value: number
}
const series = ref<Record<string, Point[]>>({})
const loading = ref(true)
const error = ref('')

function sparklinePath(points: Point[], width = 240, height = 48): string {
  if (points.length < 2) return ''
  const values = points.map((p) => p.value)
  const min = Math.min(...values)
  const max = Math.max(...values)
  const span = max - min || 1
  return points
    .map((p, i) => {
      const x = (i / (points.length - 1)) * width
      const y = height - ((p.value - min) / span) * height
      return `${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`
    })
    .join(' ')
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    series.value = await api.devices.telemetry(props.deviceId)
  } catch {
    error.value = 'Could not load telemetry.'
  } finally {
    loading.value = false
  }
}

watch(() => props.deviceId, load)
onMounted(load)
</script>

<template>
  <Card v-if="loading" class="p-6 text-sm text-muted-foreground">Loading…</Card>
  <Card v-else-if="error" class="p-6 text-sm text-danger">{{ error }}</Card>
  <Card v-else-if="Object.keys(series).length === 0" class="p-6 text-sm text-muted-foreground">
    No telemetry reported yet.
  </Card>
  <div v-else class="grid grid-cols-1 gap-4 sm:grid-cols-2">
    <Card v-for="(points, metric) in series" :key="metric" class="p-4">
      <div class="mb-2 flex items-baseline justify-between">
        <span class="text-sm font-medium">{{ metric }}</span>
        <span class="text-sm text-muted-foreground">{{ points.at(-1)?.value.toFixed(1) }}</span>
      </div>
      <svg viewBox="0 0 240 48" class="h-12 w-full">
        <path :d="sparklinePath(points)" fill="none" stroke="var(--color-accent)" stroke-width="2" />
      </svg>
    </Card>
  </div>
</template>
