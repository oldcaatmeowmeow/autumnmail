<script setup>
import { toasts } from '../toast'
import AppIcon from './AppIcon.vue'
</script>

<template>
  <div class="toast-stack">
    <TransitionGroup name="toast">
      <div v-for="item in toasts" :key="item.id" class="toast" :class="item.type">
        <AppIcon :name="item.type === 'error' ? 'alert' : 'checkCircle'" :size="16" />
        <span>{{ item.message }}</span>
      </div>
    </TransitionGroup>
  </div>
</template>
