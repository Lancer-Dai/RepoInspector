// 图表渲染：基于 Apache ECharts
// 入口 echarts 由 index.html 中的 CDN 脚本提供（全局变量）
/* global echarts */

/**
 * Vercel Design Tokens（与 style.css 保持同步）
 *  文字: ink #171717  body #4d4d4d  mute #888888
 *  线条: hairline #ebebeb  hairline-strong #a1a1a1
 *  背景: canvas #ffffff  canvas-soft #fafafa  canvas-soft-2 #f5f5f5
 *  强调: link #0070f3  cyan #50e3c2  pink #ff0080
 *        violet #7928ca  teal #00dfd8  amber #f9cb28  red #ff4d4d
 *  状态: success #0070f3  warning #f5a623  error #ee0000
 */

// Vercel 风格分类调色板（用于语言饼图等需要 8+ 区分色）
const LANG_COLORS = [
  '#10b981', // emerald  (替代 ink，更柔和的起始色)
  '#0070f3', // link
  '#50e3c2', // cyan
  '#ff0080', // pink
  '#7928ca', // violet
  '#f9cb28', // amber
  '#00dfd8', // teal
  '#ff4d4d', // red
];

// 通用文本样式（Vercel body 文字 + Geist/Inter 字体栈）
const TEXT_STYLE = {
  fontFamily: '"Geist", "Inter", system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif',
  fontSize: 12,
  color: '#4d4d4d', // body
  fontWeight: 400,
};
const AXIS_LINE = { lineStyle: { color: '#a1a1a1' } };           // hairline-strong
const SPLIT_LINE = { lineStyle: { color: '#ebebeb', type: 'dashed' } }; // hairline dashed
const TOOLTIP_STYLE = {
  backgroundColor: '#171717',
  borderColor: '#171717',
  textStyle: { color: '#ffffff', fontSize: 12, fontWeight: 400 },
  borderWidth: 0,
  borderRadius: 6,
  padding: [8, 12],
  extraCssText: 'box-shadow: 0 4px 12px rgba(0,0,0,0.15);',
};

/** 销毁该 dom 上已存在的实例（基于 echarts.getInstanceByDom）。 */
function disposeIfExists(dom) {
  const existing = echarts.getInstanceByDom(dom);
  if (existing) existing.dispose();
}

/** 空数据占位：直接在容器里渲染提示文字。 */
function drawEmpty(dom, text) {
  disposeIfExists(dom);
  dom.innerHTML = `
    <div style="
      display:flex;align-items:center;justify-content:center;
      width:100%;height:100%;
      color:#888888;font-size:13px;
      font-family:'Geist','Inter',system-ui,sans-serif;
    ">${text}</div>`;
}

/** 通用：创建图表并在下一帧 resize，确保填满父容器。 */
function makeChart(dom, option) {
  disposeIfExists(dom);
  const chart = echarts.init(dom);
  chart.setOption(option);
  // ECharts 初次 init 时容器可能尚未完成 layout，rAF 后再 resize 一次确保铺满
  requestAnimationFrame(() => {
    try { chart.resize(); } catch (_) { /* ignore */ }
  });
  return chart;
}

/* ===========================================================
 * 图表 1：编程语言分布（环形图，含右侧图例）
 * 配色：Vercel 分类调色板（ink/blue/cyan/pink/violet/amber/teal/red）
 * =========================================================== */
export function renderLanguagePie(dom, languages) {
  if (!languages || languages.length === 0) {
    drawEmpty(dom, '暂无语言数据');
    return null;
  }
  // 占比过小的合并到 "Other"
  const top = languages.slice(0, 8);
  const rest = languages.slice(8);
  const data = top.map((l, i) => ({
    name: l.name,
    value: l.percentage,
    itemStyle: {
      color: LANG_COLORS[i % LANG_COLORS.length],
      borderColor: '#ffffff',
      borderWidth: 2,
    },
  }));
  if (rest.length > 0) {
    const otherSum = +rest.reduce((s, l) => s + l.percentage, 0).toFixed(2);
    data.push({
      name: 'Other',
      value: otherSum,
      itemStyle: { color: '#a1a1a1', borderColor: '#ffffff', borderWidth: 2 },
    });
  }

  return makeChart(dom, {
    tooltip: {
      trigger: 'item',
      ...TOOLTIP_STYLE,
      formatter: (p) => `${p.name}: <b>${p.value}%</b>`,
    },
    legend: {
      type: 'scroll',
      orient: 'vertical',
      right: 10,
      top: 'middle',
      itemWidth: 10,
      itemHeight: 10,
      itemGap: 8,
      textStyle: TEXT_STYLE,
    },
    series: [{
      type: 'pie',
      radius: ['40%', '68%'],
      center: ['38%', '50%'],
      avoidLabelOverlap: true,
      itemStyle: { borderColor: '#fff', borderWidth: 2 },
      label: { show: false },
      labelLine: { show: false },
      data,
    }],
  });
}

/* ===========================================================
 * 图表 2：提交活跃度（折线 + 面积）
 * 配色：link blue 为主，cyan 渐变到透明
 * =========================================================== */
export function renderCommitLine(dom, monthly) {
  if (!monthly || monthly.length === 0) {
    drawEmpty(dom, '暂无提交数据');
    return null;
  }
  return makeChart(dom, {
    tooltip: {
      trigger: 'axis',
      ...TOOLTIP_STYLE,
      formatter: (params) => {
        const p = params[0];
        return `${p.axisValue}<br/>Commits: <b>${p.value}</b>`;
      },
    },
    grid: { left: 50, right: 20, top: 24, bottom: 36 },
    xAxis: {
      type: 'category',
      data: monthly.map((m) => m.month),
      axisLine: AXIS_LINE,
      axisTick: { show: false },
      axisLabel: { ...TEXT_STYLE, hideOverlap: true },
    },
    yAxis: {
      type: 'value',
      beginAtZero: true,
      axisLine: { show: false },
      axisTick: { show: false },
      splitLine: SPLIT_LINE,
      axisLabel: TEXT_STYLE,
    },
    series: [{
      name: 'Commits',
      type: 'line',
      data: monthly.map((m) => m.count),
      smooth: true,
      symbol: 'circle',
      symbolSize: 6,
      lineStyle: { color: '#0070f3', width: 2 },
      itemStyle: { color: '#0070f3', borderColor: '#ffffff', borderWidth: 2 },
      areaStyle: {
        // ink → transparent 渐变，保持 Vercel 极简
        color: {
          type: 'linear',
          x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: 'rgba(0, 112, 243, 0.18)' },
            { offset: 1, color: 'rgba(0, 112, 243, 0.00)' },
          ],
        },
      },
    }],
  });
}

/* ===========================================================
 * 图表 3：Top 10 贡献者（横向条形图）
 * 配色：ink（次级数据，使用中性主色）
 * =========================================================== */
export function renderContributorBar(dom, contributors) {
  if (!contributors || contributors.length === 0) {
    drawEmpty(dom, '暂无贡献者数据');
    return null;
  }
  // 翻转使第一名在最上
  const top = contributors.slice(0, 10).reverse();
  return makeChart(dom, {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      ...TOOLTIP_STYLE,
      formatter: (params) => {
        const p = params[0];
        return `${p.name}<br/>Commits: <b>${p.value}</b>`;
      },
    },
    grid: { left: 110, right: 30, top: 10, bottom: 28 },
    xAxis: {
      type: 'value',
      beginAtZero: true,
      axisLine: { show: false },
      axisTick: { show: false },
      splitLine: SPLIT_LINE,
      axisLabel: TEXT_STYLE,
    },
    yAxis: {
      type: 'category',
      data: top.map((c) => c.login),
      axisLine: AXIS_LINE,
      axisTick: { show: false },
      axisLabel: { ...TEXT_STYLE, fontSize: 12 },
    },
    series: [{
      type: 'bar',
      data: top.map((c) => c.contributions),
      itemStyle: {
        color: '#50e3c2',
        borderRadius: 4,
        borderColor: 'transparent',
        borderWidth: 0,
      },
      emphasis: { itemStyle: { color: '#0070f3' } },
      barWidth: 16,
    }],
  });
}

/* ===========================================================
 * 图表 4：健康度评分（雷达图，已不展示但保留以防回滚）
 * 配色：link blue
 * =========================================================== */
export function renderHealthRadar(dom, health) {
  if (!health) {
    drawEmpty(dom, '暂无健康度数据');
    return null;
  }
  return makeChart(dom, {
    tooltip: { ...TOOLTIP_STYLE },
    radar: {
      center: ['50%', '54%'],
      radius: '68%',
      splitNumber: 4,
      axisName: { color: '#171717', fontSize: 13 },
      splitLine: SPLIT_LINE,
      splitArea: { areaStyle: { color: ['#fafafa', '#ffffff'] } },
      axisLine: AXIS_LINE,
      indicator: [
        { name: '流行度', max: 100 },
        { name: '活跃度', max: 100 },
        { name: '社区',   max: 100 },
        { name: '维护性', max: 100 },
      ],
    },
    series: [{
      type: 'radar',
      symbol: 'circle',
      symbolSize: 6,
      lineStyle: { color: '#0070f3', width: 2 },
      itemStyle: { color: '#0070f3' },
      areaStyle: { color: 'rgba(0, 112, 243, 0.18)' },
      data: [{
        value: [
          health.popularity,
          health.activity,
          health.community,
          health.maintenance,
        ],
        name: '健康度',
      }],
    }],
  });
}

/* ===========================================================
 * 图表 5：Issue 健康度（环形图）
 * 配色：open = warning amber；closed = success/link blue
 * =========================================================== */
export function renderIssueDonut(dom, issues) {
  const open = issues?.open || 0;
  const closed = issues?.closed || 0;
  const total = open + closed;
  if (total === 0) {
    drawEmpty(dom, '暂无 Issue 数据');
    return null;
  }
  return makeChart(dom, {
    tooltip: {
      trigger: 'item',
      ...TOOLTIP_STYLE,
      formatter: (p) => `${p.name}: <b>${p.value}</b> (${p.percent}%)`,
    },
    legend: {
      bottom: 0,
      itemWidth: 10,
      itemHeight: 10,
      itemGap: 12,
      textStyle: TEXT_STYLE,
    },
    series: [{
      type: 'pie',
      radius: ['45%', '70%'],
      center: ['50%', '46%'],
      avoidLabelOverlap: true,
      itemStyle: { borderColor: '#fff', borderWidth: 2 },
      label: { show: false },
      labelLine: { show: false },
      data: [
        { name: 'Open',   value: open,   itemStyle: { color: '#f5a623', borderColor: '#ffffff', borderWidth: 2 } },
        { name: 'Closed', value: closed, itemStyle: { color: '#0070f3', borderColor: '#ffffff', borderWidth: 2 } },
      ],
    }],
  });
}
