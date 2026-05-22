const BASE = '/api'

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(text || `HTTP ${res.status}`)
  }
  return res.json()
}

export default {
  // Runs
  getRuns(params = {}) {
    const qs = new URLSearchParams(params).toString()
    return request(`/runs${qs ? '?' + qs : ''}`)
  },
  getRun(id) { return request(`/runs/${id}`) },
  deleteRun(id) { return request(`/runs/${id}`, { method: 'DELETE' }) },
  updateRun(id, data) {
    return request(`/runs/${id}`, { method: 'PUT', body: JSON.stringify(data) })
  },
  importRun(formData) {
    return fetch(`${BASE}/runs/import`, { method: 'POST', body: formData }).then(r => {
      if (!r.ok) return r.text().then(t => Promise.reject(new Error(t)))
      return r.json()
    })
  },
  importDirectory(directory) {
    return request('/runs/import-directory', {
      method: 'POST',
      body: JSON.stringify({ directory }),
    })
  },

  // Compare
  compareRewards(ids) {
    return request(`/compare/rewards?ids=${ids.join(',')}`)
  },
  compareEvents(ids) {
    return request(`/compare/events?ids=${ids.join(',')}`)
  },
  compareAgent(ids) {
    return request(`/compare/agent?ids=${ids.join(',')}`)
  },
  compareDelta(a, b) {
    return request(`/compare/delta/${a}/${b}`)
  },

  // Search
  search(query) {
    return request(`/search?q=${encodeURIComponent(query)}`)
  },
  searchEval(query) {
    return request(`/search/eval?q=${encodeURIComponent(query)}`)
  },

  // Stats
  getOverview() { return request('/stats/overview') },
  getRewardDistribution() { return request('/stats/reward-distribution') },
}
