import * as echarts from 'echarts'

type TrendKey = 'weldVoltage' | 'arcVoltage' | 'wireSpeed'

const CHART_CONFIGS: Record<TrendKey, { name: string; color: string; unit: string }> = {
  weldVoltage: { name: '焊接电压', color: '#00e5ff', unit: 'V' },
  arcVoltage: { name: '电弧电压', color: '#00e5ff', unit: 'V' },
  wireSpeed: { name: '送丝速度', color: '#00e5ff', unit: 'm/min' },
}

function buildLabels(count: number): string[] {
  return Array.from({ length: count }, (_, i) => `${i + 1}`)
}

function buildChartOption(data: number[], cfg: typeof CHART_CONFIGS[TrendKey]): echarts.EChartsOption {
  const labels = buildLabels(data.length)
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
  const chartInstances = new Set<echarts.ECharts>()

  function initChart(el: HTMLElement, key: TrendKey): echarts.ECharts {
    const chart = echarts.init(el)
    const cfg = CHART_CONFIGS[key]
    chart.setOption(buildChartOption([], cfg))
    chartInstances.add(chart)
    return chart
  }

  function setSeriesData(chartMap: Record<TrendKey, echarts.ECharts | null>, dataMap: Record<TrendKey, number[]>) {
    for (const key of Object.keys(CHART_CONFIGS) as TrendKey[]) {
      const chart = chartMap[key]
      if (!chart) continue
      chart.setOption(buildChartOption(dataMap[key] || [], CHART_CONFIGS[key]))
    }
  }

  function resizeAll() {
    chartInstances.forEach((c) => c.resize())
  }

  function dispose() {
    chartInstances.forEach((c) => c.dispose())
    chartInstances.clear()
  }

  return { initChart, setSeriesData, resizeAll, dispose, CHART_CONFIGS }
}
