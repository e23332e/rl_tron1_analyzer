<template>
  <div>
    <div class="filters-bar">
      <button @click="showImport = true">导入配置</button>
      <button @click="showBatchImport = true" class="secondary">批量导入</button>
      <button @click="refreshRuns" class="secondary">刷新</button>
      <select v-model="filterRobot" @change="applyFilters">
        <option value="">全部机器人</option>
        <option value="SF">SF</option>
        <option value="PF">PF</option>
        <option value="WF">WF</option>
      </select>
      <select v-model="filterTask" @change="applyFilters">
        <option value="">全部任务</option>
        <option value="Walk">Walk</option>
        <option value="Flat">Flat</option>
        <option value="Stand">Stand</option>
      </select>
      <span v-if="runs.length" style="margin-left: auto; color: var(--pico-muted-color);">
        共 {{ runs.length }} 条记录
      </span>
    </div>

    <!-- Stats cards -->
    <div class="stats-grid" v-if="stats">
      <div class="stat-card">
        <div class="stat-value">{{ stats.total_runs }}</div>
        <div class="stat-label">训练运行</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ stats.total_experiments }}</div>
        <div class="stat-label">实验组</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ stats.unique_params }}</div>
        <div class="stat-label">独立参数</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ compareIds.length }}</div>
        <div class="stat-label">已选对比</div>
      </div>
    </div>

    <!-- Compare action bar -->
    <div v-if="compareIds.length >= 2" style="margin-bottom: 1rem;">
      <button @click="$emit('compare-runs', compareIds)">
        对比选中的 {{ compareIds.length }} 条记录
      </button>
      <button @click="compareIds = []" class="secondary" style="margin-left: 0.5rem;">取消选择</button>
    </div>

    <!-- Table -->
    <div v-if="loading" class="empty-state"><p>加载中...</p></div>
    <div v-else-if="filteredRuns.length === 0" class="empty-state">
      <h3>暂无数据</h3>
      <p>点击"导入配置"或"批量导入"添加训练记录</p>
    </div>
    <table v-else class="data-table">
      <thead>
        <tr>
          <th style="width:40px">#</th>
          <th @click="sortBy('run_name')">运行名称 {{ sortIcon('run_name') }}</th>
          <th @click="sortBy('experiment_name')">实验 {{ sortIcon('experiment_name') }}</th>
          <th @click="sortBy('robot_type')">机器人 {{ sortIcon('robot_type') }}</th>
          <th @click="sortBy('task_variant')">任务 {{ sortIcon('task_variant') }}</th>
          <th>奖励项</th>
          <th @click="sortBy('imported_at')">导入时间 {{ sortIcon('imported_at') }}</th>
          <th>评价</th>
          <th>操作</th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="run in sortedRuns"
          :key="run.id"
          class="selectable"
          :class="{ selected: compareIds.includes(run.id) }"
          @click="viewRun(run.id)"
        >
          <td>
            <input
              type="checkbox"
              :checked="compareIds.includes(run.id)"
              @click.stop
              @change="toggleCompare(run.id)"
            />
          </td>
          <td><strong>{{ run.run_name }}</strong></td>
          <td>{{ run.experiment_name }}</td>
          <td><span class="badge badge-info">{{ run.robot_type }}</span></td>
          <td><span class="badge badge-muted">{{ run.task_variant }}</span></td>
          <td>{{ run.reward_count }}</td>
          <td>{{ formatDate(run.imported_at) }}</td>
          <td>
            <span v-if="run.eval_content" class="badge badge-warning">有评价</span>
            <span v-else style="color: var(--pico-muted-color)">-</span>
          </td>
          <td>
            <button
              @click.stop="deleteRun(run.id)"
              class="secondary"
              style="padding: 0.15rem 0.5rem; font-size: 0.75rem;"
            >删除</button>
          </td>
        </tr>
      </tbody>
    </table>

    <!-- Import dialog -->
    <ImportDialog
      v-if="showImport"
      @close="showImport = false"
      @imported="onImported"
    />

    <!-- Batch import dialog -->
    <div v-if="showBatchImport" class="modal-overlay" @click.self="showBatchImport = false">
      <div class="modal-content">
        <h3>批量导入</h3>
        <p>从指定目录批量导入 YAML 配置文件：</p>
        <input
          v-model="batchDir"
          type="text"
          placeholder="目录路径，留空使用默认目录"
          style="width: 100%"
        />
        <p style="font-size:0.8rem; color:var(--pico-muted-color);">
          需要包含 params/env.yaml 和 params/agent.yaml
        </p>
        <div style="display:flex; gap:0.5rem; margin-top:1rem;">
          <button @click="doBatchImport" :disabled="batchLoading">
            {{ batchLoading ? '导入中...' : '开始导入' }}
          </button>
          <button @click="showBatchImport = false" class="secondary">取消</button>
        </div>
        <div v-if="batchResult" style="margin-top:1rem;">
          <p :class="batchResult.imported > 0 ? 'reward-positive' : 'reward-negative'">
            {{ batchResult.imported > 0 ? '成功导入 ' + batchResult.imported + ' 条记录' : '没有找到新配置' }}
          </p>
          <ul v-if="batchResult.errors && batchResult.errors.length">
            <li v-for="(err, i) in batchResult.errors" :key="i" style="color: var(--danger-color)">
              {{ err.run }}: {{ err.error }}
            </li>
          </ul>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted } from 'vue'
import api from '../api.js'
import ImportDialog from '../components/ImportDialog.vue'

export default {
  name: 'Dashboard',
  components: { ImportDialog },
  emits: ['view-run', 'compare-runs'],
  setup(props, { emit }) {
    const runs = ref([])
    const stats = ref(null)
    const loading = ref(true)
    const compareIds = ref([])
    const showImport = ref(false)
    const showBatchImport = ref(false)
    const batchDir = ref('')
    const batchLoading = ref(false)
    const batchResult = ref(null)
    const sortField = ref('imported_at')
    const sortDir = ref('desc')
    const filterRobot = ref('')
    const filterTask = ref('')

    async function refreshRuns() {
      loading.value = true
      try {
        const data = await api.getRuns()
        runs.value = data
        stats.value = await api.getOverview()
      } catch (e) {
        console.error('Failed to load runs:', e)
      } finally {
        loading.value = false
      }
    }

    const filteredRuns = computed(() => {
      let result = runs.value
      if (filterRobot.value) {
        result = result.filter(r => r.robot_type === filterRobot.value)
      }
      if (filterTask.value) {
        result = result.filter(r => r.task_variant === filterTask.value)
      }
      return result
    })

    const sortedRuns = computed(() => {
      const arr = [...filteredRuns.value]
      arr.sort((a, b) => {
        const va = a[sortField.value] || ''
        const vb = b[sortField.value] || ''
        if (va < vb) return sortDir.value === 'asc' ? -1 : 1
        if (va > vb) return sortDir.value === 'asc' ? 1 : -1
        return 0
      })
      return arr
    })

    function sortBy(field) {
      if (sortField.value === field) {
        sortDir.value = sortDir.value === 'asc' ? 'desc' : 'asc'
      } else {
        sortField.value = field
        sortDir.value = 'asc'
      }
    }

    function sortIcon(field) {
      if (sortField.value !== field) return ''
      return sortDir.value === 'asc' ? ' \u2191' : ' \u2193'
    }

    function viewRun(runId) {
      emit('view-run', runId)
    }

    function toggleCompare(runId) {
      const idx = compareIds.value.indexOf(runId)
      if (idx >= 0) {
        compareIds.value.splice(idx, 1)
      } else {
        compareIds.value.push(runId)
      }
    }

    function applyFilters() {}

    async function deleteRun(runId) {
      if (!confirm('确认删除此运行记录？')) return
      try {
        await api.deleteRun(runId)
        await refreshRuns()
      } catch (e) {
        alert('删除失败: ' + e.message)
      }
    }

    function formatDate(ts) {
      if (!ts) return '-'
      return new Date(ts * 1000).toLocaleString('zh-CN')
    }

    function onImported() {
      showImport.value = false
      refreshRuns()
    }

    async function doBatchImport() {
      batchLoading.value = true
      batchResult.value = null
      try {
        const result = await api.importDirectory(batchDir.value || undefined)
        batchResult.value = result
        if (result.imported > 0) refreshRuns()
      } catch (e) {
        batchResult.value = { imported: 0, errors: [{ run: '', error: e.message }] }
      } finally {
        batchLoading.value = false
      }
    }

    onMounted(refreshRuns)

    return {
      runs, stats, loading, compareIds, showImport, showBatchImport,
      batchDir, batchLoading, batchResult, sortField, sortDir,
      filterRobot, filterTask, filteredRuns, sortedRuns,
      refreshRuns, sortBy, sortIcon, viewRun, toggleCompare,
      applyFilters, deleteRun, formatDate, onImported, doBatchImport,
    }
  },
}
</script>
