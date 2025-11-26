<template>
  <div class="container" style="max-width: 1200px;">
    
    <!-- Header Area -->
    <div class="page-header">
      <div>
        <h1 class="page-title">我的创作</h1>
      </div>
      <div style="display: flex; gap: 10px;">
        <button
          class="btn"
          @click="handleScanAll"
          :disabled="isScanning"
          style="border: 1px solid var(--border-color);"
        >
          <svg v-if="!isScanning" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-right: 6px;"><path d="M23 4v6h-6"></path><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path></svg>
          <div v-else class="spinner-small" style="margin-right: 6px;"></div>
          {{ isScanning ? '同步中...' : '同步历史' }}
        </button>
        <button class="btn btn-primary" @click="router.push('/')">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-right: 6px;"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>
          新建图文
        </button>
      </div>
    </div>

    <!-- Stats Overview -->
    <div class="stats-overview" v-if="stats">
      <div class="stat-box">
        <div class="stat-icon-circle blue">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>
        </div>
        <div class="stat-content">
          <h4>总作品数</h4>
          <div class="number">{{ stats.total || 0 }}</div>
        </div>
      </div>
      <div class="stat-box">
        <div class="stat-icon-circle green">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>
        </div>
        <div class="stat-content">
          <h4>已完成</h4>
          <div class="number">{{ stats.by_status?.completed || 0 }}</div>
        </div>
      </div>
      <div class="stat-box">
        <div class="stat-icon-circle orange">
           <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20h9"></path><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"></path></svg>
        </div>
        <div class="stat-content">
          <h4>草稿箱</h4>
          <div class="number">{{ stats.by_status?.draft || 0 }}</div>
        </div>
      </div>
    </div>

    <!-- Toolbar: Tabs & Search -->
    <div class="toolbar-wrapper">
      <div class="tabs-container" style="margin-bottom: 0; border-bottom: none;">
        <div 
          class="tab-item" 
          :class="{ active: currentTab === 'all' }"
          @click="switchTab('all')"
        >
          全部
        </div>
        <div 
          class="tab-item" 
          :class="{ active: currentTab === 'completed' }"
          @click="switchTab('completed')"
        >
          已完成
        </div>
        <div 
          class="tab-item" 
          :class="{ active: currentTab === 'draft' }"
          @click="switchTab('draft')"
        >
          草稿箱
        </div>
      </div>

      <div class="search-mini">
        <svg class="icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
        <input 
          v-model="searchKeyword" 
          type="text" 
          placeholder="搜索标题..." 
          @keyup.enter="handleSearch"
        />
      </div>
    </div>

    <!-- Content Area -->
    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
    </div>

    <div v-else-if="records.length === 0" class="empty-state-large">
      <div class="empty-img">
        <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" stroke-linecap="round" stroke-linejoin="round"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path><polyline points="3.27 6.96 12 12.01 20.73 6.96"></polyline><line x1="12" y1="22.08" x2="12" y2="12"></line></svg>
      </div>
      <h3>暂无相关记录</h3>
      <p>去创建一个新的作品吧</p>
    </div>

    <div v-else class="gallery-grid">
      <div 
        v-for="record in records" 
        :key="record.id" 
        class="gallery-card"
      >
        <!-- Card Cover -->
        <div class="card-cover" @click="viewImages(record.id)">
          <img
            v-if="record.thumbnail && record.task_id"
            :src="`/api/images/${record.task_id}/${record.thumbnail}`"
            alt="cover"
            loading="lazy"
            decoding="async"
          />
          <div v-else class="cover-placeholder">
            <span>{{ record.title.charAt(0) }}</span>
          </div>
          
          <!-- Overlay Actions -->
          <div class="card-overlay">
            <button class="overlay-btn" @click.stop="viewImages(record.id)">
              预览
            </button>
            <button class="overlay-btn primary" @click.stop="loadRecord(record.id)">
              编辑
            </button>
          </div>

          <!-- Status Badge -->
          <div class="status-badge" :class="record.status">
            {{ getStatusText(record.status) }}
          </div>
        </div>

        <!-- Card Footer -->
        <div class="card-footer">
          <div class="card-title" :title="record.title">{{ record.title }}</div>
          <div class="card-meta">
            <span>{{ record.page_count }}P</span>
            <span class="dot">·</span>
            <span>{{ formatDate(record.updated_at) }}</span>
            
            <div class="more-actions-wrapper">
              <button class="more-btn" @click.stop="confirmDelete(record)">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Pagination -->
    <div v-if="totalPages > 1" class="pagination-wrapper">
       <button class="page-btn" :disabled="currentPage === 1" @click="changePage(currentPage - 1)">Previous</button>
       <span class="page-indicator">{{ currentPage }} / {{ totalPages }}</span>
       <button class="page-btn" :disabled="currentPage === totalPages" @click="changePage(currentPage + 1)">Next</button>
    </div>

    <!-- Image Viewer Modal (Reused Logic) -->
    <div v-if="viewingRecord" class="modal-fullscreen" @click="closeGallery">
       <div class="modal-body" @click.stop>
          <div class="modal-header">
            <div style="flex: 1;">
              <!-- 标题区域 -->
              <div class="title-section">
                <h3
                  class="modal-title"
                  :class="{ 'collapsed': !titleExpanded && viewingRecord.title.length > 80 }"
                >
                  {{ viewingRecord.title }}
                </h3>
                <button
                  v-if="viewingRecord.title.length > 80"
                  class="title-expand-btn"
                  @click="titleExpanded = !titleExpanded"
                >
                  {{ titleExpanded ? '收起' : '展开' }}
                </button>
              </div>

              <div style="font-size: 12px; color: #999; display: flex; align-items: center; gap: 12px; margin-top: 8px;">
                <span>{{ viewingRecord.outline.pages.length }} 张图片 · {{ formatDate(viewingRecord.updated_at) }}</span>
                <button
                  class="view-outline-btn"
                  @click="showOutlineModal = true"
                  title="查看完整大纲"
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                    <polyline points="14 2 14 8 20 8"></polyline>
                    <line x1="16" y1="13" x2="8" y2="13"></line>
                    <line x1="16" y1="17" x2="8" y2="17"></line>
                  </svg>
                  查看大纲
                </button>
              </div>
            </div>
            <div style="display: flex; gap: 12px; align-items: flex-start;">
              <button class="btn" @click="downloadAllImages" style="padding: 8px 16px; font-size: 14px;">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-right: 6px;"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>
                打包下载
              </button>
              <button class="close-icon" @click="closeGallery">×</button>
            </div>
          </div>

          <div class="modal-gallery-grid">
             <div v-for="(img, idx) in viewingRecord.images.generated" :key="idx" class="modal-img-item">
                <!-- 图片预览区域 -->
                <div class="modal-img-preview" v-if="img">
                  <img
                    :src="`/api/images/${viewingRecord.images.task_id}/${img}`"
                    loading="lazy"
                    decoding="async"
                  />
                  <!-- 重新生成按钮（悬停显示） -->
                  <div class="modal-img-overlay">
                    <button
                      class="modal-overlay-btn"
                      @click="regenerateHistoryImage(idx)"
                      :disabled="regeneratingImages.has(idx)"
                    >
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M23 4v6h-6"></path>
                        <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path>
                      </svg>
                      {{ regeneratingImages.has(idx) ? '重绘中...' : '重新生成' }}
                    </button>
                  </div>
                </div>
                <div class="placeholder" v-else>Waiting...</div>
                <div style="margin-top: 8px; display: flex; justify-content: space-between; font-size: 12px; color: #666;">
                   <span>Page {{ idx + 1 }}</span>
                   <span v-if="img" style="cursor: pointer; color: var(--primary);" @click="downloadImage(img, idx)">下载</span>
                </div>
             </div>
          </div>
       </div>
    </div>

    <!-- 大纲查看模态框 -->
    <div v-if="showOutlineModal && viewingRecord" class="outline-modal-overlay" @click="showOutlineModal = false">
      <div class="outline-modal-content" @click.stop>
        <div class="outline-modal-header">
          <h3>完整大纲</h3>
          <button class="close-icon" @click="showOutlineModal = false">×</button>
        </div>
        <div class="outline-modal-body">
          <div v-for="(page, idx) in viewingRecord.outline.pages" :key="idx" class="outline-page-card">
            <div class="outline-page-card-header">
              <span class="page-badge">P{{ idx + 1 }}</span>
              <span class="page-type-badge" :class="page.type">{{ getPageTypeName(page.type) }}</span>
              <span class="word-count">{{ page.content.length }} 字</span>
            </div>
            <div class="outline-page-card-content">{{ page.content }}</div>
          </div>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { getHistoryList, getHistoryStats, searchHistory, deleteHistory, getHistory, type HistoryRecord, regenerateImage as apiRegenerateImage, updateHistory, scanAllTasks } from '../api'
import { useGeneratorStore } from '../stores/generator'

const router = useRouter()
const store = useGeneratorStore()

const records = ref<HistoryRecord[]>([])
const loading = ref(false)
const stats = ref<any>(null)
const currentTab = ref('all') // all, completed, draft
const searchKeyword = ref('')

const currentPage = ref(1)
const totalPages = ref(1)

// Viewer
const viewingRecord = ref<any>(null)
// 正在重新生成的图片索引集合
const regeneratingImages = ref<Set<number>>(new Set())
// 标题展开状态
const titleExpanded = ref(false)
// 原始输入展开状态
const rawInputExpanded = ref(false)
// 大纲模态框显示状态
const showOutlineModal = ref(false)
// 扫描状态
const isScanning = ref(false)

const loadData = async () => {
  loading.value = true
  try {
    let statusFilter = currentTab.value === 'all' ? undefined : currentTab.value
    
    // Special mapping for tabs if needed
    if (currentTab.value === 'completed') statusFilter = 'completed'
    if (currentTab.value === 'draft') statusFilter = 'draft' // API might expect 'draft'

    const res = await getHistoryList(currentPage.value, 12, statusFilter)
    if (res.success) {
      records.value = res.records
      totalPages.value = res.total_pages
    }
  } catch(e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

const loadStats = async () => {
  try {
    const res = await getHistoryStats()
    if (res.success) stats.value = res
  } catch(e) {}
}

const switchTab = (tab: string) => {
  currentTab.value = tab
  currentPage.value = 1
  loadData()
}

const handleSearch = async () => {
  if (!searchKeyword.value.trim()) {
    loadData()
    return
  }
  loading.value = true
  try {
    const res = await searchHistory(searchKeyword.value)
    if (res.success) {
      records.value = res.records
      totalPages.value = 1
    }
  } catch(e) {} finally {
    loading.value = false
  }
}

const getStatusText = (status: string) => {
  const map: any = { draft: '草稿', completed: '已完成', generating: '生成中' }
  return map[status] || status
}

const getPageTypeName = (type: string) => {
  const names: any = {
    cover: '封面',
    content: '内容',
    summary: '总结'
  }
  return names[type] || '内容'
}

const formatDate = (str: string) => {
  const d = new Date(str)
  return `${d.getMonth()+1}/${d.getDate()}`
}

const loadRecord = async (id: string) => {
  const res = await getHistory(id)
  if (res.success && res.record) {
    store.setTopic(res.record.title)
    store.setOutline(res.record.outline.raw, res.record.outline.pages)
    store.recordId = res.record.id
    if (res.record.images.generated.length > 0) {
        store.taskId = res.record.images.task_id
        store.images = res.record.outline.pages.map((page, idx) => {
          const filename = res.record!.images.generated[idx]
          return {
            index: idx,
            url: filename ? `/api/images/${res.record!.images.task_id}/${filename}` : '',
            status: filename ? 'done' : 'error',
            retryable: !filename
          }
        })
    }
    router.push('/outline')
  }
}

const viewImages = async (id: string) => {
  const res = await getHistory(id)
  if (res.success) viewingRecord.value = res.record
}

const closeGallery = () => {
  viewingRecord.value = null
  titleExpanded.value = false // 关闭时重置标题展开状态
  rawInputExpanded.value = false // 关闭时重置原始输入展开状态
  showOutlineModal.value = false // 关闭大纲模态框
}

// 复制原始输入
const copyOriginalInput = async () => {
  if (!viewingRecord.value) return
  try {
    await navigator.clipboard.writeText(viewingRecord.value.outline.raw)
    alert('原始输入已复制到剪贴板')
  } catch (e) {
    alert('复制失败，请手动复制')
  }
}

const confirmDelete = async (record: any) => {
  if(confirm('确定删除吗？')) {
    await deleteHistory(record.id)
    loadData()
    loadStats()
  }
}

const changePage = (p: number) => {
  currentPage.value = p
  loadData()
}

// 重新生成历史记录中的图片
async function regenerateHistoryImage(index: number) {
  if (!viewingRecord.value || !viewingRecord.value.images.task_id) {
    alert('无法重新生成：缺少任务信息')
    return
  }

  const page = viewingRecord.value.outline.pages[index]
  if (!page) return

  regeneratingImages.value.add(index)

  try {
    // 构建上下文信息
    const context = {
      fullOutline: viewingRecord.value.outline.raw || '',
      userTopic: viewingRecord.value.title || ''
    }

    const result = await apiRegenerateImage(
      viewingRecord.value.images.task_id,
      page,
      true,
      context
    )

    if (result.success && result.image_url) {
      const filename = result.image_url.split('/').pop()
      viewingRecord.value.images.generated[index] = filename

      const timestamp = Date.now()
      const imgElements = document.querySelectorAll(`img[src*="${viewingRecord.value.images.task_id}/${filename}"]`)
      imgElements.forEach(img => {
        const baseUrl = (img as HTMLImageElement).src.split('?')[0]
        ;(img as HTMLImageElement).src = `${baseUrl}?t=${timestamp}`
      })

      await updateHistory(viewingRecord.value.id, {
        images: {
          task_id: viewingRecord.value.images.task_id,
          generated: viewingRecord.value.images.generated
        }
      })

      regeneratingImages.value.delete(index)
    } else {
      regeneratingImages.value.delete(index)
      alert('重新生成失败: ' + (result.error || '未知错误'))
    }
  } catch (e) {
    regeneratingImages.value.delete(index)
    alert('重新生成失败: ' + String(e))
  }
}

// 下载单张图片（使用原图）
function downloadImage(filename: string, index: number) {
  if (!viewingRecord.value) return
  const link = document.createElement('a')
  link.href = `/api/images/${viewingRecord.value.images.task_id}/${filename}?thumbnail=false`
  link.download = `page_${index + 1}.png`
  link.click()
}

// 打包下载所有图片为 ZIP
async function downloadAllImages() {
  if (!viewingRecord.value) return

  // 调用 ZIP 下载接口
  const link = document.createElement('a')
  link.href = `/api/history/${viewingRecord.value.id}/download`
  link.click()
}

// 扫描所有任务并同步图片列表
async function handleScanAll() {
  isScanning.value = true
  try {
    const result = await scanAllTasks()
    if (result.success) {
      console.log('扫描完成:', result)

      // 显示扫描结果
      let message = `扫描完成！\n`
      message += `- 总任务数: ${result.total_tasks || 0}\n`
      message += `- 同步成功: ${result.synced || 0}\n`
      message += `- 同步失败: ${result.failed || 0}\n`

      if (result.orphan_tasks && result.orphan_tasks.length > 0) {
        message += `- 孤立任务（无记录）: ${result.orphan_tasks.length} 个\n`
      }

      alert(message)

      // 刷新列表和统计
      await loadData()
      await loadStats()
    } else {
      alert('扫描失败: ' + (result.error || '未知错误'))
    }
  } catch (e) {
    console.error('扫描失败:', e)
    alert('扫描失败: ' + String(e))
  } finally {
    isScanning.value = false
  }
}

onMounted(async () => {
  // 先加载数据
  await loadData()
  await loadStats()

  // 自动执行一次扫描（静默，不显示结果）
  try {
    const result = await scanAllTasks()
    if (result.success && (result.synced || 0) > 0) {
      // 如果有更新，刷新列表
      await loadData()
      await loadStats()
    }
  } catch (e) {
    console.error('自动扫描失败:', e)
  }
})
</script>

<style scoped>
/* Small Spinner */
.spinner-small {
  width: 16px;
  height: 16px;
  border: 2px solid var(--primary);
  border-top-color: transparent;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  display: inline-block;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

/* Toolbar */
.toolbar-wrapper {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  border-bottom: 1px solid var(--border-color);
  padding-bottom: 0; /* Tabs handle border */
}

.search-mini {
  position: relative;
  width: 240px;
  margin-bottom: 10px; /* Align with tabs */
}

.search-mini input {
  width: 100%;
  padding: 8px 12px 8px 36px;
  border-radius: 100px;
  border: 1px solid var(--border-color);
  font-size: 14px;
  background: white;
  transition: border-color 0.2s, box-shadow 0.2s;
}
.search-mini input:focus {
  border-color: var(--primary);
  outline: none;
  box-shadow: 0 0 0 3px var(--primary-light);
}

.search-mini .icon {
  position: absolute;
  left: 12px;
  top: 50%;
  transform: translateY(-50%);
  color: #ccc;
}

/* Gallery Grid */
.gallery-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 24px;
  margin-bottom: 40px;
}

.gallery-card {
  background: white;
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid rgba(0,0,0,0.04);
  transition: transform 0.2s cubic-bezier(0.4, 0, 0.2, 1), box-shadow 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  will-change: transform;
  contain: layout style paint;
}

.gallery-card:hover {
  transform: translateY(-4px) translateZ(0);
  box-shadow: 0 12px 24px rgba(0,0,0,0.08);
}

.card-cover {
  aspect-ratio: 3/4;
  background: #f7f7f7;
  position: relative;
  overflow: hidden;
  cursor: pointer;
}

.card-cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  will-change: transform;
  backface-visibility: hidden;
}

.gallery-card:hover .card-cover img {
  transform: scale(1.05) translateZ(0);
}

.cover-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 48px;
  color: #e0e0e0;
  font-weight: 800;
  background: #FAFAFA;
}

/* Overlay */
.card-overlay {
  position: absolute;
  inset: 0;
  background: rgba(0,0,0,0.4);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  opacity: 0;
  transition: opacity 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  backdrop-filter: blur(2px);
  pointer-events: none;
  will-change: opacity;
}

.gallery-card:hover .card-overlay {
  opacity: 1;
  pointer-events: auto;
}

.overlay-btn {
  padding: 8px 24px;
  border-radius: 100px;
  border: 1px solid rgba(255,255,255,0.8);
  background: rgba(255,255,255,0.2);
  color: white;
  font-size: 14px;
  cursor: pointer;
  transition: background-color 0.2s, color 0.2s, transform 0.1s;
  will-change: transform;
}

.overlay-btn:hover {
  background: white;
  color: var(--text-main);
  transform: translateY(-2px);
}

.overlay-btn.primary {
  background: var(--primary);
  border-color: var(--primary);
}
.overlay-btn.primary:hover {
  background: var(--primary-hover);
  color: white;
}

/* Status Badge */
.status-badge {
  position: absolute;
  top: 12px;
  left: 12px;
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  background: rgba(0,0,0,0.6);
  color: white;
  backdrop-filter: blur(4px);
}
.status-badge.completed { background: rgba(82, 196, 26, 0.9); }
.status-badge.draft { background: rgba(0, 0, 0, 0.5); }
.status-badge.generating { background: rgba(24, 144, 255, 0.9); }

/* Footer */
.card-footer {
  padding: 16px;
}

.card-title {
  font-size: 15px;
  font-weight: 600;
  margin-bottom: 8px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  color: var(--text-main);
}

.card-meta {
  display: flex;
  align-items: center;
  font-size: 12px;
  color: var(--text-sub);
}

.dot { margin: 0 6px; }

.more-actions-wrapper {
  margin-left: auto;
}

.more-btn {
  background: none;
  border: none;
  color: var(--text-placeholder);
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
}
.more-btn:hover {
  background: #fee;
  color: #ff4d4f;
}

/* Pagination */
.pagination-wrapper {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 16px;
  margin-top: 40px;
}

.page-btn {
  padding: 8px 16px;
  border: 1px solid var(--border-color);
  background: white;
  border-radius: 6px;
  cursor: pointer;
}
.page-btn:disabled { opacity: 0.5; cursor: not-allowed; }

/* Empty State */
.empty-state-large {
  text-align: center;
  padding: 80px 0;
  color: var(--text-sub);
}
.empty-img { font-size: 64px; margin-bottom: 24px; opacity: 0.5; }

/* Fullscreen Modal */
.modal-fullscreen {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.9);
  z-index: 999;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
}
.modal-body {
  background: white;
  width: 100%;
  max-width: 1000px;
  height: 90vh;
  border-radius: 16px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.modal-header {
  padding: 20px;
  border-bottom: 1px solid #eee;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  flex-shrink: 0;
  gap: 20px;
}

/* 标题区域 */
.title-section {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 4px;
}

.modal-title {
  flex: 1;
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  line-height: 1.4;
  color: #1a1a1a;
  word-break: break-word;
  transition: max-height 0.3s ease;
}

.modal-title.collapsed {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-overflow: ellipsis;
}

.title-expand-btn {
  flex-shrink: 0;
  padding: 2px 8px;
  background: #f0f0f0;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 11px;
  color: #666;
  transition: all 0.2s;
  margin-top: 2px;
}

.title-expand-btn:hover {
  background: var(--primary);
  color: white;
}

/* 原始输入区域 */
.original-input-section {
  margin-top: 16px;
  padding: 16px 20px;
  background: #ffffff;
  border-radius: 12px;
  border: 1px solid #e5e7eb;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.original-input-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  padding-bottom: 10px;
  border-bottom: 1px solid #f3f4f6;
}

.copy-btn-small {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  background: white;
  border: 1px solid #dee2e6;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  color: #495057;
  transition: all 0.2s;
}

.copy-btn-small:hover {
  background: var(--primary);
  color: white;
  border-color: var(--primary);
}

.copy-btn-small svg {
  flex-shrink: 0;
}

/* 查看大纲按钮 */
.view-outline-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  background: white;
  border: 1px solid #dee2e6;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  color: #495057;
  transition: all 0.2s;
}

.view-outline-btn:hover {
  background: var(--primary);
  color: white;
  border-color: var(--primary);
}

.view-outline-btn svg {
  flex-shrink: 0;
}

.original-input-text {
  font-size: 14px;
  line-height: 1.8;
  color: #374151;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: none;
  overflow: hidden;
  transition: max-height 0.3s ease;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
}

.original-input-text.collapsed {
  max-height: 4.8em; /* 约3行 */
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-overflow: ellipsis;
}

.expand-btn-small {
  display: block;
  margin-top: 8px;
  padding: 4px 12px;
  background: white;
  border: 1px solid #dee2e6;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  color: var(--primary);
  transition: all 0.2s;
  width: 100%;
}

.expand-btn-small:hover {
  background: #f8f9fa;
  border-color: var(--primary);
}

/* 大纲折叠区域 */
.outline-section {
  max-height: 300px;
  overflow-y: auto;
  border-bottom: 1px solid #eee;
  background: #fafafa;
  flex-shrink: 0;
}

.modal-gallery-grid {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 20px;
}
.modal-img-preview {
  position: relative;
  width: 100%;
  aspect-ratio: 3/4;
  overflow: hidden;
  border-radius: 8px;
  contain: layout style paint;
}

.modal-img-preview img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.modal-img-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.15s ease-out;
  pointer-events: none;
  will-change: opacity;
}

.modal-img-preview:hover .modal-img-overlay {
  opacity: 1;
  pointer-events: auto;
}

.modal-overlay-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  background: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  color: #333;
  transition: background-color 0.2s, color 0.2s, transform 0.1s;
  will-change: transform;
}

.modal-overlay-btn:hover {
  background: var(--primary);
  color: white;
  transform: scale(1.05);
}

.modal-overlay-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
}

.modal-img-item img {
  width: 100%;
  border-radius: 8px;
}
.close-icon {
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
}

/* 大纲查看模态框 */
.outline-modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.75);
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
}

.outline-modal-content {
  background: white;
  width: 100%;
  max-width: 800px;
  max-height: 85vh;
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
}

.outline-modal-header {
  padding: 20px 24px;
  border-bottom: 1px solid #eee;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-shrink: 0;
}

.outline-modal-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #1a1a1a;
}

.outline-modal-body {
  flex: 1;
  overflow-y: auto;
  padding: 20px 24px;
  background: #f9fafb;
}

.outline-page-card {
  background: #ffffff;
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 16px;
  border: 1px solid #e5e7eb;
  transition: all 0.2s;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.outline-page-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  border-color: #d1d5db;
}

.outline-page-card:last-child {
  margin-bottom: 0;
}

.outline-page-card-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 14px;
  padding-bottom: 14px;
  border-bottom: 1px solid #e5e7eb;
}

.page-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 36px;
  height: 24px;
  padding: 0 8px;
  background: var(--primary);
  color: white;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 700;
  font-family: 'Inter', sans-serif;
}

.page-type-badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  background: #e9ecef;
  color: #6c757d;
}

.page-type-badge.cover {
  background: #e3f2fd;
  color: #1976d2;
}

.page-type-badge.content {
  background: #f3e5f5;
  color: #7b1fa2;
}

.page-type-badge.summary {
  background: #e8f5e9;
  color: #388e3c;
}

.word-count {
  margin-left: auto;
  font-size: 11px;
  color: #999;
}

.outline-page-card-content {
  font-size: 14px;
  line-height: 1.8;
  color: #374151;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
}
</style>