const API_BASE_URL = "http://localhost:8000";

export class ApiError extends Error {
  constructor(message, options = {}) {
    super(message);
    this.name = "ApiError";
    this.status = options.status ?? null;
    this.data = options.data ?? null;
    this.url = options.url ?? null;
  }
}

async function request(path, options = {}) {
  const url = `${API_BASE_URL}${path}`;
  const response = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers ?? {}),
    },
    ...options,
  });

  const contentType = response.headers.get("content-type") ?? "";
  let payload = null;

  if (contentType.includes("application/json")) {
    payload = await response.json();
  } else {
    const text = await response.text();
    payload = text ? { message: text } : null;
  }

  if (!response.ok) {
    const message =
      payload?.message ||
      payload?.detail ||
      `Request failed with status ${response.status}`;
    throw new ApiError(message, {
      status: response.status,
      data: payload,
      url,
    });
  }

  return payload;
}

export function health() {
  return request("/health");
}

export function mastPing() {
  return request("/api/mast/ping");
}

export function searchObservations(target, radiusArcsec) {
  const params = new URLSearchParams();
  params.set("target", target);
  if (radiusArcsec !== undefined && radiusArcsec !== null && radiusArcsec !== "") {
    params.set("radiusArcsec", String(radiusArcsec));
  }
  return request(`/api/search?${params.toString()}`);
}

export function listProducts(obsid) {
  return request(`/api/obs/${encodeURIComponent(obsid)}/products`);
}

export function downloadProduct(product_id) {
  return request("/api/products/download", {
    method: "POST",
    body: JSON.stringify({ product_id }),
  });
}

export function fetchSpectrum(product_id) {
  const params = new URLSearchParams({ product_id });
  return request(`/api/products/spectrum?${params.toString()}`);
}

export const api = {
  health,
  mastPing,
  searchObservations,
  listProducts,
  downloadProduct,
  fetchSpectrum,
};

