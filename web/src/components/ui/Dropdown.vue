<script setup lang="ts">
import { ref } from 'vue'
import { onClickOutside } from '@vueuse/core'
import { cn } from '@/lib/utils'

const open = ref(false)
const root = ref<HTMLElement | null>(null)
onClickOutside(root, () => (open.value = false))

defineProps<{ class?: string }>()
</script>

<template>
  <div ref="root" class="relative inline-block">
    <span @click="open = !open"><slot name="trigger" :open="open" /></span>
    <div
      v-if="open"
      :class="
        cn(
          'absolute right-0 z-40 mt-1 min-w-40 rounded-md border border-border bg-surface py-1 shadow-md',
          $props.class,
        )
      "
      @click="open = false"
    >
      <slot :close="() => (open = false)" />
    </div>
  </div>
</template>
