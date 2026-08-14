<script setup lang="ts">
// Teleport and Transition are Vue global built-in components -- no import needed.
const open = defineModel<boolean>('open', { default: false })

function close() {
  open.value = false
}
</script>

<template>
  <Teleport to="body">
    <Transition name="fade">
      <div
        v-if="open"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4"
        @click.self="close"
      >
        <div class="w-full max-w-md rounded-lg border border-border bg-surface p-6 shadow-lg">
          <slot :close="close" />
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.15s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
