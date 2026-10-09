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

export async function serviceRequest(path) {
  const response = await fetch(serviceUrl(path));
  return readResponse(response);
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
  return readResponse(response);
}

async function readResponse(response) {
  if (response.status === 204) return null;

  const body = await response.text();
  let value;
  try {
    value = body ? JSON.parse(body) : null;
  } catch {
    throw new Error(
      response.status >= 500
        ? `Service unavailable (HTTP ${response.status}). Check the backend configuration and deployment logs.`
        : `Unexpected response from service (HTTP ${response.status}).`,
    );
  }

  if (!response.ok) {
    throw new Error(
      value?.error?.message || `Service request failed (HTTP ${response.status}).`,
    );
  }
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
