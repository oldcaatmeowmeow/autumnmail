<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api'
import { toast } from '../toast'
import { categoryTone, dateKey, fmtTime, dayNum, monthShort } from '../utils'
import AppIcon from '../components/AppIcon.vue'
import EventBadge from '../components/EventBadge.vue'
import EmptyState from '../components/EmptyState.vue'

const router = useRouter()
const cursor = ref(new Date())
const events = ref([])
const loading = ref(false)
const weekdays = ['一', '二', '三', '四', '五', '六', '日']

function keyOf(date) {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function startOfWeek(date) {
  const result = new Date(date)
  const offset = (result.getDay() + 6) % 7
  result.setDate(result.getDate() - offset)
  result.setHours(0, 0, 0, 0)
  return result
}

const weeks = computed(() => {
  const first = new Date(cursor.value.getFullYear(), cursor.value.getMonth(), 1)
  const start = startOfWeek(first)
  const today = new Date()
  const todayKey = keyOf(today)
  const grid = []
  for (let w = 0; w < 6; w += 1) {
    const week = []
    for (let d = 0; d < 7; d += 1) {
      const date = new Date(start)
      date.setDate(start.getDate() + w * 7 + d)
      const key = keyOf(date)
      week.push({
        date,
        key,
        inMonth: date.getMonth() === cursor.value.getMonth(),
        isToday: key === todayKey,
      })
    }
    grid.push(week)
  }
  return grid
})

const range = computed(() => ({
  from: `${weeks.value[0][0].key}T00:00`,
  to: `${weeks.value[5][6].key}T23:59`,
}))

const eventsByDay = computed(() => {
  const map = {}
  for (const event of events.value) {
    const key = dateKey(event.event_time || event.deadline)
    if (!key) continue
    if (!map[key]) map[key] = []
    map[key].push(event)
  }
  return map
})

const monthKey = computed(
  () => `${cursor.value.getFullYear()}-${String(cursor.value.getMonth() + 1).padStart(2, '0')}`
)

const monthEvents = computed(() =>
  events.value
    .filter((event) => dateKey(event.event_time || event.deadline).startsWith(monthKey.value))
    .sort((a, b) =>
      String(a.event_time || a.deadline).localeCompare(String(b.event_time || b.deadline))
    )
)

const monthTitle = computed(
  () => `${cursor.value.getFullYear()} 年 ${cursor.value.getMonth() + 1} 月`
)

async function load() {
  loading.value = true
  try {
    events.value = await api.events({ from: range.value.from, to: range.value.to })
  } catch (error) {
    toast(error.message, 'error')
  } finally {
    loading.value = false
  }
}

onMounted(load)
watch(range, load)

function shift(delta) {
  const next = new Date(cursor.value)
  next.setMonth(next.getMonth() + delta)
  cursor.value = next
}

function goToday() {
  cursor.value = new Date()
}

function eventsForDay(day) {
  return eventsByDay.value[day.key] || []
}

function open(event) {
  router.push(`/opportunities/${event.application_id}`)
}

async function exportIcs() {
  try {
    await api.download('/export/ics', 'autumnmail-interviews.ics')
    toast('日历文件已导出，可导入系统日历', 'success')
  } catch (error) {
    toast(error.message, 'error')
  }
}
</script>

<template>
  <div class="page">
    <div class="calendar-layout">
      <section class="panel">
        <header class="calendar-head">
          <h3>{{ monthTitle }}</h3>
          <div class="calendar-nav">
            <button class="btn ghost sm" @click="shift(-1)">上一月</button>
            <button class="btn ghost sm" @click="goToday">今天</button>
            <button class="btn ghost sm" @click="shift(1)">下一月</button>
          </div>
        </header>
        <div class="calendar-grid">
          <div v-for="day in weekdays" :key="day" class="weekday">{{ day }}</div>
          <template v-for="(week, index) in weeks" :key="index">
            <div
              v-for="day in week"
              :key="day.key"
              class="cal-cell"
              :class="{ out: !day.inMonth, today: day.isToday }"
            >
              <div class="cal-date">{{ day.date.getDate() }}</div>
              <button
                v-for="event in eventsForDay(day)"
                :key="event.id"
                class="cal-event"
                :class="categoryTone(event.category)"
                :title="`${event.company} · ${event.title || event.category}`"
                @click="open(event)"
              >
                {{ event.company }} · {{ event.title || event.category }}
              </button>
            </div>
          </template>
        </div>
      </section>

      <aside class="cal-side">
        <section class="panel">
          <header class="panel-head">
            <h3>本月安排</h3>
            <span class="muted">{{ monthEvents.length }} 项</span>
          </header>
          <div v-if="monthEvents.length" class="event-list">
            <button
              v-for="event in monthEvents"
              :key="event.id"
              class="event-row"
              @click="open(event)"
            >
              <div class="event-date">
                <span>{{ dayNum(event.event_time || event.deadline) }}</span>
                <small>{{ monthShort(event.event_time || event.deadline) }}</small>
              </div>
              <div class="event-main">
                <div class="event-title">{{ event.company }}</div>
                <div class="event-sub">
                  {{ event.title || event.category }} ·
                  {{ fmtTime(event.event_time || event.deadline) }}
                </div>
              </div>
              <EventBadge :category="event.category" />
            </button>
          </div>
          <EmptyState
            v-else
            icon="calendar"
            title="本月还没有安排"
            hint="面试、测评与截止时间会自动出现在这里。"
          />
        </section>

        <button class="btn ghost" @click="exportIcs">
          <AppIcon name="download" :size="16" /> 导出 .ics 日历
        </button>
        <p class="muted" style="font-size: 11.5px; line-height: 1.6; margin: 0 4px">
          导入系统日历后，面试前 30 分钟自动提醒。所有数据仍保存在本机。
        </p>
      </aside>
    </div>
  </div>
</template>
