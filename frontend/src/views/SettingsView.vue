<template>
  <div class="container">
    <div class="page-header">
      <h1 class="page-title">系统设置</h1>
      <p class="page-subtitle">配置文本生成和图片生成的 API 服务</p>
    </div>

    <div v-if="loading" class="loading-container">
      <div class="spinner"></div>
      <p>加载配置中...</p>
    </div>

    <div v-else class="settings-container">
      <!-- 文本生成配置 -->
      <div class="card">
        <div class="section-header">
          <div>
            <h2 class="section-title">文本生成配置</h2>
            <p class="section-desc">用于生成小红书图文大纲</p>
          </div>
          <button class="btn btn-small" @click="openAddTextProviderModal">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="12" y1="5" x2="12" y2="19"></line>
              <line x1="5" y1="12" x2="19" y2="12"></line>
            </svg>
            添加
          </button>
        </div>

        <!-- 服务商列表表格 -->
        <div class="provider-table">
          <div class="table-header">
            <div class="col-status">状态</div>
            <div class="col-name">名称</div>
            <div class="col-model">模型</div>
            <div class="col-apikey">API Key</div>
            <div class="col-actions">操作</div>
          </div>
          <div
            v-for="(provider, name) in textConfig.providers"
            :key="name"
            class="table-row"
            :class="{ active: textConfig.active_provider === name }"
          >
            <div class="col-status">
              <button
                class="btn-activate"
                :class="{ active: textConfig.active_provider === name }"
                @click="activateTextProvider(name as string)"
                :disabled="textConfig.active_provider === name"
              >
                {{ textConfig.active_provider === name ? '已激活' : '激活' }}
              </button>
            </div>
            <div class="col-name">
              <span class="provider-name">{{ name }}</span>
            </div>
            <div class="col-model">
              <span class="model-name">{{ provider.model }}</span>
            </div>
            <div class="col-apikey">
              <span class="apikey-masked" :class="{ empty: !provider.api_key_masked }">
                {{ provider.api_key_masked || '未配置' }}
              </span>
            </div>
            <div class="col-actions">
              <button class="btn-icon" @click="testTextProviderInList(name as string, provider)" title="测试连接">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline>
                </svg>
              </button>
              <button class="btn-icon" @click="openEditTextProviderModal(name as string, provider)" title="编辑">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
                  <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
                </svg>
              </button>
              <button
                class="btn-icon danger"
                @click="deleteTextProvider(name as string)"
                v-if="Object.keys(textConfig.providers).length > 1"
                title="删除"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <polyline points="3 6 5 6 21 6"></polyline>
                  <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                </svg>
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- 图片生成配置 -->
      <div class="card">
        <div class="section-header">
          <div>
            <h2 class="section-title">图片生成配置</h2>
            <p class="section-desc">用于生成小红书配图</p>
          </div>
          <button class="btn btn-small" @click="openAddImageProviderModal">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="12" y1="5" x2="12" y2="19"></line>
              <line x1="5" y1="12" x2="19" y2="12"></line>
            </svg>
            添加
          </button>
        </div>

        <!-- 服务商列表表格 -->
        <div class="provider-table">
          <div class="table-header">
            <div class="col-status">状态</div>
            <div class="col-name">名称</div>
            <div class="col-model">模型</div>
            <div class="col-apikey">API Key</div>
            <div class="col-actions">操作</div>
          </div>
          <div
            v-for="(provider, name) in imageConfig.providers"
            :key="name"
            class="table-row"
            :class="{ active: imageConfig.active_provider === name }"
          >
            <div class="col-status">
              <button
                class="btn-activate"
                :class="{ active: imageConfig.active_provider === name }"
                @click="activateImageProvider(name as string)"
                :disabled="imageConfig.active_provider === name"
              >
                {{ imageConfig.active_provider === name ? '已激活' : '激活' }}
              </button>
            </div>
            <div class="col-name">
              <span class="provider-name">{{ name }}</span>
            </div>
            <div class="col-model">
              <span class="model-name">{{ provider.model }}</span>
            </div>
            <div class="col-apikey">
              <span class="apikey-masked" :class="{ empty: !provider.api_key_masked }">
                {{ provider.api_key_masked || '未配置' }}
              </span>
            </div>
            <div class="col-actions">
              <button class="btn-icon" @click="testImageProviderInList(name as string, provider)" title="测试连接">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline>
                </svg>
              </button>
              <button class="btn-icon" @click="openEditImageProviderModal(name as string, provider)" title="编辑">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
                  <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
                </svg>
              </button>
              <button
                class="btn-icon danger"
                @click="deleteImageProvider(name as string)"
                v-if="Object.keys(imageConfig.providers).length > 1"
                title="删除"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <polyline points="3 6 5 6 21 6"></polyline>
                  <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                </svg>
              </button>
            </div>
          </div>
        </div>
      </div>

    </div>

    <!-- 编辑/添加文本生成服务商弹窗 -->
    <div v-if="showTextProviderModal" class="modal-overlay">
      <div class="modal-content">
        <div class="modal-header">
          <h3>{{ editingTextProvider ? '编辑服务商' : '添加服务商' }}</h3>
          <button class="close-btn" @click="closeTextProviderModal">×</button>
        </div>
        <div class="modal-body">
          <div class="form-group" v-if="!editingTextProvider">
            <label>服务商名称</label>
            <input
              type="text"
              class="form-input"
              v-model="textProviderForm.name"
              placeholder="例如: openai"
            />
            <span class="form-hint">唯一标识，用于区分不同服务商</span>
          </div>
          <div class="form-group">
            <label>类型</label>
            <select class="form-select" v-model="textProviderForm.type">
              <option value="google_gemini">Google Gemini</option>
              <option value="openai_compatible">OpenAI 兼容接口</option>
            </select>
          </div>
          <div class="form-group">
            <label>API Key</label>
            <input
              type="text"
              class="form-input"
              v-model="textProviderForm.api_key"
              :placeholder="editingTextProvider && textProviderForm._has_api_key ? textProviderForm.api_key_masked : '输入 API Key'"
            />
            <span class="form-hint" v-if="editingTextProvider && hasExistingApiKey(textProviderForm)">已配置 API Key，留空表示不修改</span>
          </div>
          <div class="form-group" v-if="textProviderForm.type === 'openai_compatible'">
            <label>Base URL</label>
            <input
              type="text"
              class="form-input"
              v-model="textProviderForm.base_url"
              placeholder="例如: https://api.openai.com"
            />
            <span class="form-hint" v-if="textProviderForm.base_url">
              预览: {{ textProviderForm.base_url.replace(/\/$/, '').replace(/\/v1$/, '') }}/v1/chat/completions
            </span>
          </div>
          <div class="form-group">
            <label>模型</label>
            <input
              type="text"
              class="form-input"
              v-model="textProviderForm.model"
              placeholder="例如: gpt-4o"
            />
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn" @click="testTextConnection" :disabled="testingText">
            {{ testingText ? '测试中...' : '测试连接' }}
          </button>
          <button class="btn" @click="closeTextProviderModal">取消</button>
          <button class="btn btn-primary" @click="saveTextProvider">
            {{ editingTextProvider ? '保存' : '添加' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 编辑/添加图片生成服务商弹窗 -->
    <div v-if="showImageProviderModal" class="modal-overlay">
      <div class="modal-content">
        <div class="modal-header">
          <h3>{{ editingImageProvider ? '编辑服务商' : '添加服务商' }}</h3>
          <button class="close-btn" @click="closeImageProviderModal">×</button>
        </div>
        <div class="modal-body">
          <div class="form-group" v-if="!editingImageProvider">
            <label>服务商名称</label>
            <input
              type="text"
              class="form-input"
              v-model="imageProviderForm.name"
              placeholder="例如: google_genai"
            />
            <span class="form-hint">唯一标识，用于区分不同服务商</span>
          </div>
          <div class="form-group">
            <label>类型</label>
            <select class="form-select" v-model="imageProviderForm.type">
              <option value="google_genai">Google GenAI</option>
              <option value="image_api">OpenAI 兼容接口</option>
            </select>
          </div>
          <div class="form-group">
            <label>API Key</label>
            <input
              type="text"
              class="form-input"
              v-model="imageProviderForm.api_key"
              :placeholder="editingImageProvider && imageProviderForm._has_api_key ? imageProviderForm.api_key_masked : '输入 API Key'"
            />
            <span class="form-hint" v-if="editingImageProvider && hasExistingApiKey(imageProviderForm)">已配置 API Key，留空表示不修改</span>
          </div>
          <div class="form-group" v-if="imageProviderForm.type === 'image_api'">
            <label>Base URL</label>
            <input
              type="text"
              class="form-input"
              v-model="imageProviderForm.base_url"
              placeholder="例如: https://api.openai.com"
            />
            <span class="form-hint" v-if="imageProviderForm.base_url">
              预览: {{ imageProviderForm.base_url.replace(/\/$/, '').replace(/\/v1$/, '') }}/v1/images/generations
            </span>
          </div>
          <div class="form-group">
            <label>模型</label>
            <input
              type="text"
              class="form-input"
              v-model="imageProviderForm.model"
              placeholder="例如: gemini-3-pro-image-preview"
            />
          </div>
          <div class="form-group">
            <label class="toggle-label">
              <span>高并发模式</span>
              <div class="toggle-switch" :class="{ active: imageProviderForm.high_concurrency }" @click="imageProviderForm.high_concurrency = !imageProviderForm.high_concurrency">
                <div class="toggle-slider"></div>
              </div>
            </label>
            <span class="form-hint">启用后将并行生成图片，速度更快但对 API 质量要求较高。GCP 300$ 试用账号不建议启用。</span>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn" @click="testImageConnection" :disabled="testingImage">
            {{ testingImage ? '测试中...' : '测试连接' }}
          </button>
          <button class="btn" @click="closeImageProviderModal">取消</button>
          <button class="btn btn-primary" @click="saveImageProvider">
            {{ editingImageProvider ? '保存' : '添加' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getConfig, updateConfig, testConnection, type Config } from '../api'

const loading = ref(true)
const saving = ref(false)
const testingText = ref(false)
const testingImage = ref(false)

// 文本生成配置
const textConfig = ref<{
  active_provider: string
  providers: Record<string, any>
}>({
  active_provider: '',
  providers: {}
})

// 图片生成配置
const imageConfig = ref<{
  active_provider: string
  providers: Record<string, any>
}>({
  active_provider: '',
  providers: {}
})

// 文本服务商弹窗
const showTextProviderModal = ref(false)
const editingTextProvider = ref<string | null>(null)
const textProviderForm = ref({
  name: '',
  type: 'openai_compatible',
  api_key: '',
  api_key_masked: '',
  base_url: '',
  model: '',
  _has_api_key: false
})

// 图片服务商弹窗
const showImageProviderModal = ref(false)
const editingImageProvider = ref<string | null>(null)
const imageProviderForm = ref({
  name: '',
  type: '',
  api_key: '',
  api_key_masked: '',
  base_url: '',
  model: '',
  high_concurrency: false,
  _has_api_key: false
})

// 类型标签映射
function getTypeLabel(type: string): string {
  const labels: Record<string, string> = {
    'google_gemini': 'Gemini',
    'openai_compatible': 'OpenAI',
    'google_genai': 'Google GenAI'
  }
  return labels[type] || type
}

// 检查是否已有 API Key
function hasExistingApiKey(form: any): boolean {
  return form._has_api_key === true
}

// 加载配置
async function loadConfig() {
  loading.value = true
  try {
    const result = await getConfig()
    if (result.success && result.config) {
      textConfig.value = {
        active_provider: result.config.text_generation.active_provider,
        providers: result.config.text_generation.providers
      }
      imageConfig.value = result.config.image_generation
    } else {
      alert('加载配置失败: ' + (result.error || '未知错误'))
    }
  } catch (e) {
    alert('加载配置失败: ' + String(e))
  } finally {
    loading.value = false
  }
}

// 保存配置
async function saveConfig() {
  saving.value = true
  try {
    const config: Partial<Config> = {
      text_generation: {
        active_provider: textConfig.value.active_provider,
        providers: textConfig.value.providers
      },
      image_generation: imageConfig.value
    }

    const result = await updateConfig(config)
    if (result.success) {
      alert(result.message || '配置已保存')
    } else {
      alert('保存失败: ' + (result.error || '未知错误'))
    }
  } catch (e) {
    alert('保存失败: ' + String(e))
  } finally {
    saving.value = false
  }
}

// 激活文本服务商
async function activateTextProvider(name: string) {
  textConfig.value.active_provider = name
  await autoSaveConfig()
}

// 激活图片服务商
async function activateImageProvider(name: string) {
  imageConfig.value.active_provider = name
  await autoSaveConfig()
}

// 自动保存配置
async function autoSaveConfig() {
  try {
    const config: Partial<Config> = {
      text_generation: {
        active_provider: textConfig.value.active_provider,
        providers: textConfig.value.providers
      },
      image_generation: imageConfig.value
    }

    const result = await updateConfig(config)
    if (result.success) {
      // 重新加载配置以获取最新的脱敏 API Key
      await loadConfig()
    }
  } catch (e) {
    console.error('自动保存失败:', e)
  }
}

// 打开添加文本服务商弹窗
function openAddTextProviderModal() {
  editingTextProvider.value = null
  textProviderForm.value = {
    name: '',
    type: 'openai_compatible',
    api_key: '',
    base_url: '',
    model: '',
    _has_api_key: false
  }
  showTextProviderModal.value = true
}

// 打开编辑文本服务商弹窗
function openEditTextProviderModal(name: string, provider: any) {
  editingTextProvider.value = name
  textProviderForm.value = {
    name: name,
    type: provider.type || 'openai_compatible',
    api_key: '',
    api_key_masked: provider.api_key_masked || '',
    base_url: provider.base_url || '',
    model: provider.model || '',
    _has_api_key: !!provider.api_key_masked
  }
  showTextProviderModal.value = true
}

// 关闭文本服务商弹窗
function closeTextProviderModal() {
  showTextProviderModal.value = false
  editingTextProvider.value = null
}

// 保存文本服务商
async function saveTextProvider() {
  const name = editingTextProvider.value || textProviderForm.value.name

  if (!name) {
    alert('请填写服务商名称')
    return
  }

  if (!textProviderForm.value.type) {
    alert('请选择服务商类型')
    return
  }

  // 新增时必须填写 API Key
  if (!editingTextProvider.value && !textProviderForm.value.api_key) {
    alert('请填写 API Key')
    return
  }

  const existingProvider = textConfig.value.providers[name] || {}

  const providerData: any = {
    type: textProviderForm.value.type,
    model: textProviderForm.value.model
  }

  // 如果填写了新的 API Key，使用新的；否则保留原有的
  if (textProviderForm.value.api_key) {
    providerData.api_key = textProviderForm.value.api_key
  } else if (existingProvider.api_key) {
    providerData.api_key = existingProvider.api_key
  }

  if (textProviderForm.value.base_url) {
    providerData.base_url = textProviderForm.value.base_url
  }

  textConfig.value.providers[name] = providerData

  closeTextProviderModal()
  await autoSaveConfig()
}

// 删除文本服务商
async function deleteTextProvider(name: string) {
  if (confirm(`确定要删除服务商 "${name}" 吗？`)) {
    delete textConfig.value.providers[name]
    if (textConfig.value.active_provider === name) {
      textConfig.value.active_provider = ''
    }
    await autoSaveConfig()
  }
}

// 打开添加图片服务商弹窗
function openAddImageProviderModal() {
  editingImageProvider.value = null
  imageProviderForm.value = {
    name: '',
    type: 'image_api',
    api_key: '',
    base_url: '',
    model: '',
    high_concurrency: false,
    _has_api_key: false
  }
  showImageProviderModal.value = true
}

// 打开编辑图片服务商弹窗
function openEditImageProviderModal(name: string, provider: any) {
  editingImageProvider.value = name
  imageProviderForm.value = {
    name: name,
    type: provider.type || '',
    api_key: '',
    api_key_masked: provider.api_key_masked || '',
    base_url: provider.base_url || '',
    model: provider.model || '',
    high_concurrency: provider.high_concurrency || false,
    _has_api_key: !!provider.api_key_masked
  }
  showImageProviderModal.value = true
}

// 关闭图片服务商弹窗
function closeImageProviderModal() {
  showImageProviderModal.value = false
  editingImageProvider.value = null
}

// 保存图片服务商
async function saveImageProvider() {
  const name = editingImageProvider.value || imageProviderForm.value.name

  if (!name) {
    alert('请填写服务商名称')
    return
  }

  if (!imageProviderForm.value.type) {
    alert('请填写服务商类型')
    return
  }

  // 新增时必须填写 API Key
  if (!editingImageProvider.value && !imageProviderForm.value.api_key) {
    alert('请填写 API Key')
    return
  }

  const existingProvider = imageConfig.value.providers[name] || {}

  const providerData: any = {
    type: imageProviderForm.value.type,
    model: imageProviderForm.value.model,
    high_concurrency: imageProviderForm.value.high_concurrency
  }

  // 如果填写了新的 API Key，使用新的；否则保留原有的
  if (imageProviderForm.value.api_key) {
    providerData.api_key = imageProviderForm.value.api_key
  } else if (existingProvider.api_key) {
    providerData.api_key = existingProvider.api_key
  }

  if (imageProviderForm.value.base_url) {
    providerData.base_url = imageProviderForm.value.base_url
  }

  imageConfig.value.providers[name] = providerData

  closeImageProviderModal()
  await autoSaveConfig()
}

// 删除图片服务商
async function deleteImageProvider(name: string) {
  if (confirm(`确定要删除服务商 "${name}" 吗？`)) {
    delete imageConfig.value.providers[name]
    if (imageConfig.value.active_provider === name) {
      imageConfig.value.active_provider = ''
    }
    await autoSaveConfig()
  }
}

// 测试文本服务商连接
async function testTextConnection() {
  if (!textProviderForm.value.api_key) {
    alert('请先填写 API Key')
    return
  }
  testingText.value = true
  try {
    const result = await testConnection({
      type: textProviderForm.value.type,
      api_key: textProviderForm.value.api_key,
      base_url: textProviderForm.value.base_url,
      model: textProviderForm.value.model
    })
    if (result.success) {
      alert('✅ 连接成功！')
    }
  } catch (e: any) {
    alert('❌ 连接失败：' + (e.response?.data?.error || e.message))
  } finally {
    testingText.value = false
  }
}

// 测试图片服务商连接
async function testImageConnection() {
  if (!imageProviderForm.value.api_key) {
    alert('请先填写 API Key')
    return
  }
  testingImage.value = true
  try {
    const result = await testConnection({
      type: imageProviderForm.value.type,
      api_key: imageProviderForm.value.api_key,
      base_url: imageProviderForm.value.base_url,
      model: imageProviderForm.value.model
    })
    if (result.success) {
      alert('✅ 连接成功！')
    }
  } catch (e: any) {
    alert('❌ 连接失败：' + (e.response?.data?.error || e.message))
  } finally {
    testingImage.value = false
  }
}

// 测试列表中的文本服务商
async function testTextProviderInList(name: string, provider: any) {
  try {
    const result = await testConnection({
      type: provider.type,
      api_key: provider.api_key || textConfig.value.providers[name].api_key,
      base_url: provider.base_url,
      model: provider.model
    })
    if (result.success) {
      alert('✅ 连接成功！')
    }
  } catch (e: any) {
    alert('❌ 连接失败：' + (e.response?.data?.error || e.message))
  }
}

// 测试列表中的图片服务商
async function testImageProviderInList(name: string, provider: any) {
  try {
    const result = await testConnection({
      type: provider.type,
      api_key: provider.api_key || imageConfig.value.providers[name].api_key,
      base_url: provider.base_url,
      model: provider.model
    })
    if (result.success) {
      alert('✅ 连接成功！')
    }
  } catch (e: any) {
    alert('❌ 连接失败：' + (e.response?.data?.error || e.message))
  }
}

onMounted(() => {
  loadConfig()
})
</script>

<style scoped>
.settings-container {
  max-width: 900px;
  margin: 0 auto;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 20px;
}

.section-title {
  font-size: 18px;
  font-weight: 600;
  margin-bottom: 4px;
  color: #1a1a1a;
}

.section-desc {
  font-size: 14px;
  color: #666;
  margin: 0;
}

/* 表格样式 */
.provider-table {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  overflow: hidden;
}

.table-header {
  display: grid;
  grid-template-columns: 90px 1fr 100px 1fr 120px;
  gap: 12px;
  padding: 12px 16px;
  background: #f9fafb;
  border-bottom: 1px solid #e5e7eb;
  font-size: 12px;
  font-weight: 600;
  color: #6b7280;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.table-row {
  display: grid;
  grid-template-columns: 90px 1fr 100px 1fr 120px;
  gap: 12px;
  padding: 14px 16px;
  border-bottom: 1px solid #e5e7eb;
  align-items: center;
  transition: background-color 0.15s;
}

.table-row:last-child {
  border-bottom: none;
}

.table-row:hover {
  background: #f9fafb;
}

.table-row.active {
  background: #fef2f2;
}

/* 状态相关 */
.status-badge {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
}

.status-badge.active {
  background: #dcfce7;
  color: #166534;
}

.btn-activate {
  padding: 4px 12px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  background: white;
  color: #374151;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.15s;
}

.btn-activate:hover:not(:disabled) {
  border-color: var(--primary);
  color: var(--primary);
  background: #fef2f2;
}

.btn-activate.active {
  background: #10b981;
  color: white;
  border-color: #10b981;
  cursor: default;
}

.btn-activate:disabled {
  opacity: 1;
}

/* 名称和模型 */
.provider-name {
  font-weight: 500;
  color: #1a1a1a;
}

.model-name {
  font-size: 13px;
  color: #4b5563;
  font-family: 'Monaco', 'Menlo', monospace;
}

/* API Key 列 */
.apikey-masked {
  font-size: 12px;
  font-family: 'Monaco', 'Menlo', monospace;
  color: #6b7280;
}

.apikey-masked.empty {
  color: #9ca3af;
  font-style: italic;
}

.type-tag {
  display: inline-block;
  padding: 2px 8px;
  background: #e5e7eb;
  border-radius: 4px;
  font-size: 12px;
  color: #4b5563;
}

/* 操作按钮 */
.col-actions {
  display: flex;
  gap: 8px;
}

.btn-icon {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: #6b7280;
  cursor: pointer;
  transition: all 0.15s;
}

.btn-icon:hover {
  background: #e5e7eb;
  color: #1a1a1a;
}

.btn-icon.danger:hover {
  background: #fecaca;
  color: #b91c1c;
}

/* 按钮样式 */
.btn-small {
  padding: 6px 12px;
  font-size: 13px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

/* 表单样式 */
.form-group {
  margin-bottom: 16px;
}

.form-group:last-child {
  margin-bottom: 0;
}

.form-group label {
  display: block;
  font-size: 13px;
  font-weight: 500;
  color: #333;
  margin-bottom: 6px;
}

.form-input,
.form-select {
  width: 100%;
  padding: 10px 12px;
  font-size: 14px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  transition: all 0.2s;
  font-family: inherit;
  box-sizing: border-box;
}

.form-input:focus,
.form-select:focus {
  outline: none;
  border-color: var(--primary);
  box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.1);
}

.form-input::placeholder {
  color: #9ca3af;
}

.form-hint {
  display: block;
  font-size: 12px;
  color: #9ca3af;
  margin-top: 4px;
}

/* Toggle 开关样式 */
.toggle-label {
  display: flex;
  align-items: center;
  justify-content: space-between;
  cursor: pointer;
}

.toggle-switch {
  width: 44px;
  height: 24px;
  background: #d1d5db;
  border-radius: 12px;
  position: relative;
  transition: background 0.2s;
  flex-shrink: 0;
}

.toggle-switch.active {
  background: var(--primary);
}

.toggle-slider {
  width: 20px;
  height: 20px;
  background: white;
  border-radius: 50%;
  position: absolute;
  top: 2px;
  left: 2px;
  transition: transform 0.2s;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
}

.toggle-switch.active .toggle-slider {
  transform: translateX(20px);
}

/* 操作按钮区 */
.actions {
  margin-top: 32px;
  display: flex;
  justify-content: flex-end;
}

/* 加载状态 */
.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 20px;
  color: #666;
}

/* 弹窗样式 */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 20px;
  box-sizing: border-box;
}

.modal-content {
  background: white;
  border-radius: 12px;
  max-width: 480px;
  width: 100%;
  max-height: calc(100vh - 40px);
  display: flex;
  flex-direction: column;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.15);
}

.modal-header {
  padding: 16px 20px;
  border-bottom: 1px solid #e5e7eb;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-shrink: 0;
}

.modal-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
}

.close-btn {
  background: none;
  border: none;
  font-size: 24px;
  color: #999;
  cursor: pointer;
  padding: 0;
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  transition: all 0.2s;
}

.close-btn:hover {
  background: #f3f4f6;
  color: #333;
}

.modal-body {
  padding: 20px;
  overflow-y: auto;
  flex: 1;
}

.modal-footer {
  padding: 14px 20px;
  border-top: 1px solid #e5e7eb;
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  flex-shrink: 0;
  background: white;
  border-radius: 0 0 12px 12px;
}

.spinner-small {
  width: 16px;
  height: 16px;
  border: 2px solid currentColor;
  border-top-color: transparent;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
  display: inline-block;
  margin-right: 8px;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

/* 响应式 */
@media (max-width: 768px) {
  .table-header,
  .table-row {
    grid-template-columns: 70px 1fr 80px;
  }

  .col-type,
  .col-model,
  .col-apikey {
    display: none;
  }

  .modal-overlay {
    padding: 16px;
    align-items: flex-end;
  }

  .modal-content {
    max-height: calc(100vh - 32px);
    border-radius: 16px 16px 0 0;
    max-width: 100%;
  }

  .modal-footer {
    border-radius: 0;
  }
}
</style>
