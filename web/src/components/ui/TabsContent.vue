<script setup lang="ts">
import { inject } from 'vue'
import { TabsKey } from '@/lib/tabsContext'

const props = defineProps<{ value: string }>()
const ctx = inject(TabsKey)
if (!ctx) throw new Error('TabsContent must be used inside <Tabs>')
</script>

<template>
  <div v-if="ctx.active.value === props.value" class="pt-4">
    <slot />
  </div>
</template>
