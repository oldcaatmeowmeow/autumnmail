<script setup>
defineProps({
  label: { type: String, required: true },
  value: { type: [String, Number], default: 0 },
  hint: { type: String, default: '' },
  tone: { type: String, default: 'brand' },
})
</script>

<template>
  <div class="stat-card">
    <div class="stat-label">
      <span class="stat-mark" :class="tone"></span>
      {{ label }}
    </div>
    <div class="stat-value">{{ value }}</div>
    <div v-if="hint" class="stat-hint">{{ hint }}</div>
  </div>
</template>
