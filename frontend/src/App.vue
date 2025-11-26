<template>
  <div id="app">
    <!-- 侧边栏 Sidebar -->
    <aside class="layout-sidebar">
      <div class="logo-area">
        <img src="/logo.png" alt="红墨" class="logo-icon" />
        <span class="logo-text">红墨</span>
      </div>
      
      <nav class="nav-menu">
        <RouterLink to="/" class="nav-item" active-class="active">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7"></rect><rect x="14" y="3" width="7" height="7"></rect><rect x="14" y="14" width="7" height="7"></rect><rect x="3" y="14" width="7" height="7"></rect></svg>
          创作中心
        </RouterLink>
        <RouterLink to="/history" class="nav-item" active-class="active">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>
          历史记录
        </RouterLink>
        <RouterLink to="/settings" class="nav-item" active-class="active">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"></circle><path d="M12 1v6m0 6v6m-6-6h6m6 0h-6"></path><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path></svg>
          系统设置
        </RouterLink>
      </nav>
      
      <div style="margin-top: auto; padding-top: 20px; border-top: 1px solid var(--border-color);">
        <div style="display: flex; align-items: center; gap: 10px;">
          <img src="/logo.png" alt="默子" style="width: 36px; height: 36px; border-radius: 50%; object-fit: cover;" />
          <div>
            <div style="font-size: 14px; font-weight: 600;">默子</div>
            <div style="font-size: 12px; color: var(--text-sub);">mozi</div>
          </div>
        </div>
      </div>
    </aside>

    <!-- 主内容区 -->
    <main class="layout-main">
      <RouterView v-slot="{ Component, route }">
        <component :is="Component" />

        <!-- 全局页脚版权信息（首页除外） -->
        <footer v-if="route.path !== '/'" class="global-footer">
          <div class="footer-content">
            <div class="footer-text">
              © 2025 <a href="https://github.com/HisMax/RedInk" target="_blank" rel="noopener noreferrer">RedInk</a> by 默子 (Histone)
            </div>
            <div class="footer-license">
              Licensed under <a href="https://creativecommons.org/licenses/by-nc-sa/4.0/" target="_blank" rel="noopener noreferrer">CC BY-NC-SA 4.0</a>
            </div>
          </div>
        </footer>
      </RouterView>
    </main>
  </div>
</template>

<script setup lang="ts">
import { RouterView, RouterLink } from 'vue-router'
import { onMounted } from 'vue'
import { setupAutoSave } from './stores/generator'

// 启用自动保存到 localStorage
onMounted(() => {
  setupAutoSave()
})
</script>
