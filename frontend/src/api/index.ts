import axios from 'axios'

const API_BASE_URL = '/api'

export interface Page {
  index: number
  type: 'cover' | 'content' | 'summary'
  content: string
}

export interface OutlineResponse {
  success: boolean
  outline?: string
  pages?: Page[]
  error?: string
}

export interface ProgressEvent {
  index: number
  status: 'generating' | 'done' | 'error'
  current?: number
  total?: number
  image_url?: string
  message?: string
}

export interface FinishEvent {
  success: boolean
  task_id: string
  images: string[]
}

// 生成大纲（支持图片上传）
export async function generateOutline(
  topic: string,
  images?: File[]
): Promise<OutlineResponse & { has_images?: boolean }> {
  // 如果有图片，使用 FormData
  if (images && images.length > 0) {
    const formData = new FormData()
    formData.append('topic', topic)
    images.forEach((file) => {
      formData.append('images', file)
    })

    const response = await axios.post<OutlineResponse & { has_images?: boolean }>(
      `${API_BASE_URL}/outline`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      }
    )
    return response.data
  }

  // 无图片，使用 JSON
  const response = await axios.post<OutlineResponse>(`${API_BASE_URL}/outline`, {
    topic
  })
  return response.data
}

// 获取图片 URL（新格式：task_id/filename）
// thumbnail 参数：true=缩略图（默认），false=原图
export function getImageUrl(taskId: string, filename: string, thumbnail: boolean = true): string {
  const thumbParam = thumbnail ? '?thumbnail=true' : '?thumbnail=false'
  return `${API_BASE_URL}/images/${taskId}/${filename}${thumbParam}`
}

// 重新生成图片（即使成功的也可以重新生成）
export async function regenerateImage(
  taskId: string,
  page: Page,
  useReference: boolean = true,
  context?: {
    fullOutline?: string
    userTopic?: string
  }
): Promise<{ success: boolean; index: number; image_url?: string; error?: string }> {
  const response = await axios.post(`${API_BASE_URL}/regenerate`, {
    task_id: taskId,
    page,
    use_reference: useReference,
    full_outline: context?.fullOutline,
    user_topic: context?.userTopic
  })
  return response.data
}

// 批量重试失败的图片（SSE）
export async function retryFailedImages(
  taskId: string,
  pages: Page[],
  onProgress: (event: ProgressEvent) => void,
  onComplete: (event: ProgressEvent) => void,
  onError: (event: ProgressEvent) => void,
  onFinish: (event: { success: boolean; total: number; completed: number; failed: number }) => void,
  onStreamError: (error: Error) => void
) {
  try {
    const response = await fetch(`${API_BASE_URL}/retry-failed`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        task_id: taskId,
        pages
      })
    })

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }

    const reader = response.body?.getReader()
    if (!reader) {
      throw new Error('无法读取响应流')
    }

    const decoder = new TextDecoder()
    let buffer = ''

    try {
      while (true) {
        const { done, value } = await reader.read()

        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (!line.trim()) continue

          const [eventLine, dataLine] = line.split('\n')
          if (!eventLine || !dataLine) continue

          const eventType = eventLine.replace('event: ', '').trim()
          const eventData = dataLine.replace('data: ', '').trim()

          try {
            const data = JSON.parse(eventData)

            switch (eventType) {
              case 'retry_start':
                onProgress({ index: -1, status: 'generating', message: data.message })
                break
              case 'complete':
                onComplete(data)
                break
              case 'error':
                onError(data)
                break
              case 'retry_finish':
                onFinish(data)
                break
            }
          } catch (e) {
            console.error('解析 SSE 数据失败:', e)
          }
        }
      }
    } finally {
      reader.releaseLock()
    }
  } catch (error) {
    onStreamError(error as Error)
  }
}

// ==================== 历史记录相关 API ====================

/**
 * 历史记录列表项接口
 */
export interface HistoryRecord {
  id: string
  title: string
  created_at: string
  updated_at: string
  status: string
  thumbnail: string | null
  page_count: number
  task_id: string | null
}

/**
 * 历史记录详情接口
 */
export interface HistoryDetail {
  id: string
  title: string
  created_at: string
  updated_at: string
  outline: {
    raw: string
    pages: Page[]
  }
  images: {
    task_id: string | null
    generated: string[]
  }
  status: string
  thumbnail: string | null
}

/**
 * 创建历史记录参数接口
 */
export interface CreateHistoryParams {
  topic: string
  outline: { raw: string; pages: Page[] }
  task_id?: string
  trace_id?: string | null
  content?: {
    titles: string[]
    copywriting: string
    tags: string[]
  }
  quality?: {
    quality_score: QualityScore
    publish_gate: PublishGate
  }
}

/**
 * 更新历史记录参数接口
 */
export interface UpdateHistoryParams {
  outline?: { raw: string; pages: Page[] }
  images?: { task_id: string | null; generated: string[] }
  status?: string
  thumbnail?: string
  trace_id?: string | null
  content?: {
    titles: string[]
    copywriting: string
    tags: string[]
  }
  quality?: {
    quality_score: QualityScore
    publish_gate: PublishGate
  }
  revision_entry?: RevisionResult
}

/**
 * 创建历史记录
 *
 * 用于在用户生成大纲后保存记录，以便后续查看和继续编辑
 *
 * @param topic - 绘本主题/标题
 * @param outline - 大纲数据，包含原始文本和页面列表
 * @param outline.raw - 大纲的原始文本
 * @param outline.pages - 解析后的页面列表
 * @param taskId - 可选的任务 ID，用于关联图片生成任务
 *
 * @returns Promise<{ success: boolean; record_id?: string; error?: string }>
 * - success: 是否创建成功
 * - record_id: 创建的记录 ID（成功时返回）
 * - error: 错误信息（失败时返回）
 *
 * @throws {Error} 网络错误或服务器错误
 *
 * @example
 * ```typescript
 * const result = await createHistory(
 *   '小兔子的冒险',
 *   {
 *     raw: '第一页：小兔子出门了...',
 *     pages: [{ index: 0, type: 'cover', content: '...' }]
 *   },
 *   'task-123'
 * )
 * if (result.success) {
 *   console.log('记录创建成功，ID:', result.record_id)
 * }
 * ```
 */
export async function createHistory(
  topic: string,
  outline: { raw: string; pages: Page[] },
  taskId?: string,
  metadata?: {
    trace_id?: string | null
    content?: { titles: string[]; copywriting: string; tags: string[] }
    quality?: { quality_score: QualityScore; publish_gate: PublishGate }
  }
): Promise<{ success: boolean; record_id?: string; error?: string }> {
  try {
    const response = await axios.post(
      `${API_BASE_URL}/history`,
      {
        topic,
        outline,
        task_id: taskId,
        trace_id: metadata?.trace_id,
        content: metadata?.content,
        quality: metadata?.quality
      },
      {
        timeout: 10000 // 10秒超时
      }
    )
    return response.data
  } catch (error: any) {
    if (axios.isAxiosError(error)) {
      if (error.code === 'ECONNABORTED') {
        return { success: false, error: '请求超时，请检查网络连接' }
      }
      if (!error.response) {
        return { success: false, error: '网络连接失败，请检查网络设置' }
      }
      const errorMessage = error.response?.data?.error || error.message || '创建历史记录失败'
      return { success: false, error: errorMessage }
    }
    return { success: false, error: '未知错误，请稍后重试' }
  }
}

/**
 * 获取历史记录列表
 *
 * 支持分页和按状态筛选
 *
 * @param page - 页码，从 1 开始，默认为 1
 * @param pageSize - 每页数量，默认为 20
 * @param status - 可选，按状态筛选（如 'draft', 'generating', 'completed'）
 *
 * @returns Promise 包含历史记录列表和分页信息
 */
export async function getHistoryList(
  page: number = 1,
  pageSize: number = 20,
  status?: string
): Promise<{
  success: boolean
  records: HistoryRecord[]
  total: number
  page: number
  page_size: number
  total_pages: number
  error?: string
}> {
  try {
    const params: any = { page, page_size: pageSize }
    if (status) params.status = status

    const response = await axios.get(`${API_BASE_URL}/history`, {
      params,
      timeout: 10000 // 10秒超时
    })
    return response.data
  } catch (error: any) {
    if (axios.isAxiosError(error)) {
      if (error.code === 'ECONNABORTED') {
        return {
          success: false,
          records: [],
          total: 0,
          page: 1,
          page_size: pageSize,
          total_pages: 0,
          error: '请求超时，请检查网络连接'
        }
      }
      if (!error.response) {
        return {
          success: false,
          records: [],
          total: 0,
          page: 1,
          page_size: pageSize,
          total_pages: 0,
          error: '网络连接失败，请检查网络设置'
        }
      }
      const errorMessage = error.response?.data?.error || error.message || '获取历史记录列表失败'
      return {
        success: false,
        records: [],
        total: 0,
        page: 1,
        page_size: pageSize,
        total_pages: 0,
        error: errorMessage
      }
    }
    return {
      success: false,
      records: [],
      total: 0,
      page: 1,
      page_size: pageSize,
      total_pages: 0,
      error: '未知错误，请稍后重试'
    }
  }
}

/**
 * 获取历史记录详情
 *
 * 获取指定 ID 的历史记录完整信息，包括大纲和图片数据
 *
 * @param recordId - 历史记录 ID
 *
 * @returns Promise 包含历史记录详细信息
 */
export async function getHistory(recordId: string): Promise<{
  success: boolean
  record?: HistoryDetail
  error?: string
}> {
  try {
    const response = await axios.get(`${API_BASE_URL}/history/${recordId}`, {
      timeout: 10000 // 10秒超时
    })
    return response.data
  } catch (error: any) {
    if (axios.isAxiosError(error)) {
      if (error.code === 'ECONNABORTED') {
        return { success: false, error: '请求超时，请检查网络连接' }
      }
      if (!error.response) {
        return { success: false, error: '网络连接失败，请检查网络设置' }
      }
      if (error.response.status === 404) {
        return { success: false, error: '历史记录不存在' }
      }
      const errorMessage = error.response?.data?.error || error.message || '获取历史记录详情失败'
      return { success: false, error: errorMessage }
    }
    return { success: false, error: '未知错误，请稍后重试' }
  }
}

/**
 * 更新历史记录
 *
 * 用于更新已有的历史记录，如更新大纲、图片列表、状态或缩略图
 *
 * @param recordId - 历史记录 ID
 * @param data - 需要更新的数据
 * @param data.outline - 可选，更新大纲数据
 * @param data.images - 可选，更新图片数据（任务 ID 和已生成的图片列表）
 * @param data.status - 可选，更新状态（如 'draft', 'generating', 'completed'）
 * @param data.thumbnail - 可选，更新缩略图 URL
 *
 * @returns Promise<{ success: boolean; error?: string }>
 * - success: 是否更新成功
 * - error: 错误信息（失败时返回）
 *
 * @throws {Error} 网络错误或服务器错误
 *
 * @example
 * ```typescript
 * // 更新图片生成状态
 * const result = await updateHistory('record-123', {
 *   status: 'generating',
 *   images: {
 *     task_id: 'task-456',
 *     generated: ['page1.png', 'page2.png']
 *   }
 * })
 *
 * // 更新缩略图
 * await updateHistory('record-123', {
 *   thumbnail: '/api/images/task-456/page1.png?thumbnail=true'
 * })
 * ```
 */
export async function updateHistory(
  recordId: string,
  data: UpdateHistoryParams
): Promise<{ success: boolean; error?: string }> {
  try {
    const response = await axios.put(
      `${API_BASE_URL}/history/${recordId}`,
      data,
      {
        timeout: 10000 // 10秒超时
      }
    )
    return response.data
  } catch (error: any) {
    if (axios.isAxiosError(error)) {
      if (error.code === 'ECONNABORTED') {
        return { success: false, error: '请求超时，请检查网络连接' }
      }
      if (!error.response) {
        return { success: false, error: '网络连接失败，请检查网络设置' }
      }
      const errorMessage = error.response?.data?.error || error.message || '更新历史记录失败'
      return { success: false, error: errorMessage }
    }
    return { success: false, error: '未知错误，请稍后重试' }
  }
}

/**
 * 检查历史记录是否存在
 *
 * 用于页面刷新后验证 recordId 是否仍然有效
 * 避免用户刷新页面后继续操作一个已被删除的记录
 *
 * @param recordId - 历史记录 ID
 *
 * @returns Promise<boolean> 记录是否存在
 *
 * @example
 * ```typescript
 * const recordId = localStorage.getItem('currentRecordId')
 * if (recordId) {
 *   const exists = await checkHistoryExists(recordId)
 *   if (!exists) {
 *     console.log('记录不存在，可能已被删除')
 *     localStorage.removeItem('currentRecordId')
 *   }
 * }
 * ```
 */
export async function checkHistoryExists(recordId: string): Promise<boolean> {
  try {
    // 使用专用的 /exists 端点，避免获取完整记录数据
    const response = await axios.get(
      `${API_BASE_URL}/history/${recordId}/exists`,
      {
        timeout: 5000 // 5秒超时
      }
    )
    return response.data.exists === true
  } catch (error: any) {
    if (axios.isAxiosError(error)) {
      // 404 表示记录不存在
      if (error.response?.status === 404) {
        return false
      }
      // 其他错误（网络错误等）也视为不存在
      return false
    }
    return false
  }
}

// 删除历史记录
export async function deleteHistory(recordId: string): Promise<{
  success: boolean
  error?: string
}> {
  try {
    const response = await axios.delete(
      `${API_BASE_URL}/history/${recordId}`,
      {
        timeout: 10000 // 10秒超时
      }
    )
    return response.data
  } catch (error: any) {
    if (axios.isAxiosError(error)) {
      if (error.code === 'ECONNABORTED') {
        return { success: false, error: '请求超时，请检查网络连接' }
      }
      if (!error.response) {
        return { success: false, error: '网络连接失败，请检查网络设置' }
      }
      const errorMessage = error.response?.data?.error || error.message || '删除历史记录失败'
      return { success: false, error: errorMessage }
    }
    return { success: false, error: '未知错误，请稍后重试' }
  }
}

/**
 * 搜索历史记录
 *
 * 根据关键词搜索历史记录标题
 *
 * @param keyword - 搜索关键词
 *
 * @returns Promise 包含匹配的历史记录列表
 */
export async function searchHistory(keyword: string): Promise<{
  success: boolean
  records: HistoryRecord[]
  error?: string
}> {
  try {
    const response = await axios.get(`${API_BASE_URL}/history/search`, {
      params: { keyword },
      timeout: 10000 // 10秒超时
    })
    return response.data
  } catch (error: any) {
    if (axios.isAxiosError(error)) {
      if (error.code === 'ECONNABORTED') {
        return { success: false, records: [], error: '请求超时，请检查网络连接' }
      }
      if (!error.response) {
        return { success: false, records: [], error: '网络连接失败，请检查网络设置' }
      }
      const errorMessage = error.response?.data?.error || error.message || '搜索历史记录失败'
      return { success: false, records: [], error: errorMessage }
    }
    return { success: false, records: [], error: '未知错误，请稍后重试' }
  }
}

/**
 * 获取统计信息
 *
 * 获取历史记录的统计数据，包括总数和按状态分类的数量
 *
 * @returns Promise 包含统计信息
 */
export async function getHistoryStats(): Promise<{
  success: boolean
  total: number
  by_status: Record<string, number>
  error?: string
}> {
  try {
    const response = await axios.get(`${API_BASE_URL}/history/stats`, {
      timeout: 10000 // 10秒超时
    })
    return response.data
  } catch (error: any) {
    if (axios.isAxiosError(error)) {
      if (error.code === 'ECONNABORTED') {
        return { success: false, total: 0, by_status: {}, error: '请求超时，请检查网络连接' }
      }
      if (!error.response) {
        return { success: false, total: 0, by_status: {}, error: '网络连接失败，请检查网络设置' }
      }
      const errorMessage = error.response?.data?.error || error.message || '获取统计信息失败'
      return { success: false, total: 0, by_status: {}, error: errorMessage }
    }
    return { success: false, total: 0, by_status: {}, error: '未知错误，请稍后重试' }
  }
}

// 使用 POST 方式生成图片（更可靠）
export async function generateImagesPost(
  pages: Page[],
  taskId: string | null,
  fullOutline: string,
  onProgress: (event: ProgressEvent) => void,
  onComplete: (event: ProgressEvent) => void,
  onError: (event: ProgressEvent) => void,
  onFinish: (event: FinishEvent) => void,
  onStreamError: (error: Error) => void,
  userImages?: File[],
  userTopic?: string
) {
  try {
    // 将用户图片转换为 base64
    let userImagesBase64: string[] = []
    if (userImages && userImages.length > 0) {
      userImagesBase64 = await Promise.all(
        userImages.map(file => {
          return new Promise<string>((resolve, reject) => {
            const reader = new FileReader()
            reader.onload = () => resolve(reader.result as string)
            reader.onerror = reject
            reader.readAsDataURL(file)
          })
        })
      )
    }

    const response = await fetch(`${API_BASE_URL}/generate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        pages,
        task_id: taskId,
        full_outline: fullOutline,
        user_images: userImagesBase64.length > 0 ? userImagesBase64 : undefined,
        user_topic: userTopic || ''
      })
    })

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }

    const reader = response.body?.getReader()
    if (!reader) {
      throw new Error('无法读取响应流')
    }

    const decoder = new TextDecoder()
    let buffer = ''

    try {
      while (true) {
        const { done, value } = await reader.read()

        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (!line.trim()) continue

          const [eventLine, dataLine] = line.split('\n')
          if (!eventLine || !dataLine) continue

          const eventType = eventLine.replace('event: ', '').trim()
          const eventData = dataLine.replace('data: ', '').trim()

          try {
            const data = JSON.parse(eventData)

            switch (eventType) {
              case 'progress':
                onProgress(data)
                break
              case 'complete':
                onComplete(data)
                break
              case 'error':
                onError(data)
                break
              case 'finish':
                onFinish(data)
                break
            }
          } catch (e) {
            console.error('解析 SSE 数据失败:', e)
          }
        }
      }
    } finally {
      reader.releaseLock()
    }
  } catch (error) {
    onStreamError(error as Error)
  }
}

// 扫描所有任务并同步图片列表
export async function scanAllTasks(): Promise<{
  success: boolean
  total_tasks?: number
  synced?: number
  failed?: number
  orphan_tasks?: string[]
  results?: any[]
  error?: string
}> {
  const response = await axios.post(`${API_BASE_URL}/history/scan-all`)
  return response.data
}

// ==================== 配置管理 API ====================

export interface Config {
  text_generation: {
    active_provider: string
    providers: Record<string, any>
  }
  image_generation: {
    active_provider: string
    providers: Record<string, any>
  }
}

// 获取配置
export async function getConfig(): Promise<{
  success: boolean
  config?: Config
  error?: string
}> {
  const response = await axios.get(`${API_BASE_URL}/config`)
  return response.data
}

// 更新配置
export async function updateConfig(config: Partial<Config>): Promise<{
  success: boolean
  message?: string
  error?: string
}> {
  const response = await axios.post(`${API_BASE_URL}/config`, config)
  return response.data
}

// 测试服务商连接
export async function testConnection(config: {
  type: string
  provider_name?: string
  api_key?: string
  base_url?: string
  model: string
}): Promise<{
  success: boolean
  message?: string
  error?: string
}> {
  const response = await axios.post(`${API_BASE_URL}/config/test`, config)
  return response.data
}

// ==================== 内容生成 API（标题、文案、标签） ====================

export interface ContentResponse {
  success: boolean
  titles?: string[]
  copywriting?: string
  tags?: string[]
  error?: string
}

export interface QualityScore {
  overall: number
  topic_clarity: number
  hook_strength: number
  information_density: number
  user_value: number
  xhs_style_fit: number
  originality: number
  title_strength: number
  copy_readability: number
  tag_fit: number
  cover_readability: number
  compliance_risk: number
  decision: 'approve' | 'revise' | 'block'
  issues: string[]
  suggestions: string[]
}

export interface PublishGate {
  enabled: boolean
  requires_user_confirm: boolean
  assets_ready: boolean
  title_ready: boolean
  copy_ready: boolean
  tags_ready: boolean
  risk_checked: boolean
}

export interface QualityResponse {
  success: boolean
  trace_id?: string
  evaluated_at?: string
  quality_score?: QualityScore
  publish_gate?: PublishGate
  error?: string
}

export interface RevisionResult {
  titles: string[]
  copywriting: string
  tags: string[]
  revision_summary: string[]
}

export interface RevisionResponse {
  success: boolean
  trace_id?: string
  revised_at?: string
  revision?: RevisionResult
  error?: string
}

// 生成标题、文案、标签
export async function generateContent(
  topic: string,
  outline: string
): Promise<ContentResponse> {
  const response = await axios.post<ContentResponse>(`${API_BASE_URL}/content`, {
    topic,
    outline
  })
  return response.data
}

export async function evaluateContent(params: {
  topic: string
  outline: string
  titles: string[]
  copywriting: string
  tags: string[]
  trace_id?: string | null
}): Promise<QualityResponse> {
  const response = await axios.post<QualityResponse>(`${API_BASE_URL}/quality/evaluate`, params)
  return response.data
}

export async function reviseContent(params: {
  topic: string
  outline: string
  titles: string[]
  copywriting: string
  tags: string[]
  quality_score: QualityScore
  trace_id?: string | null
}): Promise<RevisionResponse> {
  const response = await axios.post<RevisionResponse>(`${API_BASE_URL}/quality/revise`, params)
  return response.data
}
