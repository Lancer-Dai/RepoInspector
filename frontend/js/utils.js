// 工具函数
/** 校验并规范化 GitHub 仓库 URL。返回 owner/repo 字符串，或抛错。 */
export function normalizeRepoUrl(url) {
  if (!url) throw new Error('请输入 GitHub 仓库 URL');
  const trimmed = String(url).trim();
  const m = trimmed.match(
    /^https?:\/\/github\.com\/([A-Za-z0-9][A-Za-z0-9._-]*)\/([A-Za-z0-9][A-Za-z0-9._-]*?)(?:\.git)?\/?$/
  );
  if (!m) throw new Error('URL 格式不正确，应为 https://github.com/owner/repo');
  return `${m[1]}/${m[2]}`;
}

/** 数字千分位格式化。 */
export function formatNumber(n) {
  if (n === null || n === undefined) return '--';
  if (Math.abs(n) >= 1000) return n.toLocaleString('en-US');
  return String(n);
}

/** 相对时间显示。 */
export function formatRelative(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  if (isNaN(d.getTime())) return iso;
  const diff = (Date.now() - d.getTime()) / 1000;
  if (diff < 60) return '刚刚';
  if (diff < 3600) return `${Math.floor(diff / 60)} 分钟前`;
  if (diff < 86400) return `${Math.floor(diff / 3600)} 小时前`;
  if (diff < 86400 * 30) return `${Math.floor(diff / 86400)} 天前`;
  if (diff < 86400 * 365) return `${Math.floor(diff / (86400 * 30))} 个月前`;
  return `${Math.floor(diff / (86400 * 365))} 年前`;
}

/** 标准日期显示。 */
export function formatDate(iso) {
  if (!iso) return '--';
  const d = new Date(iso);
  if (isNaN(d.getTime())) return iso;
  return d.toISOString().slice(0, 10);
}

/** HTML 转义。 */
export function escapeHtml(s) {
  return String(s ?? '').replace(/[&<>"']/g, (c) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  }[c]));
}
