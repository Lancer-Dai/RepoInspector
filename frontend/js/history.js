/**
 * 历史记录管理：
 * - 把成功分析过的仓库报告保存到 localStorage
 * - 上限 20 条（LRU：超出时移除最旧）
 * - 支持加载、删除、单条清除
 */

const STORAGE_KEY = 'repoinspector.history.v1';
const MAX_ENTRIES = 20;

/** @typedef {{key:string,url:string,full_name:string,avatar:string,analyzed_at:string,score:number|null,model:string|null,report:object,aiReview:object|null}} HistoryEntry */

/** 读取所有记录（按 analyzed_at 倒序）。 */
export function listHistory() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const arr = JSON.parse(raw);
    if (!Array.isArray(arr)) return [];
    return arr.slice(0, MAX_ENTRIES);
  } catch {
    return [];
  }
}

/** 写入并去重（同仓库替换旧记录；超出上限删除最旧）。 */
export function saveHistory(entry) {
  if (!entry || !entry.url || !entry.report) return;
  const list = listHistory();
  // 同 key 移除旧的
  const filtered = list.filter((e) => e.key !== entry.key);
  // 新条目置顶
  filtered.unshift(entry);
  // 截断到上限
  const trimmed = filtered.slice(0, MAX_ENTRIES);
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(trimmed));
  } catch (e) {
    // quota exceeded: 截断到一半再试
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(trimmed.slice(0, 10)));
    } catch {
      // ignore
    }
  }
  updateDot();
  window.dispatchEvent(new CustomEvent('history-changed'));
}

/** 根据 key 取出单条。 */
export function getHistory(key) {
  return listHistory().find((e) => e.key === key) || null;
}

/** 根据 url 算出规范 key（owner/repo 小写）。 */
export function keyOf(url) {
  try {
    const m = String(url).match(/github\.com\/([^/]+)\/([^/?#]+)/i);
    if (!m) return url.toLowerCase();
    return `${m[1].toLowerCase()}/${m[2].replace(/\.git$/i, '').toLowerCase()}`;
  } catch {
    return url.toLowerCase();
  }
}

/** 删除单条。 */
export function deleteHistory(key) {
  const list = listHistory();
  const next = list.filter((e) => e.key !== key);
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
  } catch {
    /* ignore */
  }
  updateDot();
  window.dispatchEvent(new CustomEvent('history-changed'));
}

/** 全部清空。 */
export function clearHistory() {
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch {
    /* ignore */
  }
  updateDot();
  window.dispatchEvent(new CustomEvent('history-changed'));
}

/** 更新顶部红点（仅在“是否有任何记录”时显示）。 */
function updateDot() {
  const dot = document.getElementById('history-dot');
  if (dot) dot.hidden = listHistory().length === 0;
}

/** 把相对时间格式化成简短中文（如 "5 分钟前"）。 */
function relTime(iso) {
  if (!iso) return '';
  try {
    const t = new Date(iso).getTime();
    const diff = Math.max(0, Date.now() - t);
    const m = Math.floor(diff / 60000);
    if (m < 1) return '刚刚';
    if (m < 60) return `${m} 分钟前`;
    const h = Math.floor(m / 60);
    if (h < 24) return `${h} 小时前`;
    const d = Math.floor(h / 24);
    if (d < 30) return `${d} 天前`;
    return new Date(iso).toLocaleDateString('zh-CN');
  } catch {
    return '';
  }
}

/** 评分区间映射（与 AI 卡片配色一致）。 */
function scoreClass(score) {
  if (score == null) return 'score-na';
  if (score >= 80) return 'score-high';
  if (score >= 60) return 'score-mid';
  return 'score-low';
}

/** 渲染历史列表。 */
function renderList() {
  const listEl = document.getElementById('history-list');
  const emptyEl = document.getElementById('history-empty');
  const hintEl = document.getElementById('history-hint');
  if (!listEl) return;

  const items = listHistory();
  listEl.innerHTML = '';
  if (items.length === 0) {
    if (emptyEl) emptyEl.hidden = false;
    listEl.hidden = true;
    if (hintEl) hintEl.hidden = true;
    return;
  }
  if (emptyEl) emptyEl.hidden = true;
  listEl.hidden = false;
  if (hintEl) hintEl.hidden = false;

  for (const e of items) {
    const li = document.createElement('li');
    li.className = 'history-item';
    li.dataset.key = e.key;
    li.innerHTML = `
      <img class="history-avatar" src="${escapeAttr(e.avatar || '')}" alt="" loading="lazy" onerror="this.style.visibility='hidden'"/>
      <div class="history-info">
        <p class="history-name">${escapeHtml(e.full_name || e.key)}</p>
        <div class="history-meta">
          <span>${escapeHtml(relTime(e.analyzed_at))}</span>
          <span class="dot">·</span>
          <span>${e.aiReview ? 'AI ' + escapeHtml(e.model || '') : '未评估'}</span>
        </div>
      </div>
      <span class="history-score ${scoreClass(e.score)}">${e.score != null ? e.score : '—'}</span>
      <div class="history-actions">
        <button type="button" class="btn-tertiary" data-act="delete" title="Delete">
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none" aria-hidden="true">
            <path d="M3 4h10M6 4V2.5h4V4M5 4l.5 9h5L11 4" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </button>
      </div>
    `;
    // 整体点击 → 加载报告
    li.addEventListener('click', (ev) => {
      const btn = ev.target.closest('[data-act]');
      if (btn) {
        if (btn.dataset.act === 'delete') {
          ev.stopPropagation();
          if (confirm(`从历史记录中删除「${e.full_name || e.key}」？`)) {
            deleteHistory(e.key);
            renderList();
          }
          return;
        }
      }
      closeHistory();
      window.dispatchEvent(new CustomEvent('history-load', { detail: e }));
    });
    listEl.appendChild(li);
  }
}

function escapeHtml(s) {
  return String(s ?? '').replace(/[&<>"']/g, (c) =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c])
  );
}
function escapeAttr(s) {
  return escapeHtml(s);
}

/** 打开模态框。 */
export function openHistory() {
  const m = document.getElementById('history-modal');
  if (!m) return;
  renderList();
  m.hidden = false;
}

/** 关闭模态框。 */
export function closeHistory() {
  const m = document.getElementById('history-modal');
  if (m) m.hidden = true;
}

/** 初始化。 */
export function initHistory() {
  document.getElementById('history-btn')?.addEventListener('click', openHistory);
  document.getElementById('history-close')?.addEventListener('click', closeHistory);
  document.getElementById('history-modal')?.addEventListener('click', (e) => {
    if (e.target.id === 'history-modal') closeHistory();
  });
  document.getElementById('history-clear-all')?.addEventListener('click', () => {
    if (listHistory().length === 0) return;
    if (!confirm('确定清空所有历史记录？此操作不可恢复。')) return;
    clearHistory();
    renderList();
  });

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      const m = document.getElementById('history-modal');
      if (m && !m.hidden) closeHistory();
    }
  });

  updateDot();
}
