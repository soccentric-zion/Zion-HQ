<script setup lang="ts">
import { cn } from '@/lib/utils'

defineProps<{ class?: string }>()
</script>

<template>
  <div class="overflow-x-auto rounded-lg border border-border">
    <table :class="cn('w-full text-left text-sm', $props.class)">
      <slot />
    </table>
  </div>
</template>
