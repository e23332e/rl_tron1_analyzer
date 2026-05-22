<template>
  <div class="modal-overlay" @click.self="$emit('close')">
    <div class="modal-content">
      <h3>导入配置文件</h3>
      <p style="font-size:0.85rem; color:var(--pico-muted-color);">
        上传 env.yaml 和 agent.yaml 进行分析
      </p>
      <form @submit.prevent="doImport">
        <label>
          Run Name (可选)
          <input v-model="runName" type="text" placeholder="留空自动从路径推断" />
        </label>
        <label>
          Experiment Name (可选)
          <input v-model="experimentName" type="text" placeholder="如: sf_tron_1a_flat" />
        </label>
        <label>
          env.yaml <span style="color:var(--danger-color)">*</span>
          <input type="file" accept=".yaml,.yml" @change="e => envFile = e.target.files[0]" required />
        </label>
        <label>
          agent.yaml <span style="color:var(--danger-color)">*</span>
          <input type="file" accept=".yaml,.yml" @change="e => agentFile = e.target.files[0]" required />
        </label>
        <label>
          评价.txt (可选)
          <input type="file" accept=".txt" @change="e => evalFile = e.target.files[0]" />
        </label>
        <div style="display:flex; gap:0.5rem; margin-top:1rem;">
          <button type="submit" :disabled="importing">
            {{ importing ? '导入中...' : '确认导入' }}
          </button>
          <button type="button" @click="$emit('close')" class="secondary">取消</button>
        </div>
      </form>
      <div v-if="error" style="margin-top:0.75rem; color:var(--danger-color);">{{ error }}</div>
    </div>
  </div>
</template>

<script>
import { ref } from 'vue'
import api from '../api.js'

export default {
  name: 'ImportDialog',
  emits: ['close', 'imported'],
  setup(props, { emit }) {
    const runName = ref('')
    const experimentName = ref('')
    const envFile = ref(null)
    const agentFile = ref(null)
    const evalFile = ref(null)
    const importing = ref(false)
    const error = ref('')

    async function doImport() {
      if (!envFile.value || !agentFile.value) {
        error.value = '请选择 env.yaml 和 agent.yaml 文件'
        return
      }
      importing.value = true
      error.value = ''
      try {
        const formData = new FormData()
        formData.append('env', envFile.value)
        formData.append('agent', agentFile.value)
        if (evalFile.value) formData.append('eval', evalFile.value)
        if (runName.value) formData.append('run_name', runName.value)
        if (experimentName.value) formData.append('experiment_name', experimentName.value)

        await api.importRun(formData)
        emit('imported')
      } catch (e) {
        error.value = '导入失败: ' + e.message
      } finally {
        importing.value = false
      }
    }

    return { runName, experimentName, envFile, agentFile, evalFile, importing, error, doImport }
  },
}
</script>
