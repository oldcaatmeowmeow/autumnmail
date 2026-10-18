<script setup>
import { computed } from 'vue'

const props = defineProps({
  category: { type: String, default: '' },
})

const tone = computed(() => {
  const value = props.category || ''
  if (value.includes('拒')) return 'reject'
  if (value.includes('Offer') || value.includes('录用')) return 'offer'
  if (value.includes('测评') || value.includes('笔试')) return 'assessment'
  if (value.includes('面')) return 'interview'
  return 'info'
})
</script>

<template>
  <span class="badge" :class="tone">{{ category || '其他' }}</span>
</template>
