/**
 * 用户配置管理：
 * - localStorage 存储 4 个值（github_token / llm_api_key / llm_base_url / llm_model）
 * - 留空代表使用后端 .env 默认值
 * - 通过 buildOverridesHeaders() 生成 X-* 头
 */

const STORAGE_KEY = 'repoinspector.config';

const FIELDS = {
  github_token: '',
  llm_api_key: '',
  llm_base_url: '',
  llm_model: '',
};

let defaults = { ...FIELDS };

/** 从 localStorage 读出当前用户覆盖值（无值时返回空对象）。 */
export function loadOverrides() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return {};
    const data = JSON.parse(raw);
    const out = {};
    for (const k of Object.keys(FIELDS)) {
      if (typeof data[k] === 'string' && data[k].trim()) {
        out[k] = data[k].trim();
      }
    }
    return out;
  } catch {
    return {};
  }
}

/** 写入 localStorage。 */
function saveOverrides(values) {
  const data = {};
  for (const k of Object.keys(FIELDS)) {
    const v = (values[k] ?? '').trim();
    if (v) data[k] = v;
  }
  localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
}

/** 清除 localStorage 中的覆盖值。 */
function clearOverrides() {
  localStorage.removeItem(STORAGE_KEY);
}

/** 根据当前 overrides 生成 fetch headers 增量。 */
export function buildOverridesHeaders() {
  const o = loadOverrides();
  const h = {};
  if (o.github_token) h['X-Github-Token'] = o.github_token;
  if (o.llm_api_key) h['X-LLM-Api-Key'] = o.llm_api_key;
  if (o.llm_base_url) h['X-LLM-Base-Url'] = o.llm_base_url;
  if (o.llm_model) h['X-LLM-Model'] = o.llm_model;
  return h;
}

/** 是否有任何用户自定义覆盖值。 */
export function hasOverrides() {
  return Object.keys(loadOverrides()).length > 0;
}

/** 更新齿轮按钮上的小红点。 */
function updateDot() {
  const dot = document.getElementById('settings-dot');
  if (dot) dot.hidden = !hasOverrides();
}

/** 从后端拉取默认值（用于初始化表单）。 */
export async function fetchDefaults() {
  try {
    const resp = await fetch('/api/config');
    if (!resp.ok) return { ...FIELDS };
    const data = await resp.json();
    return {
      github_token: data.github_token || '',
      llm_api_key: data.llm_api_key || '',
      llm_base_url: data.llm_base_url || '',
      llm_model: data.llm_model || '',
    };
  } catch {
    return { ...FIELDS };
  }
}

/** 打开模态框。 */
export async function openSettings() {
  const modal = document.getElementById('settings-modal');
  if (!modal) return;

  // 拉取后端默认 + 合并用户覆盖（覆盖优先）
  defaults = await fetchDefaults();
  const overrides = loadOverrides();
  const values = { ...defaults, ...overrides };

  const fields = {
    'cfg-github-token': 'github_token',
    'cfg-llm-api-key': 'llm_api_key',
    'cfg-llm-base-url': 'llm_base_url',
    'cfg-llm-model': 'llm_model',
  };
  for (const [elId, key] of Object.entries(fields)) {
    const el = document.getElementById(elId);
    if (el) el.value = values[key] || '';
  }

  modal.hidden = false;
  // 焦点放到第一个输入
  setTimeout(() => document.getElementById('cfg-github-token')?.focus(), 50);
}

/** 关闭模态框。 */
export function closeSettings() {
  const modal = document.getElementById('settings-modal');
  if (modal) modal.hidden = true;
}

/** 读取当前表单值。 */
function readFormValues() {
  return {
    github_token: document.getElementById('cfg-github-token')?.value || '',
    llm_api_key: document.getElementById('cfg-llm-api-key')?.value || '',
    llm_base_url: document.getElementById('cfg-llm-base-url')?.value || '',
    llm_model: document.getElementById('cfg-llm-model')?.value || '',
  };
}

/** 提交：保存 + 关闭。 */
function onSubmit(e) {
  e.preventDefault();
  const values = readFormValues();
  // 与默认完全相同则清除（不污染 localStorage）
  const isDefault = Object.keys(FIELDS).every(
    (k) => (values[k] || '') === (defaults[k] || '')
  );
  if (isDefault) {
    clearOverrides();
  } else {
    saveOverrides(values);
  }
  updateDot();
  closeSettings();
  // 触发自定义事件，通知其它模块（app.js）刷新状态
  window.dispatchEvent(new CustomEvent('config-changed'));
}

/** Reset 按钮：清空所有用户覆盖，等价于使用后端默认。 */
function onReset() {
  clearOverrides();
  const map = {
    'cfg-github-token': 'github_token',
    'cfg-llm-api-key': 'llm_api_key',
    'cfg-llm-base-url': 'llm_base_url',
    'cfg-llm-model': 'llm_model',
  };
  for (const [elId, key] of Object.entries(map)) {
    const el = document.getElementById(elId);
    if (el) el.value = defaults[key] || '';
  }
  updateDot();
  window.dispatchEvent(new CustomEvent('config-changed'));
}

/** 初始化：绑定事件 + 更新 dot。 */
export function initSettings() {
  document.getElementById('settings-btn')?.addEventListener('click', openSettings);
  document.getElementById('settings-close')?.addEventListener('click', closeSettings);
  document.getElementById('settings-cancel')?.addEventListener('click', closeSettings);
  document.getElementById('settings-reset')?.addEventListener('click', onReset);
  document.getElementById('settings-form')?.addEventListener('submit', onSubmit);

  // 点击背景关闭
  document.getElementById('settings-modal')?.addEventListener('click', (e) => {
    if (e.target.id === 'settings-modal') closeSettings();
  });

  // ESC 关闭
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      const m = document.getElementById('settings-modal');
      if (m && !m.hidden) closeSettings();
    }
  });

  updateDot();
}
