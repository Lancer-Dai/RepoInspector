// 后端 API 调用封装
import { buildOverridesHeaders } from './settings.js';

const API_BASE = ''; // 同源；如分离部署改为 'http://localhost:8000'

/** 构造带用户配置 override 的 headers。 */
function authedHeaders() {
  return { 'Content-Type': 'application/json', ...buildOverridesHeaders() };
}

export async function analyzeRepo(url) {
  const res = await fetch(`${API_BASE}/api/analyze`, {
    method: 'POST',
    headers: authedHeaders(),
    body: JSON.stringify({ url }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = data.detail || data;
    const err = new Error(detail.message || `请求失败 (${res.status})`);
    err.code = detail.error || 'unknown';
    err.status = res.status;
    err.retryAfter = detail.retry_after;
    throw err;
  }
  return data;
}

export async function aiReviewRepo(url) {
  const res = await fetch(`${API_BASE}/api/ai-review`, {
    method: 'POST',
    headers: authedHeaders(),
    body: JSON.stringify({ url }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = data.detail || data;
    const err = new Error(detail.message || `请求失败 (${res.status})`);
    err.code = detail.error || 'unknown';
    err.status = res.status;
    err.retryAfter = detail.retry_after;
    throw err;
  }
  return data;
}

export async function healthCheck() {
  try {
    const res = await fetch(`${API_BASE}/api/health`);
    return res.ok;
  } catch {
    return false;
  }
}
