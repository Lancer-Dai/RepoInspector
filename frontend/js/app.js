// 主流程：表单提交、错误处理、报告渲染
import { analyzeRepo, aiReviewRepo } from './api.js';
import {
  renderCommitLine,
  renderContributorBar,
  renderIssueDonut,
  renderLanguagePie,
} from './charts.js';
import { initSettings } from './settings.js';
import {
  getHistory,
  initHistory,
  keyOf,
  saveHistory,
} from './history.js';
import {
  escapeHtml,
  formatDate,
  formatNumber,
  formatRelative,
  normalizeRepoUrl,
} from './utils.js';

const $ = (id) => document.getElementById(id);

const els = {
  form: $('analyze-form'),
  input: $('repo-url'),
  submitBtn: $('submit-btn'),
  loading: $('loading'),
  report: $('report'),
  errorBox: $('error-box'),
  examples: document.querySelectorAll('.example-link'),
  // AI 评估相关
  aiLoading: $('ai-loading'),
  aiError: $('ai-error'),
  aiErrorMsg: $('ai-error-msg'),
  aiReviewResult: $('ai-review-result'),
  aiRetry: $('ai-retry'),
  aiScore: $('ai-score'),
  aiScoreCircle: $('ai-score-circle'),
  aiSummary: $('ai-summary'),
  aiStrengths: $('ai-strengths'),
  aiWeaknesses: $('ai-weaknesses'),
  aiSuggestions: $('ai-suggestions'),
  aiMeta: $('ai-meta'),
};

let charts = []; // 持有 Chart 实例，便于切换时销毁
let lastAnalyzedUrl = null; // 用于 AI 评估失败时重试
let aiInFlight = null; // 当前 AI 请求 Promise，避免重复触发

// ---- AI 评估：状态切换 ----
function setAIState(state) {
  els.aiLoading.hidden = state !== 'loading';
  els.aiError.hidden = state !== 'error';
  els.aiReviewResult.hidden = state !== 'result';
}

function setAIScoreColor(score) {
  // 移除旧 class，按区间设置（无渐变，纯色，匹配 Apple 风格）
  const el = els.aiScoreCircle;
  el.classList.remove('score-high', 'score-mid', 'score-low');
  if (score >= 80) el.classList.add('score-high');
  else if (score >= 60) el.classList.add('score-mid');
  else el.classList.add('score-low');
}

function renderAIList(ulEl, items) {
  ulEl.innerHTML = '';
  if (!items || items.length === 0) {
    const li = document.createElement('li');
    li.textContent = '—';
    li.style.color = '#94a3b8';
    ulEl.appendChild(li);
    return;
  }
  items.forEach((text) => {
    const li = document.createElement('li');
    li.textContent = text;
    ulEl.appendChild(li);
  });
}

function renderAIReview(data) {
  const score = Number(data.score) || 0;
  els.aiScore.textContent = score;
  setAIScoreColor(score);
  els.aiSummary.textContent = data.summary || '（AI 未给出总结）';
  renderAIList(els.aiStrengths, data.strengths);
  renderAIList(els.aiWeaknesses, data.weaknesses);
  renderAIList(els.aiSuggestions, data.suggestions);

  const ts = data.generated_at
    ? new Date(data.generated_at).toLocaleString('zh-CN')
    : new Date().toLocaleString('zh-CN');
  const model = data.model || 'AI';
  els.aiMeta.textContent = `由 ${model} 生成 · ${ts}`;
  setAIState('result');
}

function showAIError(msg) {
  els.aiErrorMsg.textContent = msg || 'AI 评估失败，请稍后重试';
  setAIState('error');
}

async function fetchAIReview(url) {
  // 同一 URL 的请求去重
  if (aiInFlight) return aiInFlight;
  setAIState('loading');
  const p = (async () => {
    try {
      const data = await aiReviewRepo(url);
      renderAIReview(data);
      // AI 评估成功后回填到历史记录
      const key = keyOf(url);
      const e = getHistory(key);
      if (e) {
        saveHistory({ ...e, score: data.score, model: data.model, aiReview: data });
      }
    } catch (err) {
      let msg = err.message || 'AI 评估失败';
      if (err.status === 429) {
        // err.code: 'rate_limited' = GitHub 限流，'llm_rate_limited' = 大模型限流
        if (err.code === 'llm_rate_limited') {
          msg = `大模型 API 限流：${err.retryAfter || 60} 秒后重试`;
        } else {
          msg = `GitHub API 限流：${err.retryAfter || 60} 秒后重试（未认证 60 次/小时）。可在后端 .env 配置 GITHUB_TOKEN 提升到 5000 次/小时。`;
        }
      } else if (err.status === 500 && err.code === 'llm_auth') msg = '后端未配置有效的 LLM API Key';
      else if (err.status === 502) msg = `AI 服务异常：${msg}`;
      showAIError(msg);
    } finally {
      aiInFlight = null;
    }
  })();
  aiInFlight = p;
  return p;
}

// ---- 错误展示 ----
function showError(msg) {
  els.errorBox.textContent = msg;
  els.errorBox.hidden = false;
}
function clearError() {
  els.errorBox.hidden = true;
  els.errorBox.textContent = '';
}

// ---- Loading 状态 ----
function setLoading(on) {
  els.loading.hidden = !on;
  els.submitBtn.disabled = on;
  els.submitBtn.querySelector('.btn-text').textContent = on ? 'Analyzing' : 'Analyze';
  els.submitBtn.querySelector('.btn-spinner').hidden = !on;
  if (on) {
    els.report.hidden = true;
    clearError();
  }
}

// ---- 销毁已有图表 ----
function destroyCharts() {
  charts.forEach((c) => c && c.dispose && c.dispose());
  charts = [];
}

// ---- 窗口 resize 时同步所有图表 ----
window.addEventListener('resize', () => {
  charts.forEach((c) => c && c.resize && c.resize());
});

// ---- 渲染报告 ----
function renderReport(data, url, opts = {}) {
  destroyCharts();
  document.getElementById('report').scrollIntoView({ behavior: 'smooth', block: 'start' });

  // 基础信息
  const b = data.basic;
  $('owner-avatar').src = b.owner_avatar;
  $('owner-avatar').alt = b.owner_login;
  const nameEl = $('repo-fullname');
  nameEl.textContent = b.full_name;
  nameEl.href = b.html_url;
  $('repo-description').textContent = b.description || '（无描述）';

  // 保存到历史（先存报告，AI 评估完成后再补全）。加载历史时不重复保存。
  if (!opts.skipSave) {
    const key = keyOf(url);
    const existing = getHistory(key) || {};
    saveHistory({
      key,
      url,
      full_name: b.full_name,
      avatar: b.owner_avatar,
      analyzed_at: data.generated_at || existing.analyzed_at || new Date().toISOString(),
      score: existing.score ?? null,
      model: existing.model ?? null,
      report: data,
      aiReview: existing.aiReview ?? null,
    });
  }

  lastAnalyzedUrl = url;
  // 默认触发 AI 评估；历史加载时可传 aiReview 直接展示或 null 表示无缓存
  if (opts.aiReview === undefined) {
    setAIState('loading');
    fetchAIReview(url);
  } else if (opts.aiReview) {
    renderAIReview(opts.aiReview);
  } else {
    // 无缓存的 AI 评估，显示重试引导
    showAIError('该历史记录未保存 AI 评估结果。点击下方按钮重新评估。');
  }

  // tags
  const tagsEl = $('repo-tags');
  tagsEl.innerHTML = '';
  (b.topics || []).slice(0, 8).forEach((t) => {
    const s = document.createElement('span');
    s.className = 'tag';
    s.textContent = t;
    tagsEl.appendChild(s);
  });

  // 额外信息
  $('repo-extra').innerHTML = [
    b.archived ? '<span style="color:#b91c1c">📦 Archived</span>' : '',
    b.license_name ? `<span>📄 ${escapeHtml(b.license_name)}</span>` : '',
    `<span>🌿 ${escapeHtml(b.default_branch)}</span>`,
    `<span>📅 创建于 ${formatDate(b.created_at)}</span>`,
    `<span>🔄 更新于 ${formatRelative(b.updated_at)}</span>`,
  ].join('');

  // 关键指标
  $('stat-stars').textContent = formatNumber(data.social.stars);
  $('stat-forks').textContent = formatNumber(data.social.forks);
  $('stat-watchers').textContent = formatNumber(data.social.watchers);
  $('stat-issues').textContent = formatNumber(data.social.open_issues);
  $('stat-releases').textContent = formatNumber((data.releases || []).length);
  $('stat-contribs').textContent = formatNumber((data.contributors || []).length);

  // Issue 数字
  $('issue-open').textContent = formatNumber(data.issues.open);
  $('issue-closed').textContent = formatNumber(data.issues.closed);
  $('issue-rate').textContent = `${(data.issues.close_rate * 100).toFixed(1)}%`;

  // Release 列表
  const rl = $('release-list');
  if (!data.releases || data.releases.length === 0) {
    rl.innerHTML = '<li><span class="tag-name">暂无 Release</span></li>';
  } else {
    rl.innerHTML = data.releases.map((r) => `
      <li>
        <a class="tag-name" href="${escapeHtml(r.html_url)}" target="_blank" rel="noopener">${escapeHtml(r.tag_name)}</a>
        <span class="date">${formatDate(r.published_at)}</span>
      </li>
    `).join('');
  }

  // 生成时间
  $('generated-at').textContent = `数据生成于 ${new Date(data.generated_at).toLocaleString('zh-CN')}`;

  // 图表
  charts.push(renderLanguagePie($('lang-chart'), data.languages));
  charts.push(renderCommitLine($('commit-chart'), data.commits_monthly));
  charts.push(renderContributorBar($('contrib-chart'), data.contributors));
  charts.push(renderIssueDonut($('issue-chart'), data.issues));

  els.report.hidden = false;
}

// ---- 提交处理 ----
async function onSubmit(e) {
  e.preventDefault();
  clearError();

  let url;
  try {
    url = normalizeRepoUrl(els.input.value);
  } catch (err) {
    showError(err.message);
    return;
  }

  setLoading(true);
  try {
    const data = await analyzeRepo(url);
    renderReport(data, url);
  } catch (err) {
    let msg = err.message || '分析失败';
    if (err.status === 404) msg = '仓库不存在或为私有仓库，请检查 URL';
    else if (err.status === 429) {
      msg = `GitHub API 限流：${err.retryAfter || 60} 秒后重试（未认证 60 次/小时）。在后端 .env 配置 GITHUB_TOKEN 可提升到 5000 次/小时。`;
    } else if (err.status === 403) msg = 'GitHub API 拒绝访问，可能是限流或 Token 无效。请稍后再试，或在后端 .env 配置 GITHUB_TOKEN';
    showError(msg);
  } finally {
    setLoading(false);
  }
}

// ---- 绑定事件 ----
els.form.addEventListener('submit', onSubmit);
els.examples.forEach((a) => {
  a.addEventListener('click', (e) => {
    e.preventDefault();
    els.input.value = a.dataset.url;
    els.form.requestSubmit();
  });
});
els.aiRetry.addEventListener('click', () => {
  if (lastAnalyzedUrl) fetchAIReview(lastAnalyzedUrl);
});

// 初始化设置（齿轮按钮 + 模态框 + localStorage 同步）
initSettings();
// 初始化历史（记录按钮 + 模态框 + localStorage）
initHistory();

// 配置变更时，如果当前有分析过的 URL，自动重跑 AI 评估以使用新配置
window.addEventListener('config-changed', () => {
  if (lastAnalyzedUrl) {
    setAIState('loading');
    fetchAIReview(lastAnalyzedUrl);
  }
});

// 加载历史记录（不重新请求后端，直接用缓存的 report 渲染）
window.addEventListener('history-load', (ev) => {
  const entry = ev.detail;
  if (!entry || !entry.report) return;
  // 同步 URL 框（方便再次分析时一眼看到）
  els.input.value = entry.url;
  // 直接渲染；若有缓存 AI 评估则直接显示（不再发起新请求），否则只标记 loading 让用户手动重试
  renderReport(entry.report, entry.url, {
    skipSave: true, // 已是历史记录，renderReport 不必再保存
    aiReview: entry.aiReview || null, // null = 不重跑
  });
});

// 暴露给控制台调试
window.__ri__ = { renderReport, fetchAIReview };
