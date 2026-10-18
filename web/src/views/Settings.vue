<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api'
import { refreshBootstrap, store } from '../store'
import { toast } from '../toast'
import { fmtDateTime } from '../utils'
import AppIcon from '../components/AppIcon.vue'

const router = useRouter()
const settings = ref(null)
const accounts = ref([])
const meta = ref(null)
const saving = ref(false)
const adding = ref(false)
const testing = ref(false)
const testedCredentials = ref('')
const showAdvanced = ref(false)
const copied = ref(false)

const accountForm = reactive({ email: '', auth_code: '', display_name: '' })
const aiForm = reactive({
  llm_provider: 'deepseek',
  llm_model: 'deepseek-chat',
  llm_base_url: 'https://api.deepseek.com/v1',
  llm_api_key: '',
  llm_rules_only: false,
})
const scanForm = reactive({
  scan_interval_min: 15,
  scan_since_days: 90,
  notify_enabled: true,
  quiet_hours: '22:00-08:00',
})

const llmPresets = {
  deepseek: { label: 'DeepSeek', model: 'deepseek-chat', base: 'https://api.deepseek.com/v1' },
  qwen: { label: '通义千问', model: 'qwen-plus', base: 'https://dashscope.aliyuncs.com/compatible-mode/v1' },
  openai: { label: 'OpenAI', model: 'gpt-4o-mini', base: 'https://api.openai.com/v1' },
  custom: { label: '自定义 OpenAI 兼容', model: '', base: '' },
  ollama: { label: '本地 Ollama', model: 'qwen2.5:7b', base: 'http://127.0.0.1:11434/v1' },
}

const providerMeta = {
  qq: { label: 'QQ 邮箱', hint: '设置 → 账户 → 开启 IMAP/SMTP 服务，生成授权码', available: true },
  163: { label: '网易邮箱', hint: '设置 → POP3/SMTP/IMAP → 开启 IMAP/SMTP，获取客户端授权密码', available: true },
  outlook: { label: 'Outlook', hint: 'Outlook 将在二期（M5）通过 Microsoft Graph 支持', available: false },
  imap: { label: '通用 IMAP', hint: '当前先支持 QQ / 163；通用 IMAP 在后续完善', available: true },
}

const providerKey = computed(() => {
  const domain = accountForm.email.split('@')[1]?.toLowerCase() || ''
  if (['qq.com', 'foxmail.com'].includes(domain)) return 'qq'
  if (['163.com', '126.com', 'yeah.net'].includes(domain)) return '163'
  if (['outlook.com', 'hotmail.com', 'live.com', 'msn.com'].includes(domain)) return 'outlook'
  return 'imap'
})
const provider = computed(() => providerMeta[providerKey.value])

const accountProviderLabel = (key) => providerMeta[key]?.label || key

async function load() {
  try {
    const [settingsData, accountList, metaData] = await Promise.all([
      api.settings(),
      api.accounts(),
      api.meta(),
    ])
    settings.value = settingsData
    accounts.value = accountList
    meta.value = metaData
    Object.assign(aiForm, {
      llm_provider: settingsData.llm_provider,
      llm_model: settingsData.llm_model,
      llm_base_url: settingsData.llm_base_url,
      llm_rules_only: settingsData.llm_rules_only,
      llm_api_key: '',
    })
    Object.assign(scanForm, {
      scan_interval_min: settingsData.scan_interval_min,
      scan_since_days: settingsData.scan_since_days,
      notify_enabled: settingsData.notify_enabled,
      quiet_hours: settingsData.quiet_hours,
    })
  } catch (error) {
    toast(error.message, 'error')
  }
}

onMounted(load)

function onProviderChange() {
  const preset = llmPresets[aiForm.llm_provider]
  if (preset && aiForm.llm_provider !== 'custom') {
    aiForm.llm_model = preset.model
    aiForm.llm_base_url = preset.base
  }
}

async function saveAi() {
  saving.value = true
  try {
    const payload = {
      llm_provider: aiForm.llm_provider,
      llm_model: aiForm.llm_model,
      llm_base_url: aiForm.llm_base_url,
      llm_rules_only: aiForm.llm_rules_only,
    }
    if (aiForm.llm_api_key) payload.llm_api_key = aiForm.llm_api_key
    settings.value = await api.saveSettings(payload)
    aiForm.llm_api_key = ''
    toast('AI 设置已保存', 'success')
    await refreshBootstrap()
  } catch (error) {
    toast(error.message, 'error')
  } finally {
    saving.value = false
  }
}

async function clearKey() {
  try {
    settings.value = await api.saveSettings({ clear_api_key: true })
    toast('API Key 已清除', 'success')
  } catch (error) {
    toast(error.message, 'error')
  }
}

async function saveScan() {
  saving.value = true
  try {
    settings.value = await api.saveSettings({ ...scanForm })
    toast('扫描设置已保存', 'success')
    await refreshBootstrap()
  } catch (error) {
    toast(error.message, 'error')
  } finally {
    saving.value = false
  }
}

async function addAccount() {
  if (!accountForm.email.trim()) return toast('请输入邮箱地址', 'error')
  if (!provider.value.available) return toast(provider.value.hint, 'error')
  if (providerKey.value === 'imap') {
    return toast('通用 IMAP 将在后续完善，当前请使用 QQ / 163', 'error')
  }
  if (!accountForm.auth_code.trim()) return toast('请填写授权码（不是登录密码）', 'error')

  adding.value = true
  try {
    const signature = `${accountForm.email}|${accountForm.auth_code}`
    await api.addAccount({
      ...accountForm,
      verify: testedCredentials.value !== signature,
    })
    toast('邮箱已添加', 'success')
    testedCredentials.value = ''
    accountForm.email = ''
    accountForm.auth_code = ''
    accountForm.display_name = ''
    accounts.value = await api.accounts()
    await refreshBootstrap()
  } catch (error) {
    toast(error.message, 'error')
  } finally {
    adding.value = false
  }
}

async function testDraft() {
  if (!accountForm.email.trim()) return toast('请输入邮箱地址', 'error')
  if (!provider.value.available) return toast(provider.value.hint, 'error')
  if (providerKey.value === 'imap') {
    return toast('通用 IMAP 将在后续完善，当前请使用 QQ / 163', 'error')
  }
  if (!accountForm.auth_code.trim()) return toast('请填写授权码（不是登录密码）', 'error')

  testing.value = true
  try {
    const result = await api.testAccountDraft({
      email: accountForm.email,
      auth_code: accountForm.auth_code,
    })
    if (result.ok) {
      testedCredentials.value = `${accountForm.email}|${accountForm.auth_code}`
      toast(`连接成功，收件箱 ${result.messages ?? '?'} 封`, 'success')
    } else {
      toast(result.message || '连接失败', 'error')
    }
  } catch (error) {
    toast(error.message, 'error')
  } finally {
    testing.value = false
  }
}

async function testAccount(account) {
  try {
    const result = await api.testAccount(account.id)
    if (result.ok) toast(result.message || '连接成功', 'success')
    else toast(result.message || '连接失败', 'error')
  } catch (error) {
    toast(error.message, 'error')
  }
}

async function syncAccount(account) {
  try {
    const result = await api.syncAccount(account.id)
    if (result.ok) toast(result.message, 'success')
    else if (result.message && (result.message.includes('还没有添加') || result.message.includes('演示账户'))) {
      toast(result.message, 'info')
    } else {
      toast(result.message || '同步失败', 'error')
    }
    accounts.value = await api.accounts()
    await refreshBootstrap()
    store.revision += 1
  } catch (error) {
    toast(error.message, 'error')
  }
}

async function removeAccount(account) {
  if (!window.confirm(`确定移除 ${account.email}？`)) return
  try {
    await api.deleteAccount(account.id)
    accounts.value = await api.accounts()
    await refreshBootstrap()
    toast('邮箱已移除', 'success')
  } catch (error) {
    toast(error.message, 'error')
  }
}

async function exportFile(kind) {
  try {
    if (kind === 'csv') {
      await api.download('/export/csv', 'autumnmail-applications.csv')
      toast('CSV 已导出', 'success')
    } else {
      await api.download('/export/ics', 'autumnmail-interviews.ics')
      toast('日历文件已导出', 'success')
    }
  } catch (error) {
    toast(error.message, 'error')
  }
}

async function resetDemo() {
  if (!window.confirm('将清空当前数据并恢复演示数据，确定继续？')) return
  try {
    await api.resetDemo()
    await refreshBootstrap()
    await load()
    toast('演示数据已重置', 'success')
    store.revision += 1
  } catch (error) {
    toast(error.message, 'error')
  }
}

async function restartWizard() {
  try {
    await api.saveSettings({ onboarded: false })
    await refreshBootstrap()
    router.push('/onboarding')
  } catch (error) {
    toast(error.message, 'error')
  }
}

async function copyDataDir() {
  try {
    await navigator.clipboard.writeText(meta.value?.data_dir || '')
    copied.value = true
    setTimeout(() => (copied.value = false), 1600)
    toast('数据目录已复制', 'success')
  } catch {
    toast('复制失败，请手动选择路径', 'error')
  }
}
</script>

<template>
  <div v-if="settings" class="page">
    <section class="section">
      <header class="section-head">
        <h3><AppIcon name="mail" :size="17" /> 邮箱账户</h3>
        <p>QQ / 163 使用授权码，只读连接。授权码只保存在本机；解析与事件生成在 M2 接入。</p>
      </header>
      <div class="section-body">
        <div v-if="accounts.length">
          <div v-for="account in accounts" :key="account.id" class="account-row">
            <div class="avatar">{{ account.email.slice(0, 1).toUpperCase() }}</div>
            <div class="account-info">
              <div class="account-email">{{ account.email }}</div>
              <div class="account-meta">
                {{ accountProviderLabel(account.provider) }}，{{ account.message_count || 0 }} 封邮件，{{
                  account.last_sync_at ? `上次同步 ${fmtDateTime(account.last_sync_at)}` : '尚未同步'
                }}
              </div>
            </div>
            <span class="provider-tag">{{ accountProviderLabel(account.provider) }}</span>
            <button class="btn ghost sm" @click="testAccount(account)">测试</button>
            <button class="btn ghost sm" @click="syncAccount(account)">同步</button>
            <button class="btn subtle sm" @click="removeAccount(account)">
              <AppIcon name="trash" :size="14" />
            </button>
          </div>
        </div>
        <div v-else class="notice">
          <AppIcon name="alert" :size="16" />
          <span>还没有邮箱。添加 QQ 或 163 邮箱后即可开始扫描。</span>
        </div>

        <div class="form-grid">
          <div class="field">
            <label>邮箱地址</label>
            <input v-model="accountForm.email" class="input" placeholder="you@qq.com" />
          </div>
          <div class="field">
            <label>授权码</label>
            <input
              v-model="accountForm.auth_code"
              class="input"
              type="password"
              placeholder="邮箱后台生成的授权码"
            />
          </div>
          <div class="field full">
            <div class="notice" :class="{ warn: accountForm.email && !provider.available }">
              <AppIcon name="shield" :size="16" />
              <span v-if="accountForm.email">
                <strong>{{ provider.label }}</strong> · {{ provider.hint }}
              </span>
              <span v-else>输入邮箱地址后，会自动识别服务商并填好 IMAP 服务器。</span>
            </div>
          </div>
        </div>

        <div class="inline">
          <button class="btn ghost" :disabled="testing" @click="testDraft">
            {{ testing ? '连接中…' : '测试连接' }}
          </button>
          <button class="btn primary" :disabled="adding" @click="addAccount">
            <AppIcon name="plus" :size="16" />
            {{ adding ? '添加中…' : '添加邮箱' }}
          </button>
          <span class="muted" style="font-size: 11.5px">添加前会测试 IMAP；只读拉取，不会标记已读。</span>
        </div>
      </div>
    </section>

    <section class="section">
      <header class="section-head">
        <h3><AppIcon name="brain" :size="17" /> AI 解析</h3>
        <p>规则引擎离线可用；大模型只处理规则不确定的邮件。</p>
      </header>
      <div class="section-body">
        <div class="form-grid">
          <div class="field">
            <label>服务商</label>
            <select v-model="aiForm.llm_provider" class="select" @change="onProviderChange">
              <option v-for="(preset, key) in llmPresets" :key="key" :value="key">
                {{ preset.label }}
              </option>
            </select>
          </div>
          <div class="field">
            <label>模型</label>
            <input v-model="aiForm.llm_model" class="input" placeholder="deepseek-chat" />
          </div>
          <div class="field full">
            <label>
              API Key
              <span v-if="settings.llm_api_key_set" class="provider-tag" style="margin-left: 6px">
                已保存 {{ settings.llm_api_key_preview }}
              </span>
            </label>
            <input
              v-model="aiForm.llm_api_key"
              class="input"
              type="password"
              :placeholder="settings.llm_api_key_set ? '留空则不修改已保存的 Key' : 'sk-...'"
            />
            <span class="hint">Key 使用 Windows DPAPI 加密，只对当前 Windows 用户可解密。</span>
          </div>
          <div v-if="showAdvanced" class="field full">
            <label>Base URL</label>
            <input v-model="aiForm.llm_base_url" class="input" placeholder="https://api.deepseek.com/v1" />
            <span class="hint">任何 OpenAI 兼容端点都可以，包括本地 Ollama。</span>
          </div>
        </div>

        <div class="inline">
          <label class="switch">
            <input v-model="aiForm.llm_rules_only" type="checkbox" />
            仅使用规则引擎（不调用大模型）
          </label>
          <button class="btn link" @click="showAdvanced = !showAdvanced">
            {{ showAdvanced ? '收起高级设置' : '高级设置' }}
          </button>
          <button v-if="settings.llm_api_key_set" class="btn link" @click="clearKey">
            清除 Key
          </button>
        </div>

        <div class="inline">
          <button class="btn primary" :disabled="saving" @click="saveAi">
            {{ saving ? '保存中…' : '保存 AI 设置' }}
          </button>
        </div>
      </div>
    </section>

    <section class="section">
      <header class="section-head">
        <h3><AppIcon name="refresh" :size="17" /> 扫描与通知</h3>
        <p>应用在后台按间隔增量拉取，不需要系统计划任务。</p>
      </header>
      <div class="section-body">
        <div class="form-grid">
          <div class="field">
            <label>扫描间隔（分钟）</label>
            <input v-model.number="scanForm.scan_interval_min" class="input" type="number" min="1" max="1440" />
          </div>
          <div class="field">
            <label>首次回看天数</label>
            <input v-model.number="scanForm.scan_since_days" class="input" type="number" min="1" max="365" />
          </div>
          <div class="field">
            <label>免打扰时段</label>
            <input v-model="scanForm.quiet_hours" class="input" placeholder="22:00-08:00" />
          </div>
          <div class="field" style="justify-content: flex-end">
            <label class="switch">
              <input v-model="scanForm.notify_enabled" type="checkbox" />
              开启桌面通知
            </label>
          </div>
        </div>
        <div class="inline">
          <button class="btn primary" :disabled="saving" @click="saveScan">
            {{ saving ? '保存中…' : '保存扫描设置' }}
          </button>
        </div>
      </div>
    </section>

    <section class="section">
      <header class="section-head">
        <h3><AppIcon name="database" :size="17" /> 数据与隐私</h3>
        <p>所有邮件索引、事件和反馈都在本机 SQLite 中，不上传云端。</p>
      </header>
      <div class="section-body">
        <div class="field">
          <label>本地数据目录</label>
          <div class="inline">
            <input class="input" :value="meta?.data_dir" readonly />
            <button class="btn ghost sm" @click="copyDataDir">
              {{ copied ? '已复制' : '复制路径' }}
            </button>
          </div>
        </div>

        <div class="inline">
          <button class="btn ghost" @click="exportFile('csv')">
            <AppIcon name="download" :size="15" /> 导出 CSV
          </button>
          <button class="btn ghost" @click="exportFile('ics')">
            <AppIcon name="calendar" :size="15" /> 导出 .ics
          </button>
          <button class="btn subtle" @click="resetDemo">重置演示数据</button>
          <button class="btn subtle" @click="restartWizard">重新体验首次向导</button>
        </div>

        <div class="notice">
          <AppIcon name="shield" :size="16" />
          <span>
            本地 API 只监听 127.0.0.1，并用随机令牌校验；授权码/API Key 不会写入日志或导出文件。
          </span>
        </div>
      </div>
    </section>

    <section class="section">
      <header class="section-head">
        <h3><AppIcon name="sparkles" :size="17" /> 关于</h3>
      </header>
      <div class="section-body">
        <div class="summary-list">
          <div class="summary-row"><span>版本</span><strong>v{{ meta?.version }}</strong></div>
          <div class="summary-row"><span>当前阶段</span><strong>M1 · 真实 IMAP 接入（只读）</strong></div>
          <div class="summary-row"><span>已支持邮箱</span><strong>QQ / 163；Outlook 二期</strong></div>
          <div class="summary-row"><span>下一步</span><strong>M2 · 中文秋招解析与事件生成</strong></div>
        </div>
        <p class="muted" style="font-size: 11.5px; line-height: 1.6; margin: 0">
          秋信（AutumnMail）是一个本地优先的秋招邮件助手。M0 目标是打通桌面壳、本地服务、SQLite 与完整 UI；
          真实邮箱读取与中文秋招解析将在 M1/M2 接入。
        </p>
      </div>
    </section>
  </div>

  <div v-else class="panel">
    <div class="empty"><p>正在加载设置…</p></div>
  </div>
</template>
