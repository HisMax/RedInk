<template>
  <div class="container home-container">
    <!-- 图片网格轮播背景 -->
    <div class="showcase-background">
      <div class="showcase-grid" :style="{ transform: `translateY(-${scrollOffset}px)` }">
        <div v-for="(image, index) in showcaseImages" :key="index" class="showcase-item">
          <img :src="`/assets/showcase/${image}`" :alt="`封面 ${index + 1}`" />
        </div>
      </div>
      <div class="showcase-overlay"></div>
    </div>

    <!-- Hero Area -->
    <div class="hero-section">
      <div class="hero-content">
        <div class="brand-pill">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-right: 6px;"><path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z"/></svg>
          AI 驱动的红墨创作助手
        </div>
        <div class="platform-slogan">
          让传播不再需要门槛，让创作从未如此简单
        </div>
        <h1 class="page-title">灵感一触即发</h1>
        <p class="page-subtitle">输入你的创意主题，让 AI 帮你生成爆款标题、正文和封面图</p>
      </div>

      <!-- Search Box (Composer Style) -->
      <div class="composer-container">
        <div class="composer-input-wrapper">
          <div class="search-icon-static">
             <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M21 21L16.65 16.65M19 11C19 15.4183 15.4183 19 11 19C6.58172 19 3 15.4183 3 11C3 6.58172 6.58172 3 11 3C15.4183 3 19 6.58172 19 11Z" stroke="#999" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </div>
          <textarea
            ref="textareaRef"
            v-model="topic"
            class="composer-textarea"
            placeholder="输入主题，例如：秋季显白美甲..."
            @keydown.enter.prevent="handleEnter"
            @input="adjustHeight"
            :disabled="loading"
            rows="1"
          ></textarea>
        </div>

        <!-- 已上传图片预览 -->
        <div v-if="uploadedImages.length > 0" class="uploaded-images-preview">
          <div
            v-for="(img, idx) in uploadedImages"
            :key="idx"
            class="uploaded-image-item"
          >
            <img :src="img.preview" :alt="`图片 ${idx + 1}`" />
            <button class="remove-image-btn" @click="removeImage(idx)">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="18" y1="6" x2="6" y2="18"></line>
                <line x1="6" y1="6" x2="18" y2="18"></line>
              </svg>
            </button>
          </div>
          <div class="upload-hint">
            这些图片将用于生成封面和内容参考
          </div>
        </div>

        <!-- Toolbar -->
        <div class="composer-toolbar">
          <div class="toolbar-left">
            <label class="tool-btn" :class="{ 'active': uploadedImages.length > 0 }" title="上传参考图">
              <input
                type="file"
                accept="image/*"
                multiple
                @change="handleImageUpload"
                :disabled="loading"
                style="display: none;"
              />
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
                <circle cx="8.5" cy="8.5" r="1.5"></circle>
                <polyline points="21 15 16 10 5 21"></polyline>
              </svg>
              <span v-if="uploadedImages.length > 0" class="badge-count">{{ uploadedImages.length }}</span>
            </label>
          </div>
          <div class="toolbar-right">
            <button
              class="btn btn-primary generate-btn"
              @click="handleGenerate"
              :disabled="!topic.trim() || loading"
            >
              <span v-if="loading" class="spinner-sm"></span>
              <span v-else>生成大纲</span>
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Quick Scenarios & Dashboard -->
    <div class="content-section">
    <!-- Dashboard Grid -->
    <div class="dashboard-grid">

      <!-- Recent Activity (Mockup) -->
      <div class="card feature-card">
        <div class="card-header">
          <div class="header-left">
             <div class="icon-box purple">
               <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20h9"></path><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"></path></svg>
             </div>
             <h3 class="section-title-sm">最近创作</h3>
          </div>
          <button class="btn-text" @click="router.push('/history')">全部记录</button>
        </div>

        <div v-if="recentRecords.length > 0" class="recent-list">
          <div v-for="record in recentRecords" :key="record.id" class="recent-item" @click="loadRecord(record)">
            <div class="recent-icon">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" color="#666"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>
            </div>
            <div class="recent-info">
              <div class="recent-title">{{ record.title }}</div>
              <div class="recent-date">{{ formatDate(record.updated_at) }}</div>
            </div>
            <div class="recent-arrow">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"></polyline></svg>
            </div>
          </div>
        </div>
        <div v-else class="empty-state-mini">
          <p>暂无最近记录</p>
        </div>
      </div>

      <!-- Trending -->
      <div class="card feature-card">
        <div class="card-header">
          <div class="header-left">
             <div class="icon-box orange">
               <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"></polyline><polyline points="17 6 23 6 23 12"></polyline></svg>
             </div>
             <h3 class="section-title-sm">全站热搜</h3>
          </div>
          <span class="refresh-icon">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M23 4v6h-6"></path><path d="M1 20v-6h6"></path><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path></svg>
          </span>
        </div>
        <div class="trend-list">
          <div class="trend-item">
            <span class="trend-rank rank-1">1</span>
            <span class="trend-name">#OOTD 每日穿搭</span>
            <span class="trend-hot">
               <svg width="12" height="12" viewBox="0 0 24 24" fill="#FF4D4F" stroke="#FF4D4F" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-right: 4px;"><path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.1.2-2.2.5-3.3a7 7 0 0 0 3 2.8Z"/></svg>
               234w
            </span>
          </div>
          <div class="trend-item">
            <span class="trend-rank rank-2">2</span>
            <span class="trend-name">#探店日记</span>
            <span class="trend-hot">
               <svg width="12" height="12" viewBox="0 0 24 24" fill="#FF6B81" stroke="#FF6B81" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-right: 4px;"><path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.1.2-2.2.5-3.3a7 7 0 0 0 3 2.8Z"/></svg>
               189w
            </span>
          </div>
          <div class="trend-item">
            <span class="trend-rank rank-3">3</span>
            <span class="trend-name">#低脂减肥餐</span>
            <span class="trend-hot">
               <svg width="12" height="12" viewBox="0 0 24 24" fill="#FF9CA8" stroke="#FF9CA8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-right: 4px;"><path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.1.2-2.2.5-3.3a7 7 0 0 0 3 2.8Z"/></svg>
               156w
            </span>
          </div>
          <div class="trend-item">
            <span class="trend-rank">4</span>
            <span class="trend-name">#家居改造</span>
            <span class="trend-hot">120w</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 首页页脚版权 -->
    <footer class="home-footer">
      <div class="footer-copyright">
        © 2025 <a href="https://github.com/HisMax/RedInk" target="_blank" rel="noopener noreferrer">RedInk</a> by 默子 (Histone)
      </div>
      <div class="footer-license-info">
        Licensed under <a href="https://creativecommons.org/licenses/by-nc-sa/4.0/" target="_blank" rel="noopener noreferrer">CC BY-NC-SA 4.0</a>
      </div>
    </footer>
    </div>

    <div v-if="error" class="error-toast">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>
      {{ error }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useGeneratorStore } from '../stores/generator'
import { generateOutline, getHistoryList, getHistory } from '../api'

const router = useRouter()
const store = useGeneratorStore()

const topic = ref('')
const loading = ref(false)
const error = ref('')
const recentRecords = ref<any[]>([])
const textareaRef = ref<HTMLTextAreaElement | null>(null)
const isExpanded = ref(false)

// 图片网格轮播相关
const showcaseImages = ref<string[]>([])
const scrollOffset = ref(0)
let scrollInterval: ReturnType<typeof setInterval> | null = null

// 加载展示图片列表
const loadShowcaseImages = async () => {
  try {
    const response = await fetch('/assets/showcase_manifest.json')
    const data = await response.json()
    const originalImages = data.covers || []

    // 复制图片数组3次以实现无缝循环
    showcaseImages.value = [...originalImages, ...originalImages, ...originalImages]

    // 启动平滑滚动动画
    if (showcaseImages.value.length > 0) {
      scrollInterval = setInterval(() => {
        scrollOffset.value += 1

        // 计算网格总高度（每行约180px：164px图片 + 16px间距）
        const rowHeight = 180
        const itemsPerRow = 11
        const totalRows = Math.ceil(originalImages.length / itemsPerRow)
        const sectionHeight = totalRows * rowHeight

        // 滚动到第二组末尾时重置到第一组开始位置
        if (scrollOffset.value >= sectionHeight) {
          scrollOffset.value = 0
        }
      }, 30) // 每30ms移动1px，实现流畅滚动
    }
  } catch (e) {
    console.error('加载展示图片失败:', e)
  }
}

// 图片上传相关
interface UploadedImage {
  file: File
  preview: string
}
const uploadedImages = ref<UploadedImage[]>([])

const adjustHeight = () => {
  const el = textareaRef.value
  if (!el) return
  
  el.style.height = 'auto'
  const newHeight = Math.max(64, Math.min(el.scrollHeight, 200)) // Min 64px, Max 200px
  el.style.height = newHeight + 'px'
  
  isExpanded.value = newHeight > 64
}

const handleEnter = (e: KeyboardEvent) => {
  if (e.shiftKey) return // Allow multiline
  handleGenerate()
}

// 处理图片上传
const handleImageUpload = (event: Event) => {
  const target = event.target as HTMLInputElement
  if (!target.files) return

  const files = Array.from(target.files)
  files.forEach((file) => {
    // 限制最多 5 张图片
    if (uploadedImages.value.length >= 5) {
      error.value = '最多只能上传 5 张图片'
      return
    }
    // 创建预览 URL
    const preview = URL.createObjectURL(file)
    uploadedImages.value.push({ file, preview })
  })

  // 清空 input，允许重复选择同一文件
  target.value = ''
}

// 移除图片
const removeImage = (index: number) => {
  const img = uploadedImages.value[index]
  // 释放预览 URL
  URL.revokeObjectURL(img.preview)
  uploadedImages.value.splice(index, 1)
}

const loadRecent = async () => {
  try {
    const res = await getHistoryList(1, 4)
    if (res.success) {
      recentRecords.value = res.records
    }
  } catch (e) {
    // ignore
  }
}

const formatDate = (str: string) => {
  const d = new Date(str)
  return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours()}:${d.getMinutes().toString().padStart(2, '0')}`
}

const loadRecord = async (record: any) => {
   // Simple load for edit
   try {
     const res = await getHistory(record.id)
     if (res.success && res.record) {
        store.setTopic(res.record.title)
        store.setOutline(res.record.outline.raw, res.record.outline.pages)
        store.recordId = res.record.id
        router.push('/outline')
     }
   } catch(e) {
     console.error(e)
   }
}

const handleGenerate = async () => {
  if (!topic.value.trim()) return

  loading.value = true
  error.value = ''

  try {
    // 获取上传的图片文件列表
    const imageFiles = uploadedImages.value.map(img => img.file)

    const result = await generateOutline(
      topic.value.trim(),
      imageFiles.length > 0 ? imageFiles : undefined
    )

    if (result.success && result.pages) {
      store.setTopic(topic.value.trim())
      store.setOutline(result.outline || '', result.pages)
      store.recordId = null  // 重置历史记录ID,确保创建新记录

      // 如果有上传图片，保存到 store 中用于图片生成
      if (imageFiles.length > 0) {
        store.userImages = imageFiles
      } else {
        store.userImages = []
      }

      // 清理预览 URL
      uploadedImages.value.forEach(img => URL.revokeObjectURL(img.preview))
      uploadedImages.value = []

      router.push('/outline')
    } else {
      error.value = result.error || '生成大纲失败'
    }
  } catch (err: any) {
    error.value = err.message || '网络错误，请重试'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadRecent()
  loadShowcaseImages()
})

onUnmounted(() => {
  if (scrollInterval) {
    clearInterval(scrollInterval)
  }
})
</script>

<style scoped>
/* 图片网格轮播背景 */
.showcase-background {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100vh;
  z-index: -1;
  overflow: hidden;
}

.showcase-grid {
  display: grid;
  grid-template-columns: repeat(11, 1fr);
  gap: 16px;
  padding: 20px;
  width: 100%;
  will-change: transform;
}

.showcase-item {
  width: 100%;
  aspect-ratio: 3 / 4;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

.showcase-item img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.showcase-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(
    to bottom,
    rgba(255, 255, 255, 0.7) 0%,
    rgba(255, 255, 255, 0.65) 30%,
    rgba(255, 255, 255, 0.6) 100%
  );
  backdrop-filter: blur(2px);
}

.home-container {
  max-width: 1100px;
  padding-top: 10px;
  position: relative;
  z-index: 1;
}

/* Section Headers */
.section-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  margin-bottom: 16px;
  padding: 0 4px;
}

.section-header h3 {
  font-size: 18px;
  font-weight: 700;
  color: var(--text-main);
}

.link-more {
  font-size: 13px;
  color: var(--text-sub);
  cursor: pointer;
}
.link-more:hover { color: var(--primary); }

/* Hero Section */
.hero-section {
  text-align: center;
  margin-bottom: 40px;
  padding: 50px 60px;
  animation: fadeIn 0.6s ease-out;
  background: rgba(255, 255, 255, 0.95);
  border-radius: 24px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.06);
  backdrop-filter: blur(10px);
}

/* Content Section */
.content-section {
  background: rgba(255, 255, 255, 0.95);
  border-radius: 24px;
  padding: 40px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.06);
  backdrop-filter: blur(10px);
}

.hero-content {
  margin-bottom: 36px;
}

.brand-pill {
  display: inline-block;
  padding: 6px 16px;
  background: rgba(255, 36, 66, 0.08);
  color: var(--primary);
  border-radius: 100px;
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 20px;
  letter-spacing: 0.5px;
}

.platform-slogan {
  font-size: 20px;
  font-weight: 600;
  color: var(--text-main);
  margin-bottom: 24px;
  line-height: 1.6;
  letter-spacing: 0.5px;
}

.page-subtitle {
  font-size: 16px;
  color: var(--text-sub);
  margin-top: 12px;
}

/* Search Box */
.search-box-wrapper {
  max-width: 680px;
  margin: 0 auto;
  position: relative;
}

.input-group.big-search {
  position: relative;
}

.search-icon {
  position: absolute;
  left: 24px;
  top: 50%;
  transform: translateY(-50%);
  z-index: 2;
  pointer-events: none;
}

.search-input {
  padding-left: 60px; /* Space for icon */
  padding-right: 190px; /* Space for buttons: 130px (upload) + 40px (width) + spacing */
  padding-top: 18px;
  padding-bottom: 18px;
  min-height: 64px;
  font-size: 16px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.04);
  border-radius: 32px; /* Slightly less rounded for textarea look if multiline, but we want pill shape initially. 32px is half of 64px */
  resize: none;
  overflow-y: auto;
  line-height: 1.6;
  font-family: inherit;
}

/* 当高度增加时，圆角调整一下更好看 */
.input-group.expanded .search-input {
  border-radius: 24px;
}

.search-btn {
  position: absolute;
  right: 8px;
  bottom: 8px; /* Anchor to bottom */
  top: auto;   /* Reset top */
  padding: 0 28px;
  font-size: 15px;
  border-radius: 100px;
  height: 48px; /* Fixed height for button */
  z-index: 5;
}

/* 图片上传按钮 */
.upload-btn {
  position: absolute;
  right: 146px; /* 8px (right margin) + 110px (approx btn width) + gap */
  bottom: 12px; /* Anchor to bottom */
  top: auto;    /* Reset top */
  width: 40px;
  height: 40px;
  border-radius: 10px;
  background: #f5f5f5;
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #666;
  transition: all 0.2s;
  z-index: 5;
}

.upload-btn:hover {
  background: #eee;
  color: var(--primary);
}

.upload-btn.has-images {
  background: rgba(255, 36, 66, 0.1);
  color: var(--primary);
}

.upload-btn span {
  position: absolute;
  top: -4px;
  right: -4px;
  min-width: 18px;
  height: 18px;
  background: var(--primary);
  color: white;
  border-radius: 9px;
  font-size: 11px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 4px;
}

/* 已上传图片预览 */
.uploaded-images-preview {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 16px;
  padding: 16px;
  background: #fafafa;
  border-radius: 12px;
  align-items: center;
}

.uploaded-image-item {
  position: relative;
  width: 60px;
  height: 60px;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.uploaded-image-item img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.remove-image-btn {
  position: absolute;
  top: 2px;
  right: 2px;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.6);
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  opacity: 0;
  transition: opacity 0.2s;
}

.uploaded-image-item:hover .remove-image-btn {
  opacity: 1;
}

.remove-image-btn:hover {
  background: var(--primary);
}

.upload-hint {
  flex: 1;
  font-size: 12px;
  color: var(--text-sub);
  text-align: right;
}

/* Dashboard Grid */
.dashboard-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 24px;
  animation: slideUp 0.6s ease-out 0.2s backwards;
}

.feature-card {
  height: 100%;
  min-height: 280px;
  display: flex;
  flex-direction: column;
  padding: 24px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.section-title-sm {
  font-size: 16px;
  font-weight: 700;
  margin: 0;
}

.icon-box {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
}

.icon-box.purple {
  background: linear-gradient(135deg, #9F7AEA 0%, #805AD5 100%);
  box-shadow: 0 4px 12px rgba(128, 90, 213, 0.2);
}

.icon-box.orange {
  background: linear-gradient(135deg, #F6AD55 0%, #ED8936 100%);
  box-shadow: 0 4px 12px rgba(237, 137, 54, 0.2);
}

.btn-text {
  background: none;
  border: none;
  color: var(--text-sub);
  font-size: 13px;
  cursor: pointer;
}
.btn-text:hover { color: var(--primary); }

/* Recent List */
.recent-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.recent-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border-radius: 12px;
  background: #F9FAFB;
  cursor: pointer;
  transition: all 0.2s;
}

.recent-item:hover {
  background: #F0F2F5;
  transform: translateX(2px);
}

.recent-icon {
  width: 32px;
  height: 32px;
  background: white;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  box-shadow: 0 2px 6px rgba(0,0,0,0.03);
}

.recent-info {
  flex: 1;
  overflow: hidden;
}

.recent-title {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-main);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.recent-date {
  font-size: 12px;
  color: var(--text-sub);
}

.recent-arrow {
  color: var(--text-placeholder);
  font-size: 16px;
}

.empty-state-mini {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-placeholder);
  font-size: 14px;
  background: #FAFAFA;
  border-radius: 12px;
  border: 1px dashed #eee;
}

/* Trend List */
.trend-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.trend-item {
  display: flex;
  align-items: center;
  padding: 12px 0;
  border-bottom: 1px solid #F5F5F5;
}
.trend-item:last-child { border-bottom: none; }

.trend-rank {
  width: 24px;
  text-align: center;
  font-weight: 800;
  font-size: 16px;
  margin-right: 12px;
  color: var(--text-placeholder);
  font-style: italic;
}

.trend-rank.rank-1 { color: #FF2442; }
.trend-rank.rank-2 { color: #FF6B81; }
.trend-rank.rank-3 { color: #FF9CA8; }

.trend-name {
  font-weight: 500;
  color: var(--text-main);
  flex: 1;
  font-size: 14px;
}

.trend-hot {
  font-size: 12px;
  color: var(--text-sub);
}

/* Animations */
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes slideUp {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

.error-toast {
  position: fixed;
  bottom: 32px;
  left: 50%;
  transform: translateX(-50%);
  background: #FF4D4F;
  color: white;
  padding: 12px 24px;
  border-radius: 50px;
  box-shadow: 0 8px 24px rgba(255, 77, 79, 0.3);
  display: flex;
  align-items: center;
  gap: 8px;
  z-index: 1000;
  animation: slideUp 0.3s ease-out;
}

/* Responsive */
@media (max-width: 768px) {
  .showcase-grid {
    grid-template-columns: repeat(3, 1fr);
    gap: 12px;
    padding: 12px;
  }

  .dashboard-grid {
    grid-template-columns: 1fr;
  }

  .scenarios-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

/* 首页页脚样式 */
.home-footer {
  margin-top: 48px;
  padding: 32px 0 16px;
  border-top: 1px solid rgba(0, 0, 0, 0.06);
  text-align: center;
}

.footer-copyright {
  font-size: 14px;
  color: #666;
  font-weight: 500;
  margin-bottom: 8px;
}

.footer-copyright a {
  color: var(--primary);
  text-decoration: none;
  font-weight: 600;
  transition: all 0.2s ease;
}

.footer-copyright a:hover {
  color: var(--primary-hover);
  text-decoration: underline;
}

.footer-license-info {
  font-size: 13px;
  color: #999;
}

.footer-license-info a {
  color: #777;
  text-decoration: none;
  transition: all 0.2s ease;
}

.footer-license-info a:hover {
  color: var(--primary);
  text-decoration: underline;
}
</style>
