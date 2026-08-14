<script setup lang="ts">
import { provide, ref, watch } from 'vue'
import { TabsKey } from '@/lib/tabsContext'

const props = defineProps<{ modelValue?: string; defaultValue?: string }>()
const emit = defineEmits<{ 'update:modelValue': [string] }>()

const active = ref(props.modelValue ?? props.defaultValue ?? '')
watch(
  () => props.modelValue,
  (v) => {
    if (v !== undefined) active.value = v
  },
)

function setActive(value: string) {
  active.value = value
  emit('update:modelValue', value)
}

provide(TabsKey, { active, setActive })
</script>

<template>
  <div><slot /></div>
</template>
