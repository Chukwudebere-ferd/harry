const API_BASE =
  localStorage.getItem("harry_api_base") || "http://localhost:8000";
export function getApiKey() {
  return localStorage.getItem("harry_api_key") || "";
}
export function setApiKey(v) {
  localStorage.setItem("harry_api_key", v);
}
export async function api(path, opts = {}) {
  const headers = opts.headers || {};
  const key = getApiKey();
  if (key) headers["Authorization"] = `Bearer ${key}`;
  headers["Content-Type"] = "application/json";
  const res = await fetch(`${API_BASE}${path}`, { ...opts, headers });
  const text = await res.text();
  let data;
  try {
    data = JSON.parse(text);
  } catch {
    data = { raw: text };
  }
  if (!res.ok)
    throw Object.assign(new Error(data?.error?.message || res.statusText), {
      status: res.status,
      data,
    });
  return data;
}
