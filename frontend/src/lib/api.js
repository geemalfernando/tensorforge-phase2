const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/+$/, "");

export function serviceUrl(path) {
  return `${API_BASE_URL}${path}`;
}

export async function api(path, body, method) {
  return request("/dashboard/api" + path, body, method);
}
export async function sessionRequest(path, body) {
  return request(path, body);
}
async function request(path, body, method) {
  const response = await fetch(serviceUrl(path), {
    method: method || (body ? "POST" : "GET"),
    credentials: API_BASE_URL ? "include" : "same-origin",
    headers: {
      "X-TensorForge-Dashboard": "1",
      ...(body ? { "Content-Type": "application/json" } : {}),
    },
    ...(body ? { body: JSON.stringify(body) } : {}),
  });
  const value = response.status === 204 ? null : await response.json();
  if (!response.ok)
    throw new Error(value?.error?.message || "Service request failed");
  return value;
}
export const label = (value) =>
  value
    ? value.replaceAll("_", " ").replace(/\b\w/g, (c) => c.toUpperCase())
    : "None";
export function download(value, name = "predictions.json") {
  const url = URL.createObjectURL(
    new Blob([JSON.stringify(value, null, 2)], { type: "application/json" }),
  );
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
