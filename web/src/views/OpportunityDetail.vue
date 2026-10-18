<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../api'
import { toast } from '../toast'
import { categoryTone, fmtDateTime, statusTone } from '../utils'
import AppIcon from '../components/AppIcon.vue'
import EventBadge from '../components/EventBadge.vue'
import EmptyState from '../components/EmptyState.vue'

const route = useRoute()
const router = useRouter()
const data = ref(null)
const loading = ref(true)
const busy = ref(0)

async function load() {
  loading.value = true
  try {
    data.value = await api.opportunity(route.params.id)
  } catch (error) {
    toast(error.message, 'error')
  } finally {
    loading.value = false
  }
}

onMounted(load)

const application = computed(() => data.value?.application)
const events = computed(() => data.value?.events || [])
const messages = computed(() => data.value?.messages || {})

const statusLabels = {
  pending: '待处理',
  confirmed: '已确认',
  done: '已完成',
  skipped: '已跳过',
}

async function setStatus(event, status) {
  busy.value = event.id
  try {
    await api.updateEvent(event.id, status)
    toast(status === 'done' ? '已标记为完成' : '状态已更新', 'success')
    await load()
  } catch (error) {
    toast(error.message, 'error')
  } finally {
    busy.value = 0
  }
}

function messageFor(event) {
  return event.message_id ? messages.value[event.message_id] : null
}
</script>

<template>
  <div class="page">
    <RouterLink to="/opportunities" class="back-link">
      <AppIcon name="arrowLeft" :size="15" /> 返回机会列表
    </RouterLink>

    <div v-if="loading" class="panel">
      <EmptyState icon="refresh" title="正在加载详情…" />
    </div>

    <template v-else-if="application">
      <section class="detail-head">
        <div class="avatar">{{ application.company.slice(0, 1) }}</div>
        <div class="detail-title">
          <h2>{{ application.company }}</h2>
          <p>
            {{ application.position }}
            <template v-if="application.location"> · {{ application.location }}</template>
            · {{ events.length }} 个节点
          </p>
        </div>
        <div class="detail-actions">
          <span class="badge" :class="statusTone(application.status)">{{ application.status }}</span>
        </div>
      </section>

      <section class="panel">
        <header class="panel-head">
          <h3>时间线</h3>
          <span class="muted">每条结论都附带原邮件依据</span>
        </header>
        <div v-if="events.length">
          <article
            v-for="event in events"
            :key="event.id"
            class="event-card"
          >
            <div class="event-card-top">
              <div class="event-card-body">
                <div class="event-card-title">
                  {{ event.title || event.category }}
                  <EventBadge :category="event.category" />
                  <span class="badge info">{{ statusLabels[event.status] || event.status }}</span>
                </div>
                <div class="event-card-meta">
                  <span>{{ fmtDateTime(event.event_time || event.deadline) }}</span>
                  <span v-if="event.platform">{{ event.platform }}</span>
                  <span v-if="event.duration_min">{{ event.duration_min }} 分钟</span>
                  <span v-if="event.needs_reply">需要回复</span>
                  <span v-if="event.confidence">
                    置信度 {{ Math.round(event.confidence * 100) }}%
                  </span>
                </div>
                <p v-if="event.evidence" class="quote">{{ event.evidence }}</p>
                <div v-if="messageFor(event)" class="event-card-meta">
                  <span>原邮件：{{ messageFor(event).subject }}</span>
                </div>
              </div>
              <div class="event-actions">
                <a
                  v-if="event.link"
                  class="btn subtle sm"
                  :href="event.link"
                  target="_blank"
                  rel="noreferrer"
                >
                  打开链接
                </a>
                <button
                  v-if="event.status !== 'done'"
                  class="btn ghost sm"
                  :disabled="busy === event.id"
                  @click="setStatus(event, 'done')"
                >
                  标记完成
                </button>
                <button
                  v-else
                  class="btn subtle sm"
                  :disabled="busy === event.id"
                  @click="setStatus(event, 'pending')"
                >
                  恢复待处理
                </button>
                <button
                  v-if="event.status !== 'skipped'"
                  class="btn subtle sm"
                  :disabled="busy === event.id"
                  @click="setStatus(event, 'skipped')"
                >
                  忽略
                </button>
              </div>
            </div>
          </article>
        </div>
        <EmptyState v-else icon="clock" title="还没有事件" hint="同步邮件后，这里会出现投递、测评与面试节点。" />
      </section>
    </template>

    <div v-else class="panel">
      <EmptyState icon="alert" title="机会不存在" hint="它可能已被删除，请返回列表。" />
    </div>
  </div>
</template>
