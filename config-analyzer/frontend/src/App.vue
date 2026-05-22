<template>
  <div id="app-root">
    <nav class="nav-bar">
      <h1>RL Config Analyzer</h1>
      <div class="nav-tabs">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          class="nav-tab"
          :class="{ active: activeTab === tab.id }"
          @click="switchTab(tab.id)"
        >{{ tab.label }}</button>
      </div>
      <div class="nav-actions">
        <button @click="activeTab = 'dashboard'; selectedRun = null" class="secondary">首页</button>
      </div>
    </nav>

    <main class="main-content">
      <Dashboard
        v-if="activeTab === 'dashboard'"
        @view-run="viewRun"
        @compare-runs="startCompare"
      />
      <RunDetail
        v-else-if="activeTab === 'detail' && selectedRun"
        :runId="selectedRun"
        @back="activeTab = 'dashboard'"
      />
      <Compare
        v-else-if="activeTab === 'compare'"
        :initialRunIds="compareRunIds"
        @back="activeTab = 'dashboard'; compareRunIds = []"
      />
      <SearchView v-else-if="activeTab === 'search'" @view-run="viewRun" />
    </main>
  </div>
</template>

<script>
import { ref } from 'vue'
import Dashboard from './views/Dashboard.vue'
import RunDetail from './views/RunDetail.vue'
import Compare from './views/Compare.vue'
import SearchView from './views/SearchView.vue'

export default {
  name: 'App',
  components: { Dashboard, RunDetail, Compare, SearchView },
  setup() {
    const tabs = [
      { id: 'dashboard', label: '仪表盘' },
      { id: 'compare', label: '对比分析' },
      { id: 'search', label: '搜索' },
    ]
    const activeTab = ref('dashboard')
    const selectedRun = ref(null)
    const compareRunIds = ref([])

    function switchTab(id) {
      activeTab.value = id
      if (id !== 'detail') selectedRun.value = null
    }

    function viewRun(runId) {
      selectedRun.value = runId
      activeTab.value = 'detail'
    }

    function startCompare(ids) {
      compareRunIds.value = ids
      activeTab.value = 'compare'
    }

    return { tabs, activeTab, selectedRun, compareRunIds, switchTab, viewRun, startCompare }
  },
}
</script>
