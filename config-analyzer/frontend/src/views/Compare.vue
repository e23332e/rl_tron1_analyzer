<template>
  <div>
    <button @click="$emit('back')" class="secondary" style="margin-bottom:1rem;">&larr; 返回仪表盘</button>

    <!-- Run selector -->
    <div style="margin-bottom: 1rem;">
      <div style="display: flex; gap: 0.5rem; align-items: center; flex-wrap: wrap;">
        <span style="font-weight:600;">选择要对比的运行：</span>
        <select v-for="(id, idx) in selectedIds" :key="idx" v-model="selectedIds[idx]">
          <option value="">-- 选择运行 --</option>
          <option v-for="r in runs" :key="r.id" :value="r.id">{{ r.run_name }} ({{ r.experiment_name }})</option>
        </select>
        <button v-if="selectedIds.length < 4" @click="selectedIds.push('')" class="secondary">+ 添加</button>
        <button v-if="selectedIds.length > 2" @click="selectedIds.pop()" class="secondary">- 移除</button>
        <button @click="doCompare" :disabled="validIds.length < 2">开始对比</button>
      </div>
    </div>

    <!-- Compare tabs -->
    <div v-if="compareResult" style="margin-bottom:1rem;">
      <div class="nav-tabs" style="display:flex; gap:0.25rem;">
        <button
          v-for="t in ['rewards', 'agent']"
          :key="t"
          class="nav-tab"
          :class="{ active: compareTab === t }"
          @click="compareTab = t"
        >{{ t === 'rewards' ? '奖励对比' : 'Agent 参数对比' }}</button>
      </div>
    </div>

    <!-- Reward comparison -->
    <div v-if="compareTab === 'rewards' && rewardCompare">
      <h3>奖励项对比</h3>
      <p style="margin-bottom:0.5rem;">
        <label>
          <input type="checkbox" v-model="showDiffsOnly" /> 仅显示差异
        </label>
      </p>
      <table class="compare-table">
        <thead>
          <tr>
            <th>奖励项</th>
            <th v-for="run in rewardCompare.runs" :key="run.id">
              {{ run.run_name }}
            </th>
            <th>状态</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="term in filteredRewardTerms"
            :key="term.term_name"
            :class="{ diff: !term.identical, same: term.identical }"
          >
            <td><strong>{{ term.term_name }}</strong></td>
            <td v-for="run in rewardCompare.runs" :key="run.id">
              <template v-if="term.values[run.id]">
                <span :class="term.values[run.id].weight > 0 ? 'reward-positive' : 'reward-negative'">
                  {{ term.values[run.id].weight }}
                </span>
              </template>
              <span v-else style="color:var(--pico-muted-color)">-</span>
            </td>
            <td>
              <span :class="term.identical ? 'badge badge-success' : 'badge badge-warning'">
                {{ term.identical ? '相同' : '不同' }}
              </span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Agent comparison -->
    <div v-if="compareTab === 'agent' && agentCompare">
      <h3>Agent 参数对比</h3>
      <p style="margin-bottom:0.5rem;">
        <label>
          <input type="checkbox" v-model="showDiffsOnly" /> 仅显示差异
        </label>
      </p>
      <table class="compare-table">
        <thead>
          <tr>
            <th>参数</th>
            <th v-for="run in agentCompare.runs" :key="run.id">
              {{ run.run_name }}
            </th>
            <th>状态</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="p in filteredAgentParams"
            :key="p.field"
            :class="{ diff: !p.identical, same: p.identical }"
          >
            <td><strong>{{ p.field }}</strong></td>
            <td v-for="run in agentCompare.runs" :key="run.id">
              {{ formatAgentVal(p.values[run.id]) }}
            </td>
            <td>
              <span :class="p.identical ? 'badge badge-success' : 'badge badge-warning'">
                {{ p.identical ? '相同' : '不同' }}
              </span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Delta analysis (for 2 runs) -->
    <div v-if="selectedIds.length === 2 && delta && validIds.length === 2" style="margin-top:2rem;">
      <h3 class="section-title">变化分析 (Delta)</h3>

      <div v-if="delta.reward_changes" class="card">
        <h4>奖励变化</h4>
        <div v-if="delta.reward_changes.modified.length">
          <p style="font-weight:600; color:var(--warning-color);">修改的奖励项:</p>
          <ul>
            <li v-for="c in delta.reward_changes.modified" :key="c.term">
              {{ c.term }}: {{ c.from }} &rarr; {{ c.to }}
            </li>
          </ul>
        </div>
        <div v-if="delta.reward_changes.added.length">
          <p style="font-weight:600; color:var(--success-color);">新增的奖励项:</p>
          <ul><li v-for="c in delta.reward_changes.added" :key="c">{{ c }}</li></ul>
        </div>
        <div v-if="delta.reward_changes.removed.length">
          <p style="font-weight:600; color:var(--danger-color);">移除的奖励项:</p>
          <ul><li v-for="c in delta.reward_changes.removed" :key="c">{{ c }}</li></ul>
        </div>
        <p v-if="!delta.reward_changes.modified.length && !delta.reward_changes.added.length && !delta.reward_changes.removed.length">
          无变化
        </p>
      </div>

      <div v-if="delta.agent_changes && Object.keys(delta.agent_changes).length" class="card">
        <h4>Agent 参数变化</h4>
        <ul>
          <li v-for="(val, key) in delta.agent_changes" :key="key">
            {{ key }}: {{ val.from }} &rarr; {{ val.to }}
          </li>
        </ul>
      </div>

      <div v-if="delta.event_changes" class="card">
        <h4>事件变化</h4>
        <div v-if="delta.event_changes.added.length">
          <p style="font-weight:600; color:var(--success-color);">新增事件:</p>
          <ul><li v-for="c in delta.event_changes.added" :key="c">{{ c }}</li></ul>
        </div>
        <div v-if="delta.event_changes.removed.length">
          <p style="font-weight:600; color:var(--danger-color);">移除事件:</p>
          <ul><li v-for="c in delta.event_changes.removed" :key="c">{{ c }}</li></ul>
        </div>
      </div>
    </div>

    <div v-if="!compareResult && !loading" class="empty-state">
      <h3>请选择 2-4 条运行记录进行对比</h3>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted, watch } from 'vue'
import api from '../api.js'

export default {
  name: 'Compare',
  props: { initialRunIds: { type: Array, default: () => [] } },
  emits: ['back'],
  setup(props) {
    const runs = ref([])
    const selectedIds = ref([...props.initialRunIds.map(String), '', ''].slice(0, 2))
    const validIds = computed(() => selectedIds.value.filter(id => id).map(Number))
    const compareResult = ref(null)
    const rewardCompare = ref(null)
    const agentCompare = ref(null)
    const delta = ref(null)
    const compareTab = ref('rewards')
    const showDiffsOnly = ref(false)
    const loading = ref(false)

    const filteredRewardTerms = computed(() => {
      if (!rewardCompare.value) return []
      if (!showDiffsOnly.value) return rewardCompare.value.terms
      return rewardCompare.value.terms.filter(t => !t.identical)
    })

    const filteredAgentParams = computed(() => {
      if (!agentCompare.value) return []
      if (!showDiffsOnly.value) return agentCompare.value.params
      return agentCompare.value.params.filter(p => !p.identical)
    })

    function formatAgentVal(val) {
      if (val === null || val === undefined) return '-'
      if (Array.isArray(val)) return `[${val.join(', ')}]`
      return String(val)
    }

    async function doCompare() {
      if (validIds.value.length < 2) return
      loading.value = true
      try {
        const [rewards, agent] = await Promise.all([
          api.compareRewards(validIds.value),
          api.compareAgent(validIds.value),
        ])
        rewardCompare.value = rewards
        agentCompare.value = agent
        compareResult.value = true

        if (validIds.value.length === 2) {
          try {
            delta.value = await api.compareDelta(validIds.value[0], validIds.value[1])
          } catch (e) { delta.value = null }
        }
      } catch (e) {
        console.error('Compare failed:', e)
      } finally {
        loading.value = false
      }
    }

    onMounted(async () => {
      try {
        const data = await api.getRuns()
        runs.value = data
        if (props.initialRunIds.length >= 2) {
          selectedIds.value = props.initialRunIds.map(String)
          await doCompare()
        }
      } catch (e) {
        console.error(e)
      }
    })

    return {
      runs, selectedIds, validIds, compareResult, rewardCompare,
      agentCompare, delta, compareTab, showDiffsOnly, loading,
      filteredRewardTerms, filteredAgentParams,
      formatAgentVal, doCompare,
    }
  },
}
</script>
