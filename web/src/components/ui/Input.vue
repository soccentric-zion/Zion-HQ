<script setup lang="ts">
import { cn } from '@/lib/utils'

defineProps<{ class?: string }>()
const model = defineModel<string>()
</script>

<template>
  <input
    v-model="model"
    :class="
      cn(
        'h-9 w-full rounded-md border border-border bg-surface px-3 text-sm placeholder:text-muted',
        'focus-visible:border-accent',
        $props.class,
      )
    "
  />
</template>
