import { ref } from 'vue'
import { getConfig, testConnection, updateConfig, type Config } from '../api'

type ProviderCategory = 'text' | 'image'

interface TypeOption {
  value: string
  label: string
}

export const textTypeOptions: TypeOption[] = [
  { value: 'openai_compatible', label: 'OpenAI 兼容' },
  { value: 'google_gemini', label: 'Google Gemini' }
]

export const imageTypeOptions: TypeOption[] = [
  { value: 'image_api', label: '通用图片 API' },
  { value: 'google_genai', label: 'Google GenAI (Imagen)' },
  { value: 'wan2.6-t2i', label: '通义万相 Wan2.6 (文生图V2)' },
  { value: 'modelscope_z_image', label: '魔塔 ModelScope Z-Image-Turbo' }
]

interface Provider {
  type: string
  model: string
  base_url?: string
  api_key?: string
  api_key_masked?: string
  _has_api_key?: boolean
  endpoint_type?: string
  high_concurrency?: boolean
  short_prompt?: boolean
}

interface ProviderGroup {
  active_provider: string
  providers: Record<string, Provider>
}

interface TextFormData {
  name: string
  type: string
  api_key: string
  api_key_masked?: string
  _has_api_key?: boolean
  base_url: string
  model: string
  endpoint_type?: string
}

interface ImageFormData {
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

function buildEmptyTextForm(): TextFormData {
  return {
    name: '',
    type: 'openai_compatible',
    api_key: '',
    base_url: '',
    model: '',
    endpoint_type: ''
  }
}

function buildEmptyImageForm(): ImageFormData {
  return {
    name: '',
    type: 'image_api',
    api_key: '',
    base_url: '',
    model: '',
    endpoint_type: '',
    high_concurrency: false,
    short_prompt: false
  }
}

function pickFirstKey<T extends Record<string, any>>(obj: T): string {
  return Object.keys(obj)[0] || ''
}

function normalizeGroup(group: any): ProviderGroup {
  const providers = (group?.providers || {}) as Record<string, Provider>
  let active_provider = String(group?.active_provider || '')
  if (!active_provider || !providers[active_provider]) {
    active_provider = pickFirstKey(providers)
  }
  return { active_provider, providers }
}

async function saveGroup(category: ProviderCategory, group: ProviderGroup): Promise<boolean> {
  const payload: Partial<Config> =
    category === 'text'
      ? { text_generation: group }
      : { image_generation: group }

  const result = await updateConfig(payload)
  if (!result.success) {
    alert(result.error || '保存失败')
    return false
  }
  return true
}

export function useProviderForm() {
  const loading = ref(true)
  const testingText = ref(false)
  const testingImage = ref(false)

  const textConfig = ref<ProviderGroup>({ active_provider: '', providers: {} })
  const imageConfig = ref<ProviderGroup>({ active_provider: '', providers: {} })

  const showTextModal = ref(false)
  const editingTextProvider = ref<string | null>(null)
  const textForm = ref<TextFormData>(buildEmptyTextForm())

  const showImageModal = ref(false)
  const editingImageProvider = ref<string | null>(null)
  const imageForm = ref<ImageFormData>(buildEmptyImageForm())

  async function loadConfig() {
    loading.value = true
    try {
      const result = await getConfig()
      if (!result.success || !result.config) {
        alert(result.error || '加载配置失败')
        return
      }

      textConfig.value = normalizeGroup(result.config.text_generation)
      imageConfig.value = normalizeGroup(result.config.image_generation)
    } catch (e) {
      alert(String(e))
    } finally {
      loading.value = false
    }
  }

  async function activateTextProvider(name: string) {
    if (!textConfig.value.providers[name]) return
    const next = { ...textConfig.value, active_provider: name }
    const ok = await saveGroup('text', next)
    if (ok) await loadConfig()
  }

  function openAddTextModal() {
    editingTextProvider.value = null
    textForm.value = buildEmptyTextForm()
    showTextModal.value = true
  }

  function openEditTextModal(name: string, provider: Provider) {
    editingTextProvider.value = name
    textForm.value = {
      name,
      type: provider.type || 'openai_compatible',
      api_key: '',
      api_key_masked: provider.api_key_masked,
      _has_api_key: provider._has_api_key,
      base_url: provider.base_url || '',
      model: provider.model || '',
      endpoint_type: provider.endpoint_type || ''
    }
    showTextModal.value = true
  }

  function closeTextModal() {
    showTextModal.value = false
    editingTextProvider.value = null
    textForm.value = buildEmptyTextForm()
  }

  async function saveTextProvider() {
    const name = textForm.value.name.trim()
    if (!name) {
      alert('请输入服务商名称')
      return
    }

    const providers = { ...textConfig.value.providers }
    const isEditing = !!editingTextProvider.value
    const targetName = isEditing ? editingTextProvider.value! : name

    if (!isEditing && providers[targetName]) {
      alert('服务商名称已存在')
      return
    }

    if (!isEditing && !textForm.value.api_key.trim()) {
      alert('请输入 API Key')
      return
    }

    providers[targetName] = {
      type: textForm.value.type,
      model: textForm.value.model,
      base_url: textForm.value.base_url || undefined,
      endpoint_type: textForm.value.endpoint_type || undefined,
      api_key: textForm.value.api_key
    }

    const nextGroup: ProviderGroup = {
      active_provider: textConfig.value.active_provider || targetName,
      providers
    }

    const ok = await saveGroup('text', nextGroup)
    if (!ok) return
    await loadConfig()
    closeTextModal()
  }

  async function deleteTextProvider(name: string) {
    if (!textConfig.value.providers[name]) return
    const providerNames = Object.keys(textConfig.value.providers)
    if (providerNames.length <= 1) {
      alert('至少保留一个服务商')
      return
    }
    if (!confirm(`确定删除服务商 “${name}” 吗？`)) return

    const providers = { ...textConfig.value.providers }
    delete providers[name]

    const active_provider =
      textConfig.value.active_provider === name
        ? pickFirstKey(providers)
        : textConfig.value.active_provider

    const ok = await saveGroup('text', { active_provider, providers })
    if (ok) await loadConfig()
  }

  async function testTextConnection() {
    testingText.value = true
    try {
      const payload = {
        type: textForm.value.type,
        provider_name: editingTextProvider.value || undefined,
        api_key: textForm.value.api_key || undefined,
        base_url: textForm.value.base_url || undefined,
        model: textForm.value.model,
        endpoint_type: textForm.value.endpoint_type || undefined
      }
      const result = await testConnection(payload)
      alert(result.success ? (result.message || '连接成功') : (result.error || '连接失败'))
    } catch (e) {
      alert(String(e))
    } finally {
      testingText.value = false
    }
  }

  async function testTextProviderInList(name: string, provider: Provider) {
    testingText.value = true
    try {
      const result = await testConnection({
        type: provider.type,
        provider_name: name,
        base_url: provider.base_url,
        model: provider.model,
        endpoint_type: provider.endpoint_type
      })
      alert(result.success ? (result.message || '连接成功') : (result.error || '连接失败'))
    } catch (e) {
      alert(String(e))
    } finally {
      testingText.value = false
    }
  }

  function updateTextForm(data: TextFormData) {
    textForm.value = data
  }

  async function activateImageProvider(name: string) {
    if (!imageConfig.value.providers[name]) return
    const next = { ...imageConfig.value, active_provider: name }
    const ok = await saveGroup('image', next)
    if (ok) await loadConfig()
  }

  function openAddImageModal() {
    editingImageProvider.value = null
    imageForm.value = buildEmptyImageForm()
    showImageModal.value = true
  }

  function openEditImageModal(name: string, provider: Provider) {
    editingImageProvider.value = name
    imageForm.value = {
      name,
      type: provider.type || 'image_api',
      api_key: '',
      api_key_masked: provider.api_key_masked,
      _has_api_key: provider._has_api_key,
      base_url: provider.base_url || '',
      model: provider.model || '',
      endpoint_type: provider.endpoint_type || '',
      high_concurrency: !!provider.high_concurrency,
      short_prompt: !!provider.short_prompt
    }
    showImageModal.value = true
  }

  function closeImageModal() {
    showImageModal.value = false
    editingImageProvider.value = null
    imageForm.value = buildEmptyImageForm()
  }

  async function saveImageProvider() {
    const name = imageForm.value.name.trim()
    if (!name) {
      alert('请输入服务商名称')
      return
    }

    const providers = { ...imageConfig.value.providers }
    const isEditing = !!editingImageProvider.value
    const targetName = isEditing ? editingImageProvider.value! : name

    if (!isEditing && providers[targetName]) {
      alert('服务商名称已存在')
      return
    }

    if (!isEditing && !imageForm.value.api_key.trim()) {
      alert('请输入 API Key')
      return
    }

    providers[targetName] = {
      type: imageForm.value.type,
      model: imageForm.value.model,
      base_url: imageForm.value.base_url || undefined,
      endpoint_type: imageForm.value.endpoint_type || undefined,
      high_concurrency: !!imageForm.value.high_concurrency,
      short_prompt: !!imageForm.value.short_prompt,
      api_key: imageForm.value.api_key
    }

    const nextGroup: ProviderGroup = {
      active_provider: imageConfig.value.active_provider || targetName,
      providers
    }

    const ok = await saveGroup('image', nextGroup)
    if (!ok) return
    await loadConfig()
    closeImageModal()
  }

  async function deleteImageProvider(name: string) {
    if (!imageConfig.value.providers[name]) return
    const providerNames = Object.keys(imageConfig.value.providers)
    if (providerNames.length <= 1) {
      alert('至少保留一个服务商')
      return
    }
    if (!confirm(`确定删除服务商 “${name}” 吗？`)) return

    const providers = { ...imageConfig.value.providers }
    delete providers[name]

    const active_provider =
      imageConfig.value.active_provider === name
        ? pickFirstKey(providers)
        : imageConfig.value.active_provider

    const ok = await saveGroup('image', { active_provider, providers })
    if (ok) await loadConfig()
  }

  async function testImageConnection() {
    testingImage.value = true
    try {
      const payload = {
        type: imageForm.value.type,
        provider_name: editingImageProvider.value || undefined,
        api_key: imageForm.value.api_key || undefined,
        base_url: imageForm.value.base_url || undefined,
        model: imageForm.value.model,
        endpoint_type: imageForm.value.endpoint_type || undefined
      }
      const result = await testConnection(payload)
      alert(result.success ? (result.message || '连接成功') : (result.error || '连接失败'))
    } catch (e) {
      alert(String(e))
    } finally {
      testingImage.value = false
    }
  }

  async function testImageProviderInList(name: string, provider: Provider) {
    testingImage.value = true
    try {
      const result = await testConnection({
        type: provider.type,
        provider_name: name,
        base_url: provider.base_url,
        model: provider.model,
        endpoint_type: provider.endpoint_type
      })
      alert(result.success ? (result.message || '连接成功') : (result.error || '连接失败'))
    } catch (e) {
      alert(String(e))
    } finally {
      testingImage.value = false
    }
  }

  function updateImageForm(data: ImageFormData) {
    imageForm.value = data
  }

  return {
    loading,
    testingText,
    testingImage,
    textConfig,
    imageConfig,
    showTextModal,
    editingTextProvider,
    textForm,
    showImageModal,
    editingImageProvider,
    imageForm,
    loadConfig,
    activateTextProvider,
    openAddTextModal,
    openEditTextModal,
    closeTextModal,
    saveTextProvider,
    deleteTextProvider,
    testTextConnection,
    testTextProviderInList,
    updateTextForm,
    activateImageProvider,
    openAddImageModal,
    openEditImageModal,
    closeImageModal,
    saveImageProvider,
    deleteImageProvider,
    testImageConnection,
    testImageProviderInList,
    updateImageForm
  }
}
