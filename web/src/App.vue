<script setup>
import { computed, onMounted, ref } from 'vue'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'
import AppIcon from './components/AppIcon.vue'
import ToastStack from './components/ToastStack.vue'
import { api } from './api'
import { refreshBootstrap, store } from './store'
import { toast } from './toast'

const route = useRoute()
const router = useRouter()
const syncing = ref(false)
const bootError = ref('')

const nav = [
  { to: '/', label: '仪表盘', icon: 'dashboard' },
  { to: '/opportunities', label: '机会', icon: 'briefcase' },
  { to: '/calendar', label: '日历', icon: 'calendar' },
  { to: '/review', label: '审核队列', icon: 'checkCircle' },
  { to: '/settings', label: '设置', icon: 'settings' },
]

const isBare = computed(() => route.meta.bare === true)
const pageTitle = computed(() => route.meta.title || '秋信')
const pageSubtitle = computed(() => route.meta.subtitle || '')
const reviewCount = computed(() => store.bootstrap?.review_count || 0)

function isActive(path) {
  return path === '/' ? route.path === '/' : route.path.startsWith(path)
}

onMounted(async () => {
  try {
    const boot = await refreshBootstrap()
    if (!boot.onboarded && route.path !== '/onboarding') {
      router.replace('/onboarding')
    }
  } catch (error) {
    bootError.value = error.message
  } finally {
    store.loading = false
  }
})

async function sync() {
  syncing.value = true
  try {
    const result = await api.sync()
    if (result.ok) {
      toast(result.message || `同步完成：扫描 ${result.scanned} 封，新增 ${result.new} 封`, 'success')
    } else if (result.message && (result.message.includes('还没有添加') || result.message.includes('演示账户'))) {
      toast(result.message, 'info')
    } else {
      toast(result.message || '同步失败', 'error')
    }
    await refreshBootstrap()
    store.revision += 1
  } catch (error) {
    toast(error.message, 'error')
  } finally {
    syncing.value = false
  }
}
</script>

<template>
  <div v-if="store.loading" class="boot">
    <div class="boot-mark"><AppIcon name="mail" :size="26" /></div>
    <p>正在启动秋信…</p>
  </div>

  <div v-else-if="bootError" class="boot">
    <div class="boot-error">
      <div class="boot-mark danger"><AppIcon name="alert" :size="24" /></div>
      <h2>无法连接本地服务</h2>
      <p>{{ bootError }}</p>
      <p class="muted">请从桌面应用启动，而不是直接打开浏览器。</p>
    </div>
  </div>

  <div v-else class="app-shell" :class="{ bare: isBare }">
    <aside v-if="!isBare" class="sidebar">
      <div class="brand">
        <div class="brand-mark"><AppIcon name="mail" :size="19" /></div>
        <div class="brand-text">
          <strong>秋信</strong>
          <span>AutumnMail</span>
        </div>
      </div>

      <nav class="nav">
        <RouterLink
          v-for="item in nav"
          :key="item.to"
          :to="item.to"
          class="nav-item"
          :class="{ active: isActive(item.to) }"
        >
          <AppIcon :name="item.icon" :size="18" />
          <span>{{ item.label }}</span>
          <span v-if="item.to === '/review' && reviewCount" class="nav-count">{{ reviewCount }}</span>
        </RouterLink>
      </nav>

      <div class="sidebar-foot">
        <div class="privacy-line"><AppIcon name="shield" :size="14" /> 数据仅存本机</div>
        <div class="version">v{{ store.meta.version }}</div>
      </div>
    </aside>

    <div class="main">
      <header v-if="!isBare" class="topbar">
        <div class="topbar-title">
          <h1>{{ pageTitle }}</h1>
          <p>{{ pageSubtitle }}</p>
        </div>
        <div class="topbar-actions">
          <span v-if="store.bootstrap?.demo_mode" class="pill demo">演示数据</span>
          <button class="btn ghost" :disabled="syncing" @click="sync">
            <AppIcon name="refresh" :size="16" :class="{ spin: syncing }" />
            {{ syncing ? '同步中…' : '同步邮件' }}
          </button>
        </div>
      </header>

      <div :class="isBare ? 'bare-content' : 'content'">
        <RouterView />
      </div>
    </div>
  </div>

  <ToastStack />
</template>
