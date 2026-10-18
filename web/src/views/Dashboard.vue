<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api'
import { store } from '../store'
import { toast } from '../toast'
import { categoryTone, dayNum, fmtDateTime, monthShort, timeAgo, isToday } from '../utils'
import AppIcon from '../components/AppIcon.vue'
import StatCard from '../components/StatCard.vue'
import EventBadge from '../components/EventBadge.vue'
import EmptyState from '../components/EmptyState.vue'

const router = useRouter()
const data = ref(null)
const loading = ref(true)

async function load() {
  loading.value = true
  try {
    data.value = await api.dashboard()
  } catch (error) {
    toast(error.message, 'error')
  } finally {
    loading.value = false
  }
}

onMounted(load)
watch(() => store.revision, load)

const greeting = computed(() => {
  const hour = new Date().getHours()
  if (hour < 6) return '夜深了'
  if (hour < 12) return '早上好'
  if (hour < 18) return '下午好'
  return '晚上好'
})

const dateLabel = new Intl.DateTimeFormat('zh-CN', {
  month: 'long',
  day: 'numeric',
  weekday: 'long',
}).format(new Date())

const todayDay = String(new Date().getDate()).padStart(2, '0')
const todayMonth = new Intl.DateTimeFormat('zh-CN', { month: 'long' }).format(new Date())

const stats = computed(() => data.value?.stats || {})
const today = computed(() => data.value?.today || [])
const upcoming = computed(() => data.value?.upcoming || [])
const actionItems = computed(() => data.value?.action_items || [])
const recent = computed(() => data.value?.recent || [])

function go(event) {
  router.push(`/opportunities/${event.application_id}`)
}
</script>

<template>
  <div class="page">
    <section class="hero">
      <div class="hero-date">
        <span class="hero-day">{{ todayDay }}</span>
        <span class="hero-month">{{ todayMonth }}</span>
      </div>
      <div class="hero-main">
        <p class="hero-kicker">{{ dateLabel }}</p>
        <h2>
          <template v-if="today.length">{{ greeting }}，今天有 {{ today.length }} 场面试</template>
          <template v-else>{{ greeting }}，今天没有面试安排</template>
        </h2>
        <p>
          未来 7 天 {{ stats.upcoming_7d || 0 }} 个节点，
          {{ stats.needs_reply || 0 }} 项需要你回复。数据只保存在这台电脑上。
        </p>
      </div>
      <div v-if="upcoming.length" class="hero-next">
        <span class="hero-next-label">下一个节点</span>
        <strong>{{ upcoming[0].company }}</strong>
        <span>{{ fmtDateTime(upcoming[0].event_time) }}</span>
        <span>{{ upcoming[0].title || upcoming[0].category }}</span>
      </div>
    </section>

    <section class="ledger">
      <StatCard label="7 天内面试/节点" :value="stats.upcoming_7d || 0" tone="brand" hint="含面试、测评与笔试" />
      <StatCard label="需要你处理" :value="stats.needs_reply || 0" tone="amber" hint="回复时间或确认安排" />
      <StatCard label="本周新拒信" :value="stats.new_rejections_7d || 0" tone="rose" hint="过去 7 天" />
      <StatCard label="进行中的机会" :value="stats.active_applications || 0" tone="green" hint="不含已拒绝/已结束" />
    </section>

    <div class="grid-2">
      <section class="panel">
        <header class="panel-head">
          <h3>接下来</h3>
          <span class="muted">未来 7 天 · {{ upcoming.length }} 项</span>
        </header>
        <div v-if="upcoming.length" class="event-list">
          <button v-for="event in upcoming" :key="event.id" class="event-row" @click="go(event)">
            <div class="event-date">
              <span>{{ dayNum(event.event_time) }}</span>
              <small>{{ monthShort(event.event_time) }}</small>
            </div>
            <div class="event-main">
              <div class="event-title">
                {{ event.company }}
                <span class="dot">·</span>
                {{ event.title || event.category }}
              </div>
              <div class="event-sub">
                {{ event.position }}
                <template v-if="event.platform"> · {{ event.platform }}</template>
                <template v-if="event.needs_reply"> · 待回复</template>
              </div>
            </div>
            <EventBadge :category="event.category" />
          </button>
        </div>
        <EmptyState
          v-else
          icon="calendar"
          title="未来 7 天没有安排"
          hint="有新的面试或测评时，这里会自动出现。"
        />
      </section>

      <section class="panel">
        <header class="panel-head">
          <h3>需要你处理</h3>
          <span class="badge info">{{ actionItems.length }}</span>
        </header>
        <div v-if="actionItems.length" class="event-list">
          <button
            v-for="event in actionItems"
            :key="event.id"
            class="event-row"
            @click="go(event)"
          >
            <div class="event-main">
              <div class="event-title">{{ event.company }} · {{ event.title || event.category }}</div>
              <div class="event-sub">
                {{ event.position }} · {{ fmtDateTime(event.event_time || event.deadline) }}
              </div>
            </div>
            <AppIcon name="chevronRight" :size="16" class="chev" />
          </button>
        </div>
        <EmptyState
          v-else
          icon="checkCircle"
          title="没有待处理事项"
          hint="需要回复、确认时间或完成测评时，会在这里提醒你。"
        />
      </section>
    </div>

    <section class="panel">
      <header class="panel-head">
        <h3>最近动态</h3>
        <RouterLink to="/opportunities" class="btn link">查看全部机会</RouterLink>
      </header>
      <div v-if="recent.length" class="timeline">
        <div
          v-for="event in recent"
          :key="event.id"
          class="timeline-item"
          :class="categoryTone(event.category)"
        >
          <div class="timeline-dot"></div>
          <div class="timeline-body">
            <div class="timeline-line">
              <span class="timeline-title">{{ event.company }} · {{ event.title || event.category }}</span>
              <EventBadge :category="event.category" />
              <span class="timeline-time">{{ timeAgo(event.created_at) }}</span>
            </div>
            <div class="timeline-company">{{ event.position }}<template v-if="isToday(event.event_time)"> · 今天</template></div>
            <p v-if="event.evidence" class="quote">{{ event.evidence }}</p>
          </div>
        </div>
      </div>
      <EmptyState v-else icon="sparkles" title="还没有动态" hint="同步邮件后，识别结果会出现在这里。" />
    </section>
  </div>
</template>
