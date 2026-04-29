import { onUnmounted, ref, type Ref } from 'vue'
import * as echarts from 'echarts'

type TrendKey = 'weldVoltage' | 'arcVoltage' | 'wireSpeed' | 'gasFlow'

const CHART_CONFIGS: Record<TrendKey, { name: string; color: string; unit: string; base: number; jitter: number }> = {
  weldVoltage: { name: '焊接电压', color: '#00e5ff', unit: 'V', base: 24, jitter: 2 },
  arcVoltage: { name: '电弧电压', color: '#00e5ff', unit: 'V', base: 20, jitter: 1.5 },
  wireSpeed: { name: '送丝速度', color: '#00e5ff', unit: 'm/min', base: 8.2, jitter: 0.3 },
  gasFlow: { name: '气体流量', color: '#00e5ff', unit: 'L/min', base: 15, jitter: 1 },
}

function generateInitialData(base: number, jitter: number, count = 20): number[] {
  const arr: number[] = []
  for (let i = 0; i < count; i++) {
    arr.push(Number((base + (Math.random() - 0.5) * jitter * 2).toFixed(2)))
  }
  return arr
}

function buildChartOption(data: number[], cfg: typeof CHART_CONFIGS[TrendKey]): echarts.EChartsOption {
  const labels = data.map((_, i) => `${i}s`)
  return {
    grid: { top: 8, right: 10, bottom: 20, left: 36 },
    xAxis: {
      type: 'category',
      data: labels,
      axisLine: { lineStyle: { color: 'rgba(0,229,255,0.2)' } },
      axisLabel: { color: 'rgba(255,255,255,0.4)', fontSize: 9 },
      axisTick: { show: false },
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: 'rgba(0,229,255,0.15)', type: 'dashed' } },
      axisLine: { show: false },
      axisLabel: { color: 'rgba(255,255,255,0.5)', fontSize: 9 },
    },
    series: [{
      type: 'line',
      data,
      smooth: true,
      symbol: 'circle',
      symbolSize: 6,
      showSymbol: false,
      lineStyle: { 
        color: cfg.color, 
        width: 2,
        shadowColor: cfg.color,
        shadowBlur: 8,
        shadowOffsetY: 2
      },
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(0,229,255,0.35)' },
          { offset: 1, color: 'rgba(0,229,255,0.02)' },
        ]),
      },
    }],
    tooltip: { trigger: 'axis', backgroundColor: 'rgba(2,16,34,0.9)', borderColor: '#00e5ff', textStyle: { color: '#d7f6ff', fontSize: 12 } },
    animation: false,
  }
}

export function useCharts() {
  const trendData = ref<Record<TrendKey, number[]>>({
    weldVoltage: generateInitialData(24, 2),
    arcVoltage: generateInitialData(20, 1.5),
    wireSpeed: generateInitialData(8.2, 0.3),
    gasFlow: generateInitialData(15, 1),
  })

  const chartInstances: echarts.ECharts[] = []
  let trendTimer: number | null = null

  function initChart(el: HTMLElement, key: TrendKey): echarts.ECharts {
    const chart = echarts.init(el)
    const cfg = CHART_CONFIGS[key]
    chart.setOption(buildChartOption(trendData.value[key], cfg))
    chartInstances.push(chart)
    return chart
  }

  function updateCharts(chartMap: Record<TrendKey, echarts.ECharts | null>) {
    for (const key of Object.keys(CHART_CONFIGS) as TrendKey[]) {
      const cfg = CHART_CONFIGS[key]
      const arr = trendData.value[key]
      const last = arr[arr.length - 1]
      const next = Number((last + (Math.random() - 0.5) * cfg.jitter).toFixed(2))
      arr.push(next)
      if (arr.length > 20) arr.shift()
      const chart = chartMap[key]
      if (chart) chart.setOption(buildChartOption(arr, cfg))
    }
  }

  function startTrendTimer(chartMap: Record<TrendKey, echarts.ECharts | null>) {
    trendTimer = window.setInterval(() => updateCharts(chartMap), 2000)
  }

  function resizeAll() {
    chartInstances.forEach(c => c.resize())
  }

  function dispose() {
    if (trendTimer) window.clearInterval(trendTimer)
    chartInstances.forEach(c => c.dispose())
    chartInstances.length = 0
  }

  return { trendData, initChart, startTrendTimer, resizeAll, dispose, CHART_CONFIGS }
}
