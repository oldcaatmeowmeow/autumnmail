<script setup>
import AppIcon from './AppIcon.vue'

defineProps({
  title: { type: String, default: '暂无内容' },
  hint: { type: String, default: '' },
  icon: { type: String, default: 'sparkles' },
})
</script>

<template>
  <div class="empty">
    <div class="empty-icon"><AppIcon :name="icon" :size="22" /></div>
    <p>{{ title }}</p>
    <span v-if="hint">{{ hint }}</span>
  </div>
</template>
