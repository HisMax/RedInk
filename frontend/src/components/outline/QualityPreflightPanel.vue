<template>
  <section class="quality-panel">
    <div class="quality-panel__header">
      <div>
        <h2>发布文案与质量评分</h2>
        <p>标题、正文、标签与发布风险会在这里汇总。</p>
      </div>
      <button class="btn btn-primary" @click="generateAndEvaluate" :disabled="busy || !store.outline.raw">
        <span v-if="busy" class="spinner-sm"></span>
        {{ busy ? '处理中...' : '生成并评分' }}
      </button>
    </div>

    <div v-if="store.content.status === 'done'" class="quality-panel__content">
      <div>
        <h3>推荐标题</h3>
        <ol>
          <li v-for="title in store.content.titles" :key="title">{{ title }}</li>
        </ol>
      </div>
      <div>
        <h3>正文</h3>
        <p class="copy">{{ store.content.copywriting }}</p>
      </div>
      <div>
        <h3>标签</h3>
        <div class="tags">
          <span v-for="tag in store.content.tags" :key="tag">#{{ tag }}</span>
        </div>
      </div>
    </div>

    <div v-if="store.qualityStatus === 'evaluating'" class="quality-status">
      <span class="status-dot"></span>
      正在评估内容质量...
    </div>

    <div v-if="store.qualityStatus === 'done' && store.quality" class="quality-score" :class="store.quality.decision">
      <div class="score-main">
        <strong>{{ store.quality.overall }}</strong>
        <span>{{ decisionText }}</span>
      </div>
      <div class="score-grid">
        <span>Hook {{ store.quality.hook_strength }}</span>
        <span>信息密度 {{ store.quality.information_density }}</span>
        <span>用户收益 {{ store.quality.user_value }}</span>
        <span>合规风险 {{ store.quality.compliance_risk }}</span>
      </div>
      <div v-if="store.quality.issues.length" class="quality-list">
        <h3>主要问题</h3>
        <ul>
          <li v-for="issue in store.quality.issues" :key="issue">{{ issue }}</li>
        </ul>
      </div>
      <div v-if="store.quality.suggestions.length" class="quality-list">
        <h3>修改建议</h3>
        <ul>
          <li v-for="suggestion in store.quality.suggestions" :key="suggestion">{{ suggestion }}</li>
        </ul>
      </div>
      <button
        v-if="store.quality.decision === 'revise'"
        class="btn btn-secondary"
        @click="requestRevision"
        :disabled="busy"
      >
        按建议改写
      </button>
    </div>

    <p v-if="store.qualityStatus === 'error'" class="quality-error">{{ store.qualityError }}</p>
  </section>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { evaluateContent, generateContent, reviseContent, updateHistory } from '../../api'
import { useGeneratorStore } from '../../stores/generator'

const store = useGeneratorStore()
const busy = ref(false)

const decisionText = computed(() => {
  if (!store.quality) return ''
  const labels = {
    approve: '可以进入图片生成',
    revise: '建议先改写',
    block: '暂不建议生成图片'
  }
  return labels[store.quality.decision]
})

async function persistQuality() {
  if (!store.recordId || !store.quality || !store.publishGate) return
  await updateHistory(store.recordId, {
    trace_id: store.traceId,
    content: {
      titles: store.content.titles,
      copywriting: store.content.copywriting,
      tags: store.content.tags
    },
    quality: {
      quality_score: store.quality,
      publish_gate: store.publishGate
    }
  })
}

async function generateAndEvaluate() {
  if (busy.value) return
  busy.value = true
  store.startContentGeneration()
  store.startQualityEvaluation()

  try {
    const content = await generateContent(store.topic, store.outline.raw)
    if (!content.success || !content.titles || !content.copywriting || !content.tags) {
      store.setContentError(content.error || '内容生成失败')
      store.setQualityError(content.error || '内容生成失败')
      return
    }

    store.setContent(content.titles, content.copywriting, content.tags)

    const quality = await evaluateContent({
      topic: store.topic,
      outline: store.outline.raw,
      titles: content.titles,
      copywriting: content.copywriting,
      tags: content.tags,
      trace_id: store.traceId
    })

    if (!quality.success || !quality.quality_score || !quality.publish_gate) {
      store.setQualityError(quality.error || '质量评分失败')
      return
    }

    store.setQualityResult(quality.quality_score, quality.publish_gate, quality.trace_id)
    await persistQuality()
  } catch (error: any) {
    const message = error.message || '质量评分失败'
    if (store.content.status === 'generating') {
      store.setContentError(message)
    }
    store.setQualityError(message)
  } finally {
    busy.value = false
  }
}

async function requestRevision() {
  if (!store.quality || busy.value) return
  busy.value = true

  try {
    const result = await reviseContent({
      topic: store.topic,
      outline: store.outline.raw,
      titles: store.content.titles,
      copywriting: store.content.copywriting,
      tags: store.content.tags,
      quality_score: store.quality,
      trace_id: store.traceId
    })

    if (!result.success || !result.revision) {
      store.setQualityError(result.error || '改写失败')
      return
    }

    store.applyRevision(result.revision)
    if (store.recordId) {
      await updateHistory(store.recordId, {
        trace_id: store.traceId,
        content: {
          titles: result.revision.titles,
          copywriting: result.revision.copywriting,
          tags: result.revision.tags
        },
        revision_entry: result.revision
      })
    }
  } catch (error: any) {
    store.setQualityError(error.message || '改写失败')
  } finally {
    busy.value = false
  }
}
</script>

<style scoped>
.quality-panel {
  max-width: 1200px;
  margin: 0 auto 24px auto;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 24px;
  box-shadow: var(--shadow-sm);
}

.quality-panel__header {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: center;
}

.quality-panel__header h2,
.quality-panel__content h3,
.quality-list h3 {
  margin: 0 0 8px 0;
}

.quality-panel__header h2 {
  font-size: 20px;
  color: var(--text-main);
}

.quality-panel__header p {
  margin: 0;
  color: var(--text-sub);
}

.quality-panel__content {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
  margin-top: 20px;
}

.quality-panel__content > div {
  min-width: 0;
  background: var(--bg-body);
  border-radius: var(--radius-sm);
  padding: 16px;
}

.quality-panel__content h3,
.quality-list h3 {
  font-size: 15px;
  color: var(--text-main);
}

.quality-panel__content ol,
.quality-list ul {
  margin: 0;
  padding-left: 20px;
  color: var(--text-main);
  line-height: 1.7;
}

.copy {
  margin: 0;
  white-space: pre-wrap;
  color: var(--text-main);
  line-height: 1.7;
}

.tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.tags span {
  color: var(--primary);
  background: var(--primary-light);
  border-radius: 999px;
  padding: 6px 10px;
}

.quality-status {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 16px;
  color: var(--text-sub);
  font-size: 14px;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--primary);
}

.quality-score {
  margin-top: 20px;
  border-radius: var(--radius-sm);
  padding: 16px;
  border: 1px solid var(--border-color);
}

.quality-score.approve {
  background: #f0fdf4;
}

.quality-score.revise {
  background: #fffbeb;
}

.quality-score.block {
  background: #fef2f2;
}

.score-main {
  display: flex;
  align-items: baseline;
  gap: 12px;
}

.score-main strong {
  font-size: 32px;
  color: var(--text-main);
}

.score-main span {
  color: var(--text-sub);
  font-weight: 600;
}

.score-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
  margin-top: 12px;
  color: var(--text-sub);
  font-size: 14px;
}

.score-grid span {
  background: rgba(255, 255, 255, 0.72);
  border-radius: 6px;
  padding: 8px;
}

.quality-list {
  margin-top: 14px;
}

.quality-score .btn {
  margin-top: 14px;
}

.quality-error {
  margin: 16px 0 0 0;
  color: #dc2626;
}

@media (max-width: 768px) {
  .quality-panel__header,
  .quality-panel__content,
  .score-grid {
    grid-template-columns: 1fr;
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
