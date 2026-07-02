<script setup lang="ts">
// 参数网格寻优主页面：左配置（选标的 + 策略 + 寻优参数）/ 右报告（排名表 + 热力图）。

import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import OptimizeHeatmap from '../components/OptimizeHeatmap.vue'
import OptimizeResultTable from '../components/OptimizeResultTable.vue'
import ParamGridPicker from '../components/ParamGridPicker.vue'
import SymbolPicker from '../components/SymbolPicker.vue'
import type { ExecutionMode } from '../types'
import { useBacktestStore } from '../stores/backtest'

const store = useBacktestStore()
const router = useRouter()

const strategy = ref('ma_cross')
const paramGrid = ref<Record<string, Array<number | string>>>({})
const cash = ref(100000)
const execution = ref<ExecutionMode>('next_open')
const EXECUTIONS: ExecutionMode[] = ['next_open', 'next_close', 'this_close', 'worst', 'best']

const selectedStrategy = computed(
  () => store.strategies.find((s) => s.name === strategy.value) ?? null,
)

onMounted(() => {
  store.loadStrategies().catch((e) => {
    store.error = `加载策略列表失败：${e instanceof Error ? e.message : e}`
  })
})

// 网格点数（前端预校验，提示用户）
const gridPoints = computed(() => {
  const sizes = Object.values(paramGrid.value).map((v) => v.length)
  return sizes.reduce((a, b) => a * b, 1)
})

async function onRun() {
  if (!store.hasBars) {
    store.error = '请先取行情数据'
    return
  }
  if (Object.keys(paramGrid.value).length === 0) {
    store.error = '请勾选至少 1 个参数并填入取值'
    return
  }
  if (gridPoints.value > 200) {
    store.error = `网格点数 ${gridPoints.value} 超过上限 200`
    return
  }
  await store.runOptimize({
    strategy: strategy.value,
    param_grid: paramGrid.value,
    cash: cash.value,
    execution: execution.value,
    ohlcv: store.ohlcv,
  })
}

// 点击排名表「查看」→ 跳转单标的页用该参数回测
function onViewParams(params: Record<string, number | string>) {
  // 通过 query 传递参数，单标的页接收后自动填充
  router.push({
    path: '/',
    query: { strategy: strategy.value, params: JSON.stringify(params) },
  })
}
</script>

<template>
  <div class="optimize-view">
    <aside class="config-panel">
      <section class="panel-section">
        <h3>行情数据</h3>
        <SymbolPicker />
      </section>

      <section class="panel-section">
        <h3>策略</h3>
        <div class="field">
          <select v-model="strategy">
            <option v-for="s in store.strategies" :key="s.name" :value="s.name">
              {{ s.label }}（{{ s.name }}）
            </option>
          </select>
        </div>
      </section>

      <section class="panel-section">
        <h3>寻优参数</h3>
        <ParamGridPicker v-model="paramGrid" :strategy="selectedStrategy" />
      </section>

      <section class="panel-section">
        <h3>资金</h3>
        <div class="field">
          <label>初始资金</label>
          <input v-model.number="cash" type="number" min="1000" step="10000" />
        </div>
        <div class="field">
          <label>成交模式</label>
          <select v-model="execution">
            <option v-for="e in EXECUTIONS" :key="e" :value="e">{{ e }}</option>
          </select>
        </div>
      </section>

      <button
        class="primary run-btn"
        :disabled="store.optimizeRunning || !store.hasBars"
        @click="onRun"
      >
        {{ store.optimizeRunning ? '寻优中…' : '开始寻优' }}
      </button>
    </aside>

    <main class="report-panel">
      <div v-if="store.error" class="error-banner">⚠ {{ store.error }}</div>

      <div
        v-if="!store.optimizeResult && !store.optimizeRunning && !store.error"
        class="placeholder"
      >
        <p>选标的 → 取行情 → 选策略 → 勾选寻优参数 → 开始寻优</p>
      </div>

      <div v-if="store.optimizeResult" class="report-content">
        <section class="report-section">
          <h3>最优结果</h3>
          <div v-if="store.optimizeResult.best" class="best-summary">
            <span class="best-params">{{ JSON.stringify(store.optimizeResult.best.params) }}</span>
            <span class="best-return pos">
              {{ (store.optimizeResult.best.total_return! * 100).toFixed(2) }}%
            </span>
            <span class="best-meta">
              夏普 {{ store.optimizeResult.best.sharpe?.toFixed(2) }} · 回撤
              {{ (store.optimizeResult.best.max_drawdown! * 100).toFixed(2) }}%
            </span>
          </div>
        </section>

        <section v-if="store.optimizeResult.heatmap" class="report-section">
          <h3>参数热力图（{{ store.optimizeResult.heatmap.x_name }} × {{ store.optimizeResult.heatmap.y_name }}）</h3>
          <OptimizeHeatmap :heatmap="store.optimizeResult.heatmap" />
        </section>

        <section class="report-section">
          <h3>网格点排名（{{ store.optimizeResult.results.length }} 个）</h3>
          <OptimizeResultTable
            :results="store.optimizeResult.results"
            :best-index="0"
            @select="onViewParams"
          />
        </section>
      </div>
    </main>
  </div>
</template>

<style scoped>
.optimize-view {
  display: flex;
  height: 100%;
}
.config-panel {
  width: 320px;
  flex-shrink: 0;
  background: var(--bg-panel);
  border-right: 1px solid var(--border);
  padding: 16px;
  overflow-y: auto;
}
.panel-section {
  margin-bottom: 20px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--border);
}
.panel-section:last-of-type {
  border-bottom: none;
}
.panel-section h3 {
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 12px;
}
.run-btn {
  width: 100%;
  padding: 10px;
  font-size: 14px;
}
.report-panel {
  flex: 1;
  overflow-y: auto;
  padding: 16px 20px;
}
.placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--text-dim);
}
.error-banner {
  background: rgba(239, 65, 70, 0.12);
  border: 1px solid var(--up);
  color: var(--up);
  padding: 10px 14px;
  border-radius: var(--radius);
  margin-bottom: 16px;
  font-size: 13px;
}
.report-section {
  background: var(--bg-panel);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 14px 16px;
  margin-bottom: 16px;
}
.report-section h3 {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-muted);
  margin-bottom: 12px;
}
.best-summary {
  display: flex;
  align-items: baseline;
  gap: 16px;
}
.best-params {
  font-family: var(--font-mono);
  font-size: 14px;
  color: var(--accent);
}
.best-return {
  font-size: 22px;
  font-weight: 700;
  font-family: var(--font-mono);
}
.best-meta {
  color: var(--text-dim);
  font-size: 12px;
}
.pos {
  color: var(--up);
}
</style>
