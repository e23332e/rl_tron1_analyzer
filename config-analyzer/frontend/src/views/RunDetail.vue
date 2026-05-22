<template>
  <div>
    <button @click="$emit('back')" class="secondary" style="margin-bottom:1rem;">&larr; 返回仪表盘</button>

    <div v-if="loading" class="empty-state"><p>加载中...</p></div>
    <div v-else-if="!run" class="empty-state"><p>未找到运行记录</p></div>

    <div v-else class="detail-layout">
      <!-- Left nav -->
      <nav class="detail-nav">
        <a :class="{ active: activeSection === 'overview' }" @click="scrollTo('overview')">概览</a>
        <a :class="{ active: activeSection === 'agent' }" @click="scrollTo('agent')">Agent 配置</a>
        <a :class="{ active: activeSection === 'rewards' }" @click="scrollTo('rewards')">奖励配置</a>
        <a :class="{ active: activeSection === 'events' }" @click="scrollTo('events')">事件配置</a>
        <a :class="{ active: activeSection === 'commands' }" @click="scrollTo('commands')">指令配置</a>
        <a :class="{ active: activeSection === 'evaluation' }" @click="scrollTo('evaluation')">评价记录</a>
        <a :class="{ active: activeSection === 'raw' }" @click="scrollTo('raw')">原始参数</a>
      </nav>

      <!-- Content -->
      <div class="detail-content" ref="contentRef" @scroll="onScroll">
        <!-- Overview -->
        <section id="section-overview">
          <h3 class="section-title">运行概览</h3>
          <div class="config-row"><span class="param-label">运行名称</span><span class="param-value">{{ run.run_name }}</span></div>
          <div class="config-row"><span class="param-label">实验名称</span><span class="param-value">{{ run.experiment_name }}</span></div>
          <div class="config-row"><span class="param-label">机器人类型</span><span class="badge badge-info">{{ run.robot_type }}</span></div>
          <div class="config-row"><span class="param-label">任务类型</span><span class="badge badge-muted">{{ run.task_variant }}</span></div>
          <div class="config-row"><span class="param-label">导入时间</span><span class="param-value">{{ formatDate(run.imported_at) }}</span></div>
          <div class="config-row"><span class="param-label">奖励项数</span><span class="param-value">{{ rewards.length }}</span></div>
          <div class="config-row"><span class="param-label">事件数</span><span class="param-value">{{ events.length }}</span></div>
        </section>

        <!-- Agent config -->
        <section id="section-agent">
          <h3 class="section-title">Agent 配置</h3>
          <div v-if="agent" class="config-rows">
            <div class="config-row"><span class="param-label">算法</span><span class="param-value">{{ agent.algorithm }}</span></div>
            <div class="config-row"><span class="param-label">学习率</span><span class="param-value">{{ agent.learning_rate }}</span></div>
            <div class="config-row"><span class="param-label">Gamma</span><span class="param-value">{{ agent.gamma }}</span></div>
            <div class="config-row"><span class="param-label">Lambda (GAE)</span><span class="param-value">{{ agent.lam }}</span></div>
            <div class="config-row"><span class="param-label">Entropy Coef</span><span class="param-value">{{ agent.entropy_coef }}</span></div>
            <div class="config-row"><span class="param-label">Desired KL</span><span class="param-value">{{ agent.desired_kl }}</span></div>
            <div class="config-row"><span class="param-label">Max Grad Norm</span><span class="param-value">{{ agent.max_grad_norm }}</span></div>
            <div class="config-row"><span class="param-label">Value Loss Coef</span><span class="param-value">{{ agent.value_loss_coef }}</span></div>
            <div class="config-row"><span class="param-label">Clip Param</span><span class="param-value">{{ agent.clip_param }}</span></div>
            <div class="config-row"><span class="param-label">Max Iterations</span><span class="param-value">{{ agent.max_iterations }}</span></div>
            <div class="config-row"><span class="param-label">Num Steps/Env</span><span class="param-value">{{ agent.num_steps }}</span></div>
            <div class="config-row"><span class="param-label">Actor Dims</span><span class="param-value">{{ formatArray(agent.actor_dims) }}</span></div>
            <div class="config-row"><span class="param-label">Critic Dims</span><span class="param-value">{{ formatArray(agent.critic_dims) }}</span></div>
            <div class="config-row"><span class="param-label">Activation</span><span class="param-value">{{ agent.activation }}</span></div>
            <div class="config-row"><span class="param-label">Encoder Dims</span><span class="param-value">{{ formatArray(agent.encoder_dims) }}</span></div>
            <div class="config-row"><span class="param-label">Encoder Output</span><span class="param-value">{{ agent.encoder_output_dim }}</span></div>
            <div class="config-row"><span class="param-label">Obs History Len</span><span class="param-value">{{ agent.obs_history_len }}</span></div>
            <div class="config-row"><span class="param-label">Seed</span><span class="param-value">{{ agent.seed }}</span></div>
            <div class="config-row"><span class="param-label">Save Interval</span><span class="param-value">{{ agent.save_interval }}</span></div>
          </div>
          <div v-else class="empty-state"><p>无 Agent 配置数据</p></div>
        </section>

        <!-- Rewards -->
        <section id="section-rewards">
          <h3 class="section-title">奖励配置 ({{ rewards.length }} 项)</h3>
          <div class="card">
            <h4 style="color: var(--success-color)">正向奖励</h4>
            <ul class="reward-list scroll-section">
              <li v-for="r in posRewards" :key="r.term_name" class="reward-item">
                <span class="reward-icon">+</span>
                <span class="reward-name">{{ r.term_name }}</span>
                <span class="reward-func">{{ r.func }}</span>
                <span class="reward-weight reward-positive">+{{ r.weight }}</span>
              </li>
            </ul>
          </div>
          <div class="card">
            <h4 style="color: var(--danger-color)">负向惩罚</h4>
            <ul class="reward-list scroll-section">
              <li v-for="r in negRewards" :key="r.term_name" class="reward-item">
                <span class="reward-icon">-</span>
                <span class="reward-name">{{ r.term_name }}</span>
                <span class="reward-func">{{ r.func }}</span>
                <span class="reward-weight reward-negative">{{ r.weight }}</span>
              </li>
            </ul>
          </div>
        </section>

        <!-- Events -->
        <section id="section-events">
          <h3 class="section-title">事件/域随机化 ({{ events.length }} 项)</h3>
          <div v-for="mode in ['startup', 'reset', 'interval']" :key="mode" class="card">
            <h4>
              <span class="badge" :class="modeBadgeClass(mode)">{{ modeText(mode) }}</span>
              <span style="font-size:0.85rem; color:var(--pico-muted-color); margin-left:0.5rem;">
                {{ modeEvents(mode).length }} 项
              </span>
            </h4>
            <ul v-if="modeEvents(mode).length" class="event-list">
              <li v-for="e in modeEvents(mode)" :key="e.event_name" class="event-item">
                <span class="event-name">{{ e.event_name }}</span>
                <span class="event-func">{{ e.func }}</span>
              </li>
            </ul>
            <p v-else style="font-size:0.85rem; color:var(--pico-muted-color);">无</p>
          </div>
        </section>

        <!-- Commands -->
        <section id="section-commands">
          <h3 class="section-title">指令配置</h3>
          <div v-if="commands" v-for="(cfg, name) in commands" :key="name" class="card">
            <h4>{{ name }}</h4>
            <div v-for="(val, key) in cfg" :key="key" class="config-row">
              <span class="param-label">{{ key }}</span>
              <span class="param-value">{{ formatValue(val) }}</span>
            </div>
          </div>
          <div v-else class="empty-state"><p>无指令配置数据</p></div>
        </section>

        <!-- Evaluation -->
        <section id="section-evaluation">
          <h3 class="section-title">评价记录</h3>
          <div class="card">
            <!-- Edit mode -->
            <div v-if="editingEval">
              <textarea
                v-model="evalContent"
                rows="5"
                style="width:100%; font-size:0.9rem; line-height:1.6;"
                placeholder="输入评价内容..."
              ></textarea>
              <div style="margin-top: 0.5rem; display: flex; gap: 0.5rem;">
                <button @click="saveEvaluation" :disabled="savingEval">
                  {{ savingEval ? '保存中...' : '保存' }}
                </button>
                <button @click="cancelEditEval" class="secondary">取消</button>
              </div>
              <p v-if="saveMsg" :style="{ color: saveOk ? 'var(--success-color)' : 'var(--danger-color)', marginTop: '0.5rem' }">{{ saveMsg }}</p>
            </div>
            <!-- View mode -->
            <div v-else>
              <div v-if="evaluation && evaluation.content">
                <p style="white-space: pre-wrap; margin-bottom: 0.5rem;">{{ evaluation.content }}</p>
                <div v-if="issues.length" style="margin-bottom: 0.5rem;">
                  <span v-for="issue in issues" :key="issue" class="badge badge-warning" style="margin-right: 0.3rem;">
                    {{ issue }}
                  </span>
                </div>
              </div>
              <p v-else style="color: var(--pico-muted-color);">暂无评价记录</p>
              <button @click="startEditEval" class="secondary" style="margin-top: 0.25rem; font-size: 0.82rem;">编辑评价</button>
            </div>
          </div>
        </section>

        <!-- All Params -->
        <section id="section-raw">
          <h3 class="section-title">全部参数</h3>
          <div v-if="allParams.length">
            <div v-for="p in allParams.slice(0, 200)" :key="p.id" class="config-row">
              <span class="param-label">{{ p.param_path }}</span>
              <span class="param-value">{{ p.value_text }}</span>
            </div>
            <p v-if="allParams.length > 200" style="color: var(--pico-muted-color);">
              ... 共 {{ allParams.length }} 项参数，仅显示前 200 项
            </p>
          </div>
          <div v-else class="empty-state"><p>无参数数据</p></div>
        </section>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted } from 'vue'
import api from '../api.js'

export default {
  name: 'RunDetail',
  props: { runId: { type: Number, required: true } },
  emits: ['back'],
  setup(props) {
    const loading = ref(true)
    const run = ref(null)
    const agent = ref(null)
    const rewards = ref([])
    const events = ref([])
    const commands = ref({})
    const allParams = ref([])
    const evaluation = ref(null)
    const activeSection = ref('overview')

    const posRewards = computed(() => rewards.value.filter(r => r.category === 'reward'))
    const negRewards = computed(() => rewards.value.filter(r => r.category === 'penalty'))
    const issues = computed(() => {
      if (evaluation.value?.parsed_issues) {
        try {
          return typeof evaluation.value.parsed_issues === 'string'
            ? JSON.parse(evaluation.value.parsed_issues)
            : evaluation.value.parsed_issues
        } catch { return [] }
      }
      return []
    })

    function modeEvents(mode) {
      return events.value.filter(e => e.mode === mode)
    }

    function modeBadgeClass(mode) {
      return mode === 'startup' ? 'badge-info' : mode === 'reset' ? 'badge-warning' : 'badge-success'
    }

    function modeText(mode) {
      return mode === 'startup' ? '启动时' : mode === 'reset' ? '重置时' : '间隔触发'
    }

    function formatDate(ts) {
      if (!ts) return '-'
      return new Date(ts * 1000).toLocaleString('zh-CN')
    }

    function formatArray(arr) {
      if (Array.isArray(arr)) return `[${arr.join(', ')}]`
      if (typeof arr === 'string') return arr
      return '-'
    }

    function formatValue(val) {
      if (Array.isArray(val)) return `[${val.join(', ')}]`
      return val
    }

    // Evaluation editing
    const editingEval = ref(false)
    const evalContent = ref('')
    const savingEval = ref(false)
    const saveMsg = ref('')
    const saveOk = ref(false)

    function startEditEval() {
      evalContent.value = evaluation.value?.content || ''
      editingEval.value = true
      saveMsg.value = ''
    }

    function cancelEditEval() {
      editingEval.value = false
      saveMsg.value = ''
    }

    async function saveEvaluation() {
      savingEval.value = true
      saveMsg.value = ''
      try {
        const resp = await fetch(`/api/runs/${props.runId}/evaluation`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ content: evalContent.value }),
        })
        const data = await resp.json()
        if (resp.ok) {
          evaluation.value = { content: evalContent.value, parsed_issues: data.parsed_issues }
          editingEval.value = false
          saveOk.value = true
          saveMsg.value = '保存成功'
        } else {
          saveOk.value = false
          saveMsg.value = data.error || '保存失败'
        }
      } catch (e) {
        saveOk.value = false
        saveMsg.value = '保存失败: ' + e.message
      } finally {
        savingEval.value = false
      }
    }

    function scrollTo(section) {
      activeSection.value = section
      const el = document.getElementById(`section-${section}`)
      if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }

    function onScroll() {
      const sections = ['overview', 'agent', 'rewards', 'events', 'commands', 'evaluation', 'raw']
      for (const s of sections) {
        const el = document.getElementById(`section-${s}`)
        if (el) {
          const rect = el.getBoundingClientRect()
          if (rect.top >= 0 && rect.top < 200) {
            activeSection.value = s
            break
          }
        }
      }
    }

    onMounted(async () => {
      try {
        const data = await api.getRun(props.runId)
        run.value = data.run
        agent.value = data.agent
        rewards.value = data.rewards || []
        events.value = data.events || []
        evaluation.value = data.evaluation

        // Fetch commands
        try {
          const cmdData = await api.getRun(props.runId) // reuse
          const cmdRes = await fetch(`/api/runs/${props.runId}/config/commands`)
          if (cmdRes.ok) {
            const c = await cmdRes.json()
            commands.value = c.commands || {}
          }
        } catch (e) { /* keep default */ }

        // Fetch all params via config endpoint
        try {
          const simRes = await fetch(`/api/runs/${props.runId}/config/sim`)
          if (simRes.ok) {
            const s = await simRes.json()
            if (s.sim_params) {
              allParams.value = Object.entries(s.sim_params).map(([k, v], i) => ({
                id: i, param_path: `sim.${k}`, value_text: v,
              }))
            }
          }
        } catch (e) { /* keep default */ }
      } catch (e) {
        console.error('Failed to load run detail:', e)
      } finally {
        loading.value = false
      }
    })

    return {
      loading, run, agent, rewards, events, commands, evaluation, allParams,
      activeSection, posRewards, negRewards, issues,
      editingEval, evalContent, savingEval, saveMsg, saveOk,
      startEditEval, cancelEditEval, saveEvaluation,
      modeEvents, modeBadgeClass, modeText,
      formatDate, formatArray, formatValue, scrollTo, onScroll,
    }
  },
}
</script>
