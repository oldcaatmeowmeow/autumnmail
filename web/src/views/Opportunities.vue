<script setup>
import { onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api'
import { store } from '../store'
import { toast } from '../toast'
import { fmtDateTime, statusTone } from '../utils'
import AppIcon from '../components/AppIcon.vue'
import EmptyState from '../components/EmptyState.vue'

const router = useRouter()
const items = ref([])
const loading = ref(true)
const status = ref('全部')
const keyword = ref('')
const statuses = ['全部', '面试中', '测评中', '投递中', '已Offer', '已拒绝', '已结束']
let timer = null

async function load() {
  loading.value = true
  try {
    items.value = await api.opportunities({ status: status.value, q: keyword.value })
  } catch (error) {
    toast(error.message, 'error')
  } finally {
    loading.value = false
  }
}

onMounted(load)
watch(status, load)
watch(keyword, () => {
  clearTimeout(timer)
  timer = setTimeout(load, 220)
})
watch(() => store.revision, load)

function open(item) {
  router.push(`/opportunities/${item.id}`)
}
</script>

<template>
  <div class="page">
    <div class="filter-bar">
      <div class="chips">
        <button
          v-for="item in statuses"
          :key="item"
          class="chip"
          :class="{ active: status === item }"
          @click="status = item"
        >
          {{ item }}
        </button>
      </div>
      <div class="search-box">
        <AppIcon name="search" :size="15" />
        <input v-model="keyword" placeholder="搜索公司或岗位" />
      </div>
    </div>

    <div v-if="loading" class="panel">
      <EmptyState icon="refresh" title="正在加载机会…" />
    </div>

    <div v-else-if="items.length" class="opp-list">
      <button v-for="item in items" :key="item.id" class="opp-card" @click="open(item)">
        <div class="avatar">{{ item.company.slice(0, 1) }}</div>
        <div class="opp-main">
          <div class="opp-company">{{ item.company }}</div>
          <div class="opp-position">
            {{ item.position }}
            <template v-if="item.location"> · {{ item.location }}</template>
            · {{ item.event_count }} 个节点
          </div>
        </div>
        <div class="opp-meta">
          <span class="badge" :class="statusTone(item.status)">{{ item.status }}</span>
          <div class="opp-next">
            <template v-if="item.next_event_time">
              <strong>{{ item.next_title || item.next_category }}</strong>
              <span>{{ fmtDateTime(item.next_event_time) }}</span>
            </template>
            <template v-else>
              <strong>暂无安排</strong>
              <span>等待新邮件</span>
            </template>
          </div>
          <AppIcon name="chevronRight" :size="17" class="chev" />
        </div>
      </button>
    </div>

    <div v-else class="panel">
      <EmptyState
        icon="briefcase"
        title="没有匹配的机会"
        hint="换个筛选条件，或点击右上角「同步邮件」。"
      />
    </div>
  </div>
</template>
