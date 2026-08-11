import type { ClientConfig } from './types';
import { DEFAULT_CLIENT_ID } from './types';
import { PRESET_CLIENTS, DEFAULT_CLIENT } from './clients';

/**
 * Aktif Client ID'sini ortamdan / URL'den / script etiketinden tespit eder.
 */
export function resolveClientId(): string {
  if (typeof window === 'undefined') return DEFAULT_CLIENT_ID;

  // 1. URL Query Parameter (örn: ?client=yildiz-hukuk)
  const params = new URLSearchParams(window.location.search);
  const queryClient = params.get('client');
  if (queryClient) return queryClient;

  // 2. Widget Embed script tag: <script data-client="xyz">
  const scriptTag = document.querySelector('script[data-client]');
  if (scriptTag) {
    const dataClient = scriptTag.getAttribute('data-client');
    if (dataClient) return dataClient;
  }

  // 3. LocalStorage override (Admin ayarlarından seçilmişse)
  const savedClient = localStorage.getItem('lawagent_client_id');
  if (savedClient) return savedClient;

  // 4. Fallback default
  return DEFAULT_CLIENT_ID;
}

/**
 * Backend API veya preset listesinden ClientConfig yükler.
 */
export async function fetchClientConfig(clientId?: string): Promise<ClientConfig> {
  const targetId = clientId || resolveClientId();

  try {
    const baseUrl = import.meta.env.VITE_API_URL || 'https://hllerdgn-lawagent-backend.hf.space';
    const res = await fetch(`${baseUrl}/clients/${targetId}`, {
      headers: { Accept: 'application/json' },
    });
    if (res.ok) {
      const data = await res.json();
      return data as ClientConfig;
    }
  } catch (err) {
    console.warn(`[ClientResolver] Backend /clients/${targetId} erişilemedi, preset fallback kullanılıyor.`, err);
  }

  // Fallback preset
  return PRESET_CLIENTS[targetId] || DEFAULT_CLIENT;
}
