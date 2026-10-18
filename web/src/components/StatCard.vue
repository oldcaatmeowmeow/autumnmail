<script setup>
import AppIcon from './AppIcon.vue'

defineProps({
  label: { type: String, required: true },
  value: { type: [String, Number], default: 0 },
  hint: { type: String, default: '' },
  icon: { type: String, default: 'sparkles' },
  tone: { type: String, default: 'brand' },
})
</script>

<template>
  <div class="stat-card">
    <div class="stat-icon" :class="tone">
      <AppIcon :name="icon" :size="18" />
    </div>
    <div class="stat-body">
      <div class="stat-value">{{ value }}</div>
      <div class="stat-label">{{ label }}</div>
      <div v-if="hint" class="stat-hint">{{ hint }}</div>
    </div>
  </div>
</template>
