<script setup>
import { computed, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api'
import { refreshBootstrap } from '../store'
import { toast } from '../toast'
import AppIcon from '../components/AppIcon.vue'

const router = useRouter()
const step = ref(1)
const busy = ref(false)
const added = ref(null)
const showAdvanced = ref(false)

const form = reactive({
  email: '',
  auth_code: '',
  llm_provider: 'deepseek',
  llm_model: 'deepseek-chat',
  llm_base_url: 'https://api.deepseek.com/v1',
  llm_api_key: '',
  scan_interval_min: 15,
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

const steps = [
  { id: 1, title: '添加邮箱', subtitle: 'QQ / 163 授权码' },
  { id: 2, title: '配置 AI', subtitle: '默认 DeepSeek' },
  { id: 3, title: '开始扫描', subtitle: '确认并进入仪表盘' },
]

const providerKey = computed(() => {
  const domain = form.email.split('@')[1]?.toLowerCase() || ''
  if (['qq.com', 'foxmail.com'].includes(domain)) return 'qq'
  if (['163.com', '126.com', 'yeah.net'].includes(domain)) return '163'
  if (['outlook.com', 'hotmail.com', 'live.com', 'msn.com'].includes(domain)) return 'outlook'
  return 'imap'
})
const provider = computed(() => providerMeta[providerKey.value])

function onProviderChange() {
  const preset = llmPresets[form.llm_provider]
  if (preset && form.llm_provider !== 'custom') {
    form.llm_model = preset.model
    form.llm_base_url = preset.base
  }
}

async function addMailbox() {
  if (!form.email.trim()) return toast('请输入邮箱地址', 'error')
  if (!provider.value.available) return toast(provider.value.hint, 'error')
  if (providerKey.value === 'imap') {
    return toast('当前先支持 QQ / 163，通用 IMAP 在后续完善', 'error')
  }
  if (!form.auth_code.trim()) return toast('请填写授权码（不是登录密码）', 'error')

  busy.value = true
  try {
    const test = await api.testAccountDraft({
      email: form.email,
      auth_code: form.auth_code,
    })
    if (!test.ok) {
      toast(test.message || '连接失败', 'error')
      return
    }
    added.value = await api.addAccount({
      email: form.email,
      auth_code: form.auth_code,
      verify: false,
    })
    await refreshBootstrap()
    toast(`连接成功，已添加 ${added.value.email}`, 'success')
    step.value = 2
  } catch (error) {
    toast(error.message, 'error')
  } finally {
    busy.value = false
  }
}

async function saveAi() {
  busy.value = true
  try {
    const payload = {
      llm_provider: form.llm_provider,
      llm_model: form.llm_model,
      llm_base_url: form.llm_base_url,
      llm_rules_only: false,
    }
    if (form.llm_api_key) payload.llm_api_key = form.llm_api_key
    await api.saveSettings(payload)
    toast('AI 设置已保存', 'success')
    step.value = 3
  } catch (error) {
    toast(error.message, 'error')
  } finally {
    busy.value = false
  }
}

async function skipAi() {
  busy.value = true
  try {
    await api.saveSettings({ llm_rules_only: true })
    toast('已切换为仅规则模式，可随时在设置里补充', 'success')
    step.value = 3
  } catch (error) {
    toast(error.message, 'error')
  } finally {
    busy.value = false
  }
}

async function finish() {
  busy.value = true
  try {
    await api.saveSettings({ onboarded: true, scan_interval_min: form.scan_interval_min })
    await refreshBootstrap()
    toast('配置完成，欢迎使用秋信', 'success')
    router.push('/')
  } catch (error) {
    toast(error.message, 'error')
  } finally {
    busy.value = false
  }
}

async function useDemo() {
  busy.value = true
  try {
    await api.saveSettings({ onboarded: true })
    await refreshBootstrap()
    toast('已进入演示数据', 'success')
    router.push('/')
  } catch (error) {
    toast(error.message, 'error')
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="wizard-card">
    <aside class="wizard-aside">
      <div>
        <div class="brand-mark" style="margin-bottom: 16px">
          <AppIcon name="mail" :size="20" />
        </div>
        <h2>秋信</h2>
        <p>把秋招的每一封信，变成清晰的下一步。</p>
      </div>

      <div class="steps">
        <div
          v-for="item in steps"
          :key="item.id"
          class="step"
          :class="{ active: step === item.id, done: step > item.id }"
        >
          <div class="step-dot">
            <AppIcon v-if="step > item.id" name="check" :size="13" />
            <template v-else>{{ item.id }}</template>
          </div>
          <div class="step-text">
            <strong>{{ item.title }}</strong>
            <span>{{ item.subtitle }}</span>
          </div>
        </div>
      </div>

      <div style="margin-top: auto; font-size: 11px; color: #64748b; line-height: 1.7">
        <div>本地数据 · 只读邮件</div>
        <div>不上传邮箱内容</div>
      </div>
    </aside>

    <div class="wizard-body">
      <template v-if="step === 1">
        <h3>先连上你的邮箱</h3>
        <p class="lead">
          输入邮箱地址，我们会自动识别服务商。QQ / 163 需要开启 IMAP 并填写授权码。
        </p>

        <div class="wizard-content">
          <div class="field">
            <label>邮箱地址</label>
            <input v-model="form.email" class="input" placeholder="you@qq.com" autofocus />
          </div>

          <div class="notice" :class="{ warn: form.email && !provider.available }">
            <AppIcon name="shield" :size="16" />
            <span v-if="form.email"><strong>{{ provider.label }}</strong> · {{ provider.hint }}</span>
            <span v-else>输入邮箱地址后，会自动识别服务商并填好 IMAP 服务器。</span>
          </div>

          <div class="field">
            <label>授权码</label>
            <input
              v-model="form.auth_code"
              class="input"
              type="password"
              placeholder="不是登录密码"
            />
            <span class="hint">授权码可在邮箱「设置 → 账户」中生成，只保存在本机。</span>
          </div>

          <div class="notice">
            <AppIcon name="shield" :size="16" />
            <span>添加前会测试 IMAP 连接；只读拉取，不会标记已读或删除邮件。</span>
          </div>
        </div>

        <div class="wizard-actions">
          <button class="btn link" @click="useDemo">先看演示数据</button>
          <button class="btn primary" :disabled="busy" @click="addMailbox">
            {{ busy ? '验证中…' : '下一步' }}
            <AppIcon name="chevronRight" :size="15" />
          </button>
        </div>
      </template>

      <template v-else-if="step === 2">
        <h3>选择用于解析的 AI</h3>
        <p class="lead">
          规则引擎会先处理明确的邮件；只有模糊的才会交给大模型。默认 DeepSeek。
        </p>

        <div class="wizard-content">
          <div class="form-grid">
            <div class="field">
              <label>服务商</label>
              <select v-model="form.llm_provider" class="select" @change="onProviderChange">
                <option v-for="(preset, key) in llmPresets" :key="key" :value="key">
                  {{ preset.label }}
                </option>
              </select>
            </div>
            <div class="field">
              <label>模型</label>
              <input v-model="form.llm_model" class="input" placeholder="deepseek-chat" />
            </div>
            <div class="field full">
              <label>API Key</label>
              <input
                v-model="form.llm_api_key"
                class="input"
                type="password"
                placeholder="sk-..."
              />
              <span class="hint">留空可先使用规则模式，之后在设置里补充。</span>
            </div>
            <div v-if="showAdvanced" class="field full">
              <label>Base URL</label>
              <input v-model="form.llm_base_url" class="input" />
            </div>
          </div>

          <div class="inline">
            <button class="btn link" @click="showAdvanced = !showAdvanced">
              {{ showAdvanced ? '收起高级设置' : '高级设置' }}
            </button>
          </div>
        </div>

        <div class="wizard-actions">
          <button class="btn ghost" @click="step = 1">上一步</button>
          <div class="inline">
            <button class="btn subtle" :disabled="busy" @click="skipAi">仅用规则</button>
            <button class="btn primary" :disabled="busy" @click="saveAi">
              {{ busy ? '保存中…' : '下一步' }}
            </button>
          </div>
        </div>
      </template>

      <template v-else>
        <h3>一切就绪</h3>
        <p class="lead">
          确认下面的配置，点击开始后应用会在后台增量扫描。M0 会先展示演示数据。
        </p>

        <div class="wizard-content">
          <div class="summary-list">
            <div class="summary-row">
              <span>邮箱</span>
              <strong>{{ added?.email || form.email || '演示邮箱' }}</strong>
            </div>
            <div class="summary-row">
              <span>服务商</span>
              <strong>{{ provider.label }}</strong>
            </div>
            <div class="summary-row">
              <span>AI</span>
              <strong>{{ llmPresets[form.llm_provider]?.label }}</strong>
            </div>
            <div class="summary-row">
              <span>扫描间隔</span>
              <strong>每 {{ form.scan_interval_min }} 分钟</strong>
            </div>
          </div>

          <div class="notice">
            <AppIcon name="shield" :size="16" />
            <span>邮件只读，不会标记已读或删除。所有解析结果保存在本机 SQLite。</span>
          </div>
        </div>

        <div class="wizard-actions">
          <button class="btn ghost" @click="step = 2">上一步</button>
          <button class="btn primary" :disabled="busy" @click="finish">
            {{ busy ? '准备中…' : '开始使用' }}
            <AppIcon name="chevronRight" :size="15" />
          </button>
        </div>
      </template>
    </div>
  </div>
</template>
