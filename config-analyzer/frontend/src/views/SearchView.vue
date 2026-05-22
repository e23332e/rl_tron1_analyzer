<template>
  <div>
    <h2>搜索配置参数</h2>
    <div class="search-box">
      <form @submit.prevent="doSearch">
        <input
          v-model="query"
          type="text"
          placeholder="搜索参数名、值或评价内容，如: pen_joint_torque, 原地踏步..."
          required
        />
        <div style="display: flex; gap: 0.5rem; margin-top: 0.5rem;">
          <button type="submit" :disabled="searching">
            {{ searching ? '搜索中...' : '搜索' }}
          </button>
          <button type="button" @click="doSearchEval" class="secondary" :disabled="searching">
            仅搜索评价
          </button>
        </div>
      </form>
    </div>

    <!-- Results -->
    <div v-if="result">
      <p style="margin-bottom: 1rem; color: var(--pico-muted-color);">
        搜索 "{{ result.query }}" &mdash;
        参数匹配 {{ result.total_param_matches }} 条,
        评价匹配 {{ result.total_eval_matches }} 条
      </p>

      <!-- Param results -->
      <div v-if="result.param_results && result.param_results.length">
        <h3>参数匹配</h3>
        <div v-for="group in result.param_results" :key="group.param_path" class="search-result-group card" style="padding: 0.75rem;">
          <h4 style="margin-bottom:0.25rem;">{{ group.param_path }}</h4>
          <p style="font-size:0.85rem; margin-bottom:0.5rem;">
            <code>{{ group.value_text }}</code>
            <span class="badge badge-muted" style="margin-left:0.5rem;">{{ group.section }}</span>
          </p>
          <div>
            <span
              v-for="run in group.runs"
              :key="run.run_id"
              class="badge badge-info"
              style="margin-right:0.3rem; cursor: pointer;"
              @click="$emit('view-run', run.run_id)"
            >
              {{ run.run_name }}
            </span>
          </div>
        </div>
      </div>

      <!-- Eval results -->
      <div v-if="result.eval_results && result.eval_results.length">
        <h3 style="margin-top:1.5rem;">评价匹配</h3>
        <div v-for="evalItem in result.eval_results" :key="evalItem.id" class="search-result-group card" style="padding: 0.75rem;">
          <div style="display:flex; align-items:center; gap:0.5rem;">
            <span
              class="badge badge-info"
              style="cursor: pointer;"
              @click="$emit('view-run', evalItem.run_id)"
            >
              {{ evalItem.run_name }}
            </span>
            <span style="font-size:0.85rem; color:var(--pico-muted-color);">{{ evalItem.experiment_name }}</span>
          </div>
          <p style="margin-top:0.5rem; white-space:pre-wrap;">{{ evalItem.content }}</p>
        </div>
      </div>

      <!-- No results -->
      <div v-if="!result.param_results.length && !result.eval_results.length && searched" class="empty-state">
        <h3>未找到匹配结果</h3>
        <p>尝试其他关键词</p>
      </div>
    </div>

    <div v-else-if="!searched" class="empty-state">
      <h3>输入关键词搜索</h3>
      <p style="font-size:0.85rem; color:var(--pico-muted-color);">
        可搜索的参数示例: keep_balance, pen_joint, weight, track_lin_vel, gait_command
      </p>
    </div>
  </div>
</template>

<script>
import { ref } from 'vue'
import api from '../api.js'

export default {
  name: 'SearchView',
  emits: ['view-run'],
  setup() {
    const query = ref('')
    const result = ref(null)
    const searched = ref(false)
    const searching = ref(false)

    async function doSearch() {
      if (!query.value.trim()) return
      searching.value = true
      try {
        result.value = await api.search(query.value.trim())
        searched.value = true
      } catch (e) {
        console.error('Search failed:', e)
      } finally {
        searching.value = false
      }
    }

    async function doSearchEval() {
      if (!query.value.trim()) return
      searching.value = true
      try {
        const evalResults = await api.searchEval(query.value.trim())
        result.value = {
          query: query.value.trim(),
          param_results: [],
          eval_results: evalResults.results,
          total_param_matches: 0,
          total_eval_matches: evalResults.total,
        }
        searched.value = true
      } catch (e) {
        console.error('Search failed:', e)
      } finally {
        searching.value = false
      }
    }

    return { query, result, searched, searching, doSearch, doSearchEval }
  },
}
</script>
