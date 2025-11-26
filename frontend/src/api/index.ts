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

// 生成图片 (SSE)
export function generateImages(
  pages: Page[],
  taskId: string | null,
  onProgress: (event: ProgressEvent) => void,
  onComplete: (event: ProgressEvent) => void,
  onError: (event: ProgressEvent) => void,
  onFinish: (event: FinishEvent) => void,
  onStreamError: (error: Error) => void
) {
  const eventSource = new EventSource(`${API_BASE_URL}/generate?pages=${encodeURIComponent(JSON.stringify(pages))}&task_id=${taskId || ''}`)

  eventSource.addEventListener('progress', (e: MessageEvent) => {
    const data = JSON.parse(e.data) as ProgressEvent
    onProgress(data)
  })

  eventSource.addEventListener('complete', (e: MessageEvent) => {
    const data = JSON.parse(e.data) as ProgressEvent
    onComplete(data)
  })

  eventSource.addEventListener('error', (e: MessageEvent) => {
    const data = JSON.parse(e.data) as ProgressEvent
    onError(data)
  })

  eventSource.addEventListener('finish', (e: MessageEvent) => {
    const data = JSON.parse(e.data) as FinishEvent
    onFinish(data)
    eventSource.close()
  })

  eventSource.onerror = (error) => {
    onStreamError(new Error('SSE 连接错误'))
    eventSource.close()
  }

  return eventSource
}

// 获取图片 URL（新格式：task_id/filename）
// thumbnail 参数：true=缩略图（默认），false=原图
export function getImageUrl(taskId: string, filename: string, thumbnail: boolean = true): string {
  const thumbParam = thumbnail ? '?thumbnail=true' : '?thumbnail=false'
  return `${API_BASE_URL}/images/${taskId}/${filename}${thumbParam}`
}

// 向后兼容：自动解析包含task_id的URL
export function getImageUrlAuto(urlOrPath: string): string {
  // 如果已经是完整URL，直接返回
  if (urlOrPath.startsWith('http') || urlOrPath.startsWith('/api/')) {
    return urlOrPath
  }
  // 否则假定为 task_id/filename 格式
  return `${API_BASE_URL}/images/${urlOrPath}`
}

// 重试单张图片
export async function retrySingleImage(
  taskId: string,
  page: Page,
  useReference: boolean = true
): Promise<{ success: boolean; index: number; image_url?: string; error?: string }> {
  const response = await axios.post(`${API_BASE_URL}/retry`, {
    task_id: taskId,
    page,
    use_reference: useReference
  })
  return response.data
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
  } catch (error) {
    onStreamError(error as Error)
  }
}

// ==================== 历史记录相关 API ====================

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

// 创建历史记录
export async function createHistory(
  topic: string,
  outline: { raw: string; pages: Page[] },
  taskId?: string
): Promise<{ success: boolean; record_id?: string; error?: string }> {
  const response = await axios.post(`${API_BASE_URL}/history`, {
    topic,
    outline,
    task_id: taskId
  })
  return response.data
}

// 获取历史记录列表
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
}> {
  const params: any = { page, page_size: pageSize }
  if (status) params.status = status

  const response = await axios.get(`${API_BASE_URL}/history`, { params })
  return response.data
}

// 获取历史记录详情
export async function getHistory(recordId: string): Promise<{
  success: boolean
  record?: HistoryDetail
  error?: string
}> {
  const response = await axios.get(`${API_BASE_URL}/history/${recordId}`)
  return response.data
}

// 更新历史记录
export async function updateHistory(
  recordId: string,
  data: {
    outline?: { raw: string; pages: Page[] }
    images?: { task_id: string | null; generated: string[] }
    status?: string
    thumbnail?: string
  }
): Promise<{ success: boolean; error?: string }> {
  const response = await axios.put(`${API_BASE_URL}/history/${recordId}`, data)
  return response.data
}

// 删除历史记录
export async function deleteHistory(recordId: string): Promise<{
  success: boolean
  error?: string
}> {
  const response = await axios.delete(`${API_BASE_URL}/history/${recordId}`)
  return response.data
}

// 搜索历史记录
export async function searchHistory(keyword: string): Promise<{
  success: boolean
  records: HistoryRecord[]
}> {
  const response = await axios.get(`${API_BASE_URL}/history/search`, {
    params: { keyword }
  })
  return response.data
}

// 获取统计信息
export async function getHistoryStats(): Promise<{
  success: boolean
  total: number
  by_status: Record<string, number>
}> {
  const response = await axios.get(`${API_BASE_URL}/history/stats`)
  return response.data
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
  } catch (error) {
    onStreamError(error as Error)
  }
}

// 扫描单个任务并同步图片列表
export async function scanTask(taskId: string): Promise<{
  success: boolean
  record_id?: string
  task_id?: string
  images_count?: number
  images?: string[]
  status?: string
  no_record?: boolean
  error?: string
}> {
  const response = await axios.get(`${API_BASE_URL}/history/scan/${taskId}`)
  return response.data
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
