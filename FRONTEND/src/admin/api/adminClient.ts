// src/admin/api/adminClient.ts
// Tüm admin API isteklerinin tek çıkış noktası.
// sessionStorage'dan 'adminKey' okuyup X-Admin-Key header'ına ekler.
// 401 gelirse login sayfasına yönlendirir.

const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:7860';
const SESSION_KEY = 'adminKey'; // AdminLogin.tsx ile birebir aynı key adı

function getKey(): string {
  return sessionStorage.getItem(SESSION_KEY) ?? '';
}

function redirectToLogin() {
  sessionStorage.removeItem(SESSION_KEY);
  window.location.href = '/admin';
}

interface RequestOptions extends Omit<RequestInit, 'headers'> {
  headers?: Record<string, string>;
}

export async function adminFetch<T>(
  path: string,
  options: RequestOptions = {}
): Promise<T> {
  const key = getKey();
  const isFormData = typeof FormData !== 'undefined' && options.body instanceof FormData;

  const headers: Record<string, string> = {
    'X-Admin-Key': key,
    ...(options.headers ?? {}),
  };

  if (!isFormData && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json';
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  if (res.status === 401) {
    redirectToLogin();
    throw new Error('Yetkisiz erişim — giriş sayfasına yönlendiriliyor.');
  }

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    const message =
      typeof body.detail === 'string'
        ? body.detail
        : JSON.stringify(body.detail ?? body);
    throw new Error(message);
  }

  return res.json() as Promise<T>;
}

// ── Auth yardımcıları ─────────────────────────────────────────────────────────

export function saveAdminKey(key: string): void {
  sessionStorage.setItem(SESSION_KEY, key);
}

export function clearAdminKey(): void {
  sessionStorage.removeItem(SESSION_KEY);
}

export function hasAdminKey(): boolean {
  return !!sessionStorage.getItem(SESSION_KEY);
}
