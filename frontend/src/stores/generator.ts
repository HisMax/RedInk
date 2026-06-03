/**
 * 生成器状态管理 Store
 *
 * 功能说明：
 * - 管理图片生成的完整流程状态（输入主题 -> 生成大纲 -> 编辑大纲 -> 生成图片 -> 查看结果）
 * - 支持历史记录的保存和恢复
 * - 支持本地 localStorage 持久化，防止页面刷新后数据丢失
 * - 支持内容生成（标题、文案、标签）
 *
 * 状态流转：
 * 1. input: 用户输入主题
 * 2. outline: 生成并编辑大纲
 * 3. generating: 正在生成图片
 * 4. result: 查看生成结果
 */
import { defineStore } from 'pinia'
import type { Page, PublishGate, QualityScore, RevisionResult } from '../api'

/**
 * 生成的图片信息
 */
export interface GeneratedImage {
  index: number  // 图片对应的页面索引
  url: string    // 图片URL
  status: 'generating' | 'done' | 'error' | 'retrying'  // 生成状态
  error?: string      // 错误信息
  retryable?: boolean // 是否可以重试
}

/**
 * 生成的内容数据（标题、文案、标签）
 */
export interface GeneratedContent {
  titles: string[]     // 标题列表（多个备选）
  copywriting: string  // 文案内容
  tags: string[]       // 标签列表
  status: 'idle' | 'generating' | 'done' | 'error'  // 生成状态
  error?: string       // 错误信息
}

export interface GeneratorState {
  // 当前阶段：input-输入主题, outline-编辑大纲, generating-生成中, result-查看结果
  stage: 'input' | 'outline' | 'generating' | 'result'

  // 用户输入的主题
  topic: string

  // 大纲数据（包含原始文本和解析后的页面列表）
  outline: {
    raw: string      // 原始大纲文本
    pages: Page[]    // 解析后的页面数组
  }

  // 图片生成进度
  progress: {
    current: number  // 当前已完成的数量
    total: number    // 总共需要生成的数量
    status: 'idle' | 'generating' | 'done' | 'error'
  }

  // 生成的图片结果列表
  images: GeneratedImage[]

  // 图片生成任务ID（用于轮询任务状态）
  taskId: string | null

  // 历史记录ID（用于保存和加载历史记录）
  recordId: string | null

  // 用户上传的参考图片（File对象，不会被持久化）
  userImages: File[]

  // 生成的内容数据（标题、文案、标签）
  content: GeneratedContent

  // 当前内容生成与质量评估链路的追踪ID
  traceId: string | null

  // 内容质量评分结果
  quality: QualityScore | null

  // 发布前检查闸门
  publishGate: PublishGate | null

  // 质量评分状态
  qualityStatus: 'idle' | 'evaluating' | 'done' | 'error'

  // 质量评分错误信息
  qualityError?: string

  // 改写历史
  revisionHistory: RevisionResult[]

  // 大纲生成状态：idle-未开始, generating-生成中, done-已完成, error-出错
  outlineStatus: 'idle' | 'generating' | 'done' | 'error'

  // 最后一次保存到服务器的时间（ISO格式字符串）
  lastSavedAt: string | null
}

const STORAGE_KEY = 'generator-state'

// 从 localStorage 加载状态
function loadState(): Partial<GeneratorState> {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved) {
      return JSON.parse(saved)
    }
  } catch (e) {
    console.error('加载状态失败:', e)
  }
  return {}
}

// 保存状态到 localStorage
function saveState(state: GeneratorState) {
  try {
    // 只保存关键数据，不保存 userImages（文件对象无法序列化）
    const toSave = {
      stage: state.stage,                    // 当前阶段
      topic: state.topic,                    // 用户输入的主题
      outline: state.outline,                // 大纲数据
      progress: state.progress,              // 生成进度
      images: state.images,                  // 生成的图片结果
      taskId: state.taskId,                  // 任务ID
      recordId: state.recordId,              // 历史记录ID
      content: state.content,                // 生成的内容（标题、文案、标签）
      traceId: state.traceId,                // 内容生成与评分追踪ID
      quality: state.quality,                // 内容质量评分
      publishGate: state.publishGate,        // 发布前检查闸门
      qualityStatus: state.qualityStatus,    // 质量评分状态
      qualityError: state.qualityError,      // 质量评分错误
      revisionHistory: state.revisionHistory, // 改写历史
      outlineStatus: state.outlineStatus,    // 大纲生成状态
      lastSavedAt: state.lastSavedAt         // 最后保存时间
    }
    localStorage.setItem(STORAGE_KEY, JSON.stringify(toSave))
  } catch (e) {
    console.error('保存状态失败:', e)
  }
}

export const useGeneratorStore = defineStore('generator', {
  state: (): GeneratorState => {
    const saved = loadState()
    return {
      // 当前阶段
      stage: saved.stage || 'input',

      // 用户输入的主题
      topic: saved.topic || '',

      // 大纲数据
      outline: saved.outline || {
        raw: '',
        pages: []
      },

      // 图片生成进度
      progress: saved.progress || {
        current: 0,
        total: 0,
        status: 'idle'
      },

      // 生成的图片结果
      images: saved.images || [],

      // 任务ID
      taskId: saved.taskId || null,

      // 历史记录ID
      recordId: saved.recordId || null,

      // 用户上传的参考图片（不从 localStorage 恢复）
      userImages: [],

      // 生成的内容数据
      content: saved.content || {
        titles: [],
        copywriting: '',
        tags: [],
        status: 'idle'
      },

      // 内容生成与质量评估链路的追踪ID
      traceId: saved.traceId || null,

      // 内容质量评分结果
      quality: saved.quality || null,

      // 发布前检查闸门
      publishGate: saved.publishGate || null,

      // 质量评分状态
      qualityStatus: saved.qualityStatus || 'idle',

      // 质量评分错误信息
      qualityError: saved.qualityError,

      // 改写历史
      revisionHistory: saved.revisionHistory || [],

      // 大纲生成状态
      outlineStatus: saved.outlineStatus || 'idle',

      // 最后保存时间
      lastSavedAt: saved.lastSavedAt || null
    }
  },

  actions: {
    /**
     * 设置用户输入的主题
     * @param topic 主题内容
     */
    setTopic(topic: string) {
      this.topic = topic
    },

    /**
     * 设置大纲数据
     * @param raw 原始大纲文本
     * @param pages 解析后的页面数组
     */
    setOutline(raw: string, pages: Page[]) {
      this.outline.raw = raw
      this.outline.pages = pages
      this.stage = 'outline'
      this.outlineStatus = 'done'  // 设置大纲为已完成状态
    },

    /**
     * 更新指定页面的内容
     * @param index 页面索引
     * @param content 新的页面内容
     */
    updatePage(index: number, content: string) {
      const page = this.outline.pages.find(p => p.index === index)
      if (page) {
        page.content = content
        // 同步更新 raw 文本
        this.syncRawFromPages()
      }
    },

    /**
     * 根据 pages 数组重新生成 raw 文本
     * 用于保持 raw 和 pages 的数据同步
     */
    syncRawFromPages() {
      this.outline.raw = this.outline.pages
        .map(page => page.content)
        .join('\n\n<page>\n\n')
    },

    /**
     * 删除指定索引的页面
     * @param index 页面索引
     */
    deletePage(index: number) {
      this.outline.pages = this.outline.pages.filter(p => p.index !== index)
      // 重新索引所有页面
      this.outline.pages.forEach((page, idx) => {
        page.index = idx
      })
      // 同步更新 raw 文本
      this.syncRawFromPages()
    },

    /**
     * 在列表末尾添加新页面
     * @param type 页面类型：cover-封面, content-内容, summary-总结
     * @param content 页面内容，默认为空
     */
    addPage(type: 'cover' | 'content' | 'summary', content: string = '') {
      const newPage: Page = {
        index: this.outline.pages.length,
        type,
        content
      }
      this.outline.pages.push(newPage)
      // 同步更新 raw 文本
      this.syncRawFromPages()
    },

    /**
     * 在指定位置后插入新页面
     * @param afterIndex 在此索引后插入
     * @param type 页面类型
     * @param content 页面内容
     */
    insertPage(afterIndex: number, type: 'cover' | 'content' | 'summary', content: string = '') {
      const newPage: Page = {
        index: afterIndex + 1,
        type,
        content
      }
      this.outline.pages.splice(afterIndex + 1, 0, newPage)
      // 重新索引所有页面
      this.outline.pages.forEach((page, idx) => {
        page.index = idx
      })
      // 同步更新 raw 文本
      this.syncRawFromPages()
    },

    /**
     * 移动页面位置（用于拖拽排序）
     * @param fromIndex 源位置索引
     * @param toIndex 目标位置索引
     */
    movePage(fromIndex: number, toIndex: number) {
      const pages = [...this.outline.pages]
      const [movedPage] = pages.splice(fromIndex, 1)
      pages.splice(toIndex, 0, movedPage)

      // 重新索引所有页面
      pages.forEach((page, idx) => {
        page.index = idx
      })

      this.outline.pages = pages
      // 同步更新 raw 文本
      this.syncRawFromPages()
    },

    /**
     * 开始图片生成流程
     * 初始化进度状态和图片列表
     */
    startGeneration() {
      this.stage = 'generating'
      this.progress.current = 0
      this.progress.total = this.outline.pages.length
      this.progress.status = 'generating'
      // 为每个页面创建对应的图片占位对象
      this.images = this.outline.pages.map(page => ({
        index: page.index,
        url: '',
        status: 'generating'
      }))
    },

    /**
     * 更新图片生成进度
     * @param index 页面索引
     * @param status 生成状态
     * @param url 图片URL（可选）
     * @param error 错误信息（可选）
     */
    updateProgress(index: number, status: 'generating' | 'done' | 'error', url?: string, error?: string) {
      const image = this.images.find(img => img.index === index)
      if (image) {
        image.status = status
        if (url) image.url = url
        if (error) image.error = error
      }
      // 成功完成时增加计数
      if (status === 'done') {
        this.progress.current++
      }
    },

    /**
     * 更新指定图片的URL
     * @param index 页面索引
     * @param newUrl 新的图片URL
     */
    updateImage(index: number, newUrl: string) {
      const image = this.images.find(img => img.index === index)
      if (image) {
        // 添加时间戳避免缓存
        const timestamp = Date.now()
        image.url = `${newUrl}?t=${timestamp}`
        image.status = 'done'
        delete image.error
      }
    },

    /**
     * 完成图片生成流程
     * @param taskId 生成任务的ID
     */
    finishGeneration(taskId: string) {
      this.taskId = taskId
      this.stage = 'result'
      this.progress.status = 'done'
    },

    /**
     * 设置指定图片为重试中状态
     * @param index 页面索引
     */
    setImageRetrying(index: number) {
      const image = this.images.find(img => img.index === index)
      if (image) {
        image.status = 'retrying'
      }
    },

    /**
     * 获取所有生成失败的图片列表
     * @returns 失败的图片数组
     */
    getFailedImages() {
      return this.images.filter(img => img.status === 'error')
    },

    /**
     * 获取生成失败的图片对应的页面
     * @returns 失败页面的数组
     */
    getFailedPages() {
      const failedIndices = this.images
        .filter(img => img.status === 'error')
        .map(img => img.index)
      return this.outline.pages.filter(page => failedIndices.includes(page.index))
    },

    /**
     * 检查是否存在生成失败的图片
     * @returns true-存在失败的图片, false-所有图片都成功
     */
    hasFailedImages() {
      return this.images.some(img => img.status === 'error')
    },

    /**
     * 重置所有状态到初始值
     * 用于开始新的生成任务时清空之前的数据
     */
    reset() {
      // 重置当前阶段为输入阶段
      this.stage = 'input'

      // 清空用户输入的主题
      this.topic = ''

      // 清空大纲数据
      this.outline = {
        raw: '',      // 原始大纲文本
        pages: []     // 解析后的页面数组
      }

      // 重置图片生成进度
      this.progress = {
        current: 0,   // 已完成数量归零
        total: 0,     // 总数归零
        status: 'idle' // 状态设为空闲
      }

      // 清空生成的图片结果
      this.images = []

      // 清空任务ID
      this.taskId = null

      // 清空历史记录ID
      this.recordId = null

      // 清空用户上传的参考图片
      this.userImages = []

      // 重置生成的内容数据
      this.content = {
        titles: [],          // 清空标题列表
        copywriting: '',     // 清空文案
        tags: [],            // 清空标签列表
        status: 'idle'       // 状态设为空闲
      }

      // 清空内容质量闭环状态
      this.traceId = null
      this.quality = null
      this.publishGate = null
      this.qualityStatus = 'idle'
      this.qualityError = undefined
      this.revisionHistory = []

      // 重置大纲生成状态
      this.outlineStatus = 'idle'

      // 清空最后保存时间
      this.lastSavedAt = null

      // 清除 localStorage 中的持久化数据
      localStorage.removeItem(STORAGE_KEY)
    },

    /**
     * 开始生成内容（标题、文案、标签）
     * 设置状态为生成中并清除之前的错误
     */
    startContentGeneration() {
      this.content.status = 'generating'
      this.content.error = undefined
    },

    /**
     * 设置生成的内容数据
     * @param titles 标题列表
     * @param copywriting 文案内容
     * @param tags 标签列表
     */
    setContent(titles: string[], copywriting: string, tags: string[]) {
      this.content.titles = titles
      this.content.copywriting = copywriting
      this.content.tags = tags
      this.content.status = 'done'
      this.content.error = undefined
    },

    /**
     * 设置内容生成失败的错误信息
     * @param error 错误描述
     */
    setContentError(error: string) {
      this.content.status = 'error'
      this.content.error = error
    },

    /**
     * 设置当前内容生成和评分链路的追踪ID
     * @param traceId 追踪ID，null表示清空
     */
    setTraceId(traceId: string | null) {
      this.traceId = traceId
    },

    /**
     * 开始质量评分
     */
    startQualityEvaluation() {
      this.qualityStatus = 'evaluating'
      this.qualityError = undefined
    },

    /**
     * 设置质量评分结果
     * @param quality 质量评分
     * @param publishGate 发布前检查闸门
     * @param traceId 可选追踪ID
     */
    setQualityResult(quality: QualityScore, publishGate: PublishGate, traceId?: string | null) {
      this.quality = quality
      this.publishGate = publishGate
      if (traceId) this.traceId = traceId
      this.qualityStatus = 'done'
      this.qualityError = undefined
    },

    /**
     * 设置质量评分错误
     * @param error 错误信息
     */
    setQualityError(error: string) {
      this.qualityStatus = 'error'
      this.qualityError = error
    },

    /**
     * 应用改写结果，并清空旧评分等待重新评估
     * @param revision 改写结果
     */
    applyRevision(revision: RevisionResult) {
      this.content.titles = revision.titles
      this.content.copywriting = revision.copywriting
      this.content.tags = revision.tags
      this.content.status = 'done'
      this.revisionHistory.push(revision)
      this.qualityStatus = 'idle'
      this.quality = null
      this.publishGate = null
    },

    /**
     * 清除生成的内容数据
     * 重置为初始状态
     */
    clearContent() {
      this.content = {
        titles: [],
        copywriting: '',
        tags: [],
        status: 'idle'
      }
    },

    /**
     * 设置大纲生成状态
     * @param status 大纲生成状态：idle-未开始, generating-生成中, done-已完成, error-出错
     */
    setOutlineStatus(status: 'idle' | 'generating' | 'done' | 'error') {
      this.outlineStatus = status
    },

    /**
     * 设置历史记录ID（带验证）
     * @param recordId 历史记录ID，null表示清空
     */
    setRecordId(recordId: string | null) {
      // 验证recordId格式（如果不为null）
      if (recordId !== null && typeof recordId !== 'string') {
        console.error('recordId 必须是字符串或 null')
        return
      }

      this.recordId = recordId

      // 如果设置了新的recordId，同时更新最后保存时间
      if (recordId !== null) {
        this.lastSavedAt = new Date().toISOString()
      }
    },

    /**
     * 标记已保存到服务器
     * 更新最后保存时间为当前时间
     */
    markSaved() {
      this.lastSavedAt = new Date().toISOString()
    },

    /**
     * 检查是否有未保存的更改
     * @returns true-有未保存的更改, false-没有未保存的更改
     */
    hasUnsavedChanges(): boolean {
      // 如果没有历史记录ID，说明从未保存过
      if (!this.recordId) {
        // 如果有任何实质性的数据（主题、大纲、图片），则认为有未保存的更改
        return !!(this.topic || this.outline.pages.length > 0 || this.images.length > 0)
      }

      // 如果有历史记录ID但没有保存时间，认为有未保存的更改
      if (!this.lastSavedAt) {
        return true
      }

      // 可以根据具体需求添加更多判断逻辑
      // 例如：检查最后修改时间是否晚于最后保存时间
      return false
    },

    /**
     * 保存当前状态到 localStorage
     * 用于浏览器刷新后恢复状态
     */
    saveToStorage() {
      saveState(this)
    }
  }
})

// 监听状态变化并自动保存（使用 watch）
import { watch } from 'vue'

/**
 * 设置自动保存功能
 * 监听store中关键字段的变化，自动保存到localStorage
 */
export function setupAutoSave() {
  const store = useGeneratorStore()

  // 监听关键字段变化并自动保存到localStorage
  watch(
    () => ({
      stage: store.stage,                    // 当前阶段
      topic: store.topic,                    // 用户输入的主题
      outline: store.outline,                // 大纲数据
      progress: store.progress,              // 生成进度
      images: store.images,                  // 生成的图片结果
      taskId: store.taskId,                  // 任务ID
      recordId: store.recordId,              // 历史记录ID
      content: store.content,                // 生成的内容
      traceId: store.traceId,                // 内容生成与评分追踪ID
      quality: store.quality,                // 内容质量评分
      publishGate: store.publishGate,        // 发布前检查闸门
      qualityStatus: store.qualityStatus,    // 质量评分状态
      qualityError: store.qualityError,      // 质量评分错误
      revisionHistory: store.revisionHistory, // 改写历史
      outlineStatus: store.outlineStatus,    // 大纲生成状态
      lastSavedAt: store.lastSavedAt         // 最后保存时间
    }),
    () => {
      store.saveToStorage()
    },
    { deep: true }  // 深度监听，确保对象内部的变化也能被捕获
  )
}
