<template>
  <!-- 图片服务商编辑/添加弹窗 -->
  <div v-if="visible" class="modal-overlay" @click="$emit('close')">
    <div class="modal-content" @click.stop>
      <div class="modal-header">
        <h3>{{ isEditing ? '编辑服务商' : '添加服务商' }}</h3>
        <button class="close-btn" @click="$emit('close')">×</button>
      </div>

      <div class="modal-body">
        <!-- 服务商名称（仅添加时显示） -->
        <div class="form-group" v-if="!isEditing">
          <label>服务商名称</label>
          <input
            type="text"
            class="form-input"
            :value="formData.name"
            @input="updateField('name', ($event.target as HTMLInputElement).value)"
            placeholder="例如: google_genai"
          />
          <span class="form-hint">唯一标识，用于区分不同服务商</span>
        </div>

        <!-- 类型选择 -->
        <div class="form-group">
          <label>类型</label>
          <select
            class="form-select"
            :value="formData.type"
            @change="updateField('type', ($event.target as HTMLSelectElement).value)"
          >
            <option v-for="opt in typeOptions" :key="opt.value" :value="opt.value">
              {{ opt.label }}
            </option>
          </select>
        </div>

        <!-- API Key -->
        <div class="form-group">
          <label>API Key</label>
          <input
            type="text"
            class="form-input"
            :value="formData.api_key"
            @input="updateField('api_key', ($event.target as HTMLInputElement).value)"
            :placeholder="isEditing && formData._has_api_key ? formData.api_key_masked : '输入 API Key'"
          />
          <span class="form-hint" v-if="isEditing && formData._has_api_key">
            已配置 API Key，留空表示不修改
          </span>
        </div>

        <!-- Base URL -->
        <div class="form-group" v-if="showBaseUrl">
          <label>Base URL</label>
          <input
            type="text"
            class="form-input"
            :value="formData.base_url"
            @input="updateField('base_url', ($event.target as HTMLInputElement).value)"
            :placeholder="baseUrlPlaceholder"
          />
          <span class="form-hint" v-if="previewUrl">
            预览: {{ previewUrl }}
          </span>
        </div>

        <!-- 模型 -->
        <div class="form-group">
          <label>模型</label>
          <input
            type="text"
            class="form-input"
            :value="formData.model"
            @input="updateField('model', ($event.target as HTMLInputElement).value)"
            :placeholder="modelPlaceholder"
          />
        </div>

        <!-- 端点路径（仅 OpenAI 兼容接口） -->
        <div class="form-group" v-if="showEndpointType">
          <label>API 端点路径</label>
          <input
            type="text"
            class="form-input"
            :value="formData.endpoint_type"
            @input="updateField('endpoint_type', ($event.target as HTMLInputElement).value)"
            placeholder="例如: /v1/images/generations 或 /v1/chat/completions"
          />
          <span class="form-hint">
            常用端点：/v1/images/generations（标准图片生成）、/v1/chat/completions（即梦等返回链接的 API）
          </span>
        </div>

        <!-- 高并发模式 -->
        <div class="form-group">
          <label class="toggle-label">
            <span>高并发模式</span>
            <div
              class="toggle-switch"
              :class="{ active: formData.high_concurrency }"
              @click="updateField('high_concurrency', !formData.high_concurrency)"
            >
              <div class="toggle-slider"></div>
            </div>
          </label>
          <span class="form-hint">
            启用后将并行生成图片，速度更快但对 API 质量要求较高。GCP 300$ 试用账号不建议启用。
          </span>
        </div>

        <!-- 短 Prompt 模式 -->
        <div class="form-group">
          <label class="toggle-label">
            <span>短 Prompt 模式</span>
            <div
              class="toggle-switch"
              :class="{ active: formData.short_prompt }"
              @click="updateField('short_prompt', !formData.short_prompt)"
            >
              <div class="toggle-slider"></div>
            </div>
          </label>
          <span class="form-hint">
            启用后使用精简版提示词，适合有字符限制的 API（如即梦 1600 字符限制）。
          </span>
        </div>
      </div>

      <div class="modal-footer">
        <button class="btn" @click="$emit('close')">取消</button>
        <button
          class="btn btn-secondary"
          @click="$emit('test')"
          :disabled="testing || (!formData.api_key && !isEditing)"
        >
          <span v-if="testing" class="spinner-small"></span>
          {{ testing ? '测试中...' : '测试连接' }}
        </button>
        <button class="btn btn-primary" @click="$emit('save')">
          {{ isEditing ? '保存' : '添加' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

/**
 * 图片服务商编辑/添加弹窗组件
 *
 * 功能：
 * - 添加新服务商
 * - 编辑现有服务商
 * - 测试连接
 * - 支持高并发模式和短 Prompt 模式开关
 */

// 定义表单数据类型
interface FormData {
  name: string
  type: string
  api_key: string
  api_key_masked?: string
  _has_api_key?: boolean
  base_url: string
  model: string
  endpoint_type?: string
  high_concurrency?: boolean
  short_prompt?: boolean
}

// 定义类型选项
interface TypeOption {
  value: string
  label: string
}

// 定义 Props
const props = defineProps<{
  visible: boolean
  isEditing: boolean
  formData: FormData
  testing: boolean
  typeOptions: TypeOption[]
}>()

// 定义 Emits
const emit = defineEmits<{
  (e: 'close'): void
  (e: 'save'): void
  (e: 'test'): void
  (e: 'update:formData', data: FormData): void
}>()

// 更新表单字段
function updateField(field: keyof FormData, value: string | boolean) {
  emit('update:formData', {
    ...props.formData,
    [field]: value
  })
}

// 是否显示 Base URL
const showBaseUrl = computed(() => {
  return ['image_api', 'google_genai', 'wan2.6-t2i', 'modelscope_z_image'].includes(props.formData.type)
})

// 是否显示端点类型
const showEndpointType = computed(() => {
  return ['image_api', 'modelscope_z_image'].includes(props.formData.type)
})

// 模型占位符
const modelPlaceholder = computed(() => {
  switch (props.formData.type) {
    case 'google_genai':
      return '例如: imagen-3.0-generate-002'
    case 'image_api':
      return '例如: flux-pro'
    case 'wan2.6-t2i':
      return '例如: wan2.6-t2i'
    case 'modelscope_z_image':
      return '例如: Tongyi-MAI/Z-Image-Turbo'
    default:
      return '例如: gpt-4o'
  }
})

const baseUrlPlaceholder = computed(() => {
  switch (props.formData.type) {
    case 'google_genai':
      return '例如: https://generativelanguage.googleapis.com'
    case 'image_api':
      return '例如: https://api.openai.com'
    case 'wan2.6-t2i':
      return '例如: https://dashscope.aliyuncs.com/api/v1'
    case 'modelscope_z_image':
      return '例如: https://api-inference.modelscope.cn'
    default:
      return '例如: https://api.example.com'
  }
})

// 预览 URL
const previewUrl = computed(() => {
  if (!props.formData.base_url) return ''

  if (props.formData.type === 'wan2.6-t2i') {
    const rawBaseUrl = props.formData.base_url.replace(/\/$/, '')
    return `${rawBaseUrl}/services/aigc/multimodal-generation/generation`
  }
  if (props.formData.type === 'modelscope_z_image') {
    const rawBaseUrl = props.formData.base_url.replace(/\/+$/, '')
    return `${rawBaseUrl}/`
  }

  const baseUrl = props.formData.base_url.replace(/\/$/, '').replace(/\/v1$/, '')
  const endpointType = props.formData.endpoint_type || '/v1/images/generations'

  switch (props.formData.type) {
    case 'image_api':
      // 如果用户自定义了 endpoint_type，直接显示完整路径
      if (props.formData.endpoint_type) {
         // 检查 base_url 是否已经包含了 endpoint 的开头部分（简单的去重逻辑）
         // 这里只做简单展示，更复杂的逻辑在后端处理
         const endpoint = props.formData.endpoint_type.startsWith('/') ? props.formData.endpoint_type : '/' + props.formData.endpoint_type
         
         // 简单的去重显示：如果 base_url 结尾是 /v1 且 endpoint 是 /v1/...
         if (baseUrl.endsWith('/v1') && endpoint.startsWith('/v1')) {
            return `${baseUrl.slice(0, -3)}${endpoint}`
         }
          // 如果 base_url 结尾是 /v3 且 endpoint 是 /v3/...
         if (baseUrl.endsWith('/v3') && endpoint.startsWith('/v3')) {
            return `${baseUrl.slice(0, -3)}${endpoint}`
         }

         return `${baseUrl}${endpoint}`
      }

      if (endpointType.includes('chat')) {
        return `${baseUrl}/v1/chat/completions`
      }
      return `${baseUrl}/v1/images/generations`
    case 'google_genai':
      return `${baseUrl}/v1beta/models/${props.formData.model || '{model}'}:generateImages`
    default:
      return ''
  }
})
</script>

<style scoped>
/* 模态框遮罩 */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 20px;
}

/* 模态框内容 */
.modal-content {
  background: white;
  border-radius: 12px;
  width: 100%;
  max-width: 500px;
  max-height: 90vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.2);
}

/* 头部 */
.modal-header {
  padding: 20px 24px;
  border-bottom: 1px solid var(--border-color, #eee);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.modal-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
}

.close-btn {
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: #999;
  padding: 0;
  line-height: 1;
}

.close-btn:hover {
  color: #333;
}

/* 主体 */
.modal-body {
  padding: 24px;
  overflow-y: auto;
  flex: 1;
}

/* 表单组 */
.form-group {
  margin-bottom: 20px;
}

.form-group:last-child {
  margin-bottom: 0;
}

.form-group label {
  display: block;
  font-size: 14px;
  font-weight: 500;
  color: var(--text-main, #1a1a1a);
  margin-bottom: 8px;
}

.form-input {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--border-color, #eee);
  border-radius: 8px;
  font-size: 14px;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.form-input:focus {
  outline: none;
  border-color: var(--primary, #ff2442);
  box-shadow: 0 0 0 3px rgba(255, 36, 66, 0.1);
}

.form-select {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--border-color, #eee);
  border-radius: 8px;
  font-size: 14px;
  background: white;
  cursor: pointer;
}

.form-hint {
  display: block;
  font-size: 12px;
  color: var(--text-sub, #666);
  margin-top: 6px;
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
  background: var(--primary, #ff2442);
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

/* 底部 */
.modal-footer {
  padding: 16px 24px;
  border-top: 1px solid var(--border-color, #eee);
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

/* 按钮样式 */
.btn {
  padding: 8px 16px;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  border: 1px solid var(--border-color, #eee);
  background: white;
  color: var(--text-main, #1a1a1a);
  transition: all 0.2s;
}

.btn:hover {
  background: #f5f5f5;
}

.btn-primary {
  background: var(--primary, #ff2442);
  border-color: var(--primary, #ff2442);
  color: white;
}

.btn-primary:hover {
  background: var(--primary-hover, #e61e3a);
}

.btn-secondary {
  background: #f0f0f0;
  border-color: #ddd;
  color: #333;
}

.btn-secondary:hover {
  background: #e5e5e5;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 加载动画 */
.spinner-small {
  display: inline-block;
  width: 14px;
  height: 14px;
  border: 2px solid currentColor;
  border-top-color: transparent;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-right: 6px;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
