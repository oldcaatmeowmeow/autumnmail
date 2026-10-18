<script setup>
import { onMounted, reactive, ref } from 'vue'
import { api } from '../api'
import { store } from '../store'
import { toast } from '../toast'
import { fmtDateTime } from '../utils'
import AppIcon from '../components/AppIcon.vue'
import EventBadge from '../components/EventBadge.vue'
import EmptyState from '../components/EmptyState.vue'

const items = ref([])
const loading = ref(true)
const busy = ref(0)
const categories = [
  '投递确认',
  '测评邀请',
  '笔试邀请',
  'AI面试',
  '技术面',
  'HR面',
  '群面',
  '终面',
  '时间约定',
  '资料补充',
  'Offer',
  '拒信',
  '其他',
]
const choices = reactive({})

async function load() {
  loading.value = true
  try {
    items.value = await api.review()
    for (const item of items.value) {
      choices[item.id] = item.category
    }
  } catch (error) {
    toast(error.message, 'error')
  } finally {
    loading.value = false
  }
}

onMounted(load)

async function resolve(item, action) {
  busy.value = item.id
  try {
    await api.resolveReview(item.id, {
      action,
      category: action === 'change' ? choices[item.id] : undefined,
    })
    toast(action === 'skip' ? '已忽略该条' : '已确认，规则会记住这次纠正', 'success')
    items.value = items.value.filter((entry) => entry.id !== item.id)
    store.revision += 1
  } catch (error) {
    toast(error.message, 'error')
  } finally {
    busy.value = 0
  }
}
</script>

<template>
  <div class="page">
    <div class="notice">
      <AppIcon name="brain" :size="16" />
      <span>
        这些邮件的置信度低于 80%，系统没有自动下结论。确认或纠正后，会写入本地反馈表，用于迭代规则。
      </span>
    </div>

    <div v-if="loading" class="panel">
      <EmptyState icon="refresh" title="正在加载审核队列…" />
    </div>

    <div v-else-if="items.length" class="opp-list">
      <article v-for="item in items" :key="item.id" class="panel">
        <div class="event-card">
          <div class="event-card-top">
            <div class="event-card-body">
              <div class="event-card-title">
                {{ item.company }} · {{ item.title || item.category }}
                <EventBadge :category="item.category" />
              </div>
              <div class="event-card-meta">
                <span>{{ item.position }}</span>
                <span>{{ fmtDateTime(item.event_time || item.deadline) }}</span>
                <span>置信度 {{ Math.round((item.confidence || 0) * 100) }}%</span>
              </div>
              <p v-if="item.evidence" class="quote">{{ item.evidence }}</p>
              <div class="inline" style="margin-top: 12px">
                <select v-model="choices[item.id]" class="select" style="max-width: 180px">
                  <option v-for="category in categories" :key="category" :value="category">
                    {{ category }}
                  </option>
                </select>
                <button
                  class="btn primary sm"
                  :disabled="busy === item.id"
                  @click="resolve(item, 'change')"
                >
                  确认类型
                </button>
                <button
                  class="btn ghost sm"
                  :disabled="busy === item.id"
                  @click="resolve(item, 'confirm')"
                >
                  保持原判
                </button>
                <button
                  class="btn subtle sm"
                  :disabled="busy === item.id"
                  @click="resolve(item, 'skip')"
                >
                  忽略
                </button>
              </div>
            </div>
          </div>
        </div>
      </article>
    </div>

    <div v-else class="panel">
      <EmptyState
        icon="checkCircle"
        title="审核队列是空的"
        hint="所有识别结果都足够确定；遇到模糊邮件时会出现在这里。"
      />
    </div>
  </div>
</template>
