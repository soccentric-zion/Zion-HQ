<script setup lang="ts">
import { inject } from 'vue'
import { TabsKey } from '@/lib/tabsContext'
import { cn } from '@/lib/utils'

const props = defineProps<{ value: string }>()
const ctx = inject(TabsKey)
if (!ctx) throw new Error('TabsTrigger must be used inside <Tabs>')
</script>

<template>
  <button
    type="button"
    :class="
      cn(
        'rounded px-3 py-1 text-sm font-medium transition-colors',
        ctx.active.value === props.value
          ? 'bg-surface text-foreground shadow-sm'
          : 'text-muted-foreground hover:text-foreground',
      )
    "
    @click="ctx.setActive(props.value)"
  >
    <slot />
  </button>
</template>
