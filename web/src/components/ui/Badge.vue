<script setup lang="ts">
import { cva } from 'class-variance-authority'
import { cn } from '@/lib/utils'

const badgeVariants = cva('inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium', {
  variants: {
    tone: {
      neutral: 'bg-surface-muted text-muted-foreground',
      accent: 'bg-accent-muted text-accent',
      success: 'bg-success-muted text-success',
      warning: 'bg-warning-muted text-warning',
      danger: 'bg-danger-muted text-danger',
    },
  },
  defaultVariants: { tone: 'neutral' },
})

// See Button.vue for why these are plain literal unions, not VariantProps<...>.
withDefaults(
  defineProps<{
    tone?: 'neutral' | 'accent' | 'success' | 'warning' | 'danger'
    class?: string
  }>(),
  { tone: 'neutral' },
)
</script>

<template>
  <span :class="cn(badgeVariants({ tone }), $props.class)">
    <slot />
  </span>
</template>
