<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { api } from '@/lib/api'
import type { Device } from '@/lib/types'
import Badge from '@/components/ui/Badge.vue'
import Card from '@/components/ui/Card.vue'
import Tabs from '@/components/ui/Tabs.vue'
import TabsList from '@/components/ui/TabsList.vue'
import TabsTrigger from '@/components/ui/TabsTrigger.vue'
import TabsContent from '@/components/ui/TabsContent.vue'
import TelemetryPanel from '@/components/device/TelemetryPanel.vue'
import FaultsAlarmsPanel from '@/components/device/FaultsAlarmsPanel.vue'
import LogsPanel from '@/components/device/LogsPanel.vue'
import OperationsPanel from '@/components/device/OperationsPanel.vue'

const props = defineProps<{ id: string }>()

const device = ref<Device | null>(null)
const loading = ref(true)
const error = ref('')

onMounted(async () => {
  try {
    device.value = await api.devices.get(props.id)
  } catch {
    error.value = 'Device not found.'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div>
    <RouterLink to="/" class="text-sm text-muted-foreground hover:text-foreground">&larr; Devices</RouterLink>

    <div v-if="loading" class="mt-4 text-sm text-muted-foreground">Loading…</div>
    <div v-else-if="error" class="mt-4 text-sm text-danger">{{ error }}</div>
    <template v-else-if="device">
      <div class="mt-2 mb-6 flex items-center gap-3">
        <h1 class="text-xl font-semibold">{{ device.name }}</h1>
        <Badge :tone="device.online ? 'success' : 'neutral'">{{ device.online ? 'Online' : 'Offline' }}</Badge>
        <Badge :tone="device.pairing_state === 'authorized' ? 'accent' : 'neutral'">{{
          device.pairing_state
        }}</Badge>
      </div>

      <Tabs default-value="overview">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="telemetry">Telemetry</TabsTrigger>
          <TabsTrigger value="faults">Faults &amp; Alarms</TabsTrigger>
          <TabsTrigger value="logs">Logs</TabsTrigger>
          <TabsTrigger value="ops">Operations</TabsTrigger>
        </TabsList>

        <TabsContent value="overview">
          <Card class="grid grid-cols-2 gap-4 p-6 text-sm sm:grid-cols-3">
            <div>
              <div class="text-muted-foreground">Serial</div>
              <div class="mt-1">{{ device.serial ?? '—' }}</div>
            </div>
            <div>
              <div class="text-muted-foreground">Board revision</div>
              <div class="mt-1">{{ device.board_rev ?? '—' }}</div>
            </div>
            <div>
              <div class="text-muted-foreground">Last seen</div>
              <div class="mt-1">
                {{ device.last_seen_at ? new Date(device.last_seen_at).toLocaleString() : '—' }}
              </div>
            </div>
            <div>
              <div class="text-muted-foreground">Created</div>
              <div class="mt-1">{{ new Date(device.created_at).toLocaleString() }}</div>
            </div>
          </Card>
        </TabsContent>

        <TabsContent value="telemetry">
          <TelemetryPanel :device-id="device.id" />
        </TabsContent>
        <TabsContent value="faults">
          <FaultsAlarmsPanel :device-id="device.id" />
        </TabsContent>
        <TabsContent value="logs">
          <LogsPanel :device-id="device.id" />
        </TabsContent>
        <TabsContent value="ops">
          <OperationsPanel :device="device" @updated="device = $event" />
        </TabsContent>
      </Tabs>
    </template>
  </div>
</template>
