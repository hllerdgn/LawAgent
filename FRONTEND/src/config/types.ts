import type { HallmarkThemeId } from '../themes/types';

export interface ClientContactInfo {
  email: string;
  phone: string;
  address: string;
}

export interface ClientConfig {
  /** Uniq tenant/client ID (slug-style, e.g. "lawagent-demo", "yildiz-hukuk") */
  id: string;

  /** Firma / Büro Adı (e.g. "LawAgent AI", "Yıldız Hukuk Bürosu") */
  name: string;

  /** Atanmış Hallmark teması ID'si */
  themeId: HallmarkThemeId;

  /** Chatbot açılış/karşılama mesajı */
  welcomeMessage: string;

  /** İletişim bilgileri */
  contactInfo: ClientContactInfo;

  /** Özel logo URL'si (varsa) */
  logoUrl?: string;

  /** Slogan / açıklama */
  description?: string;

  /** Özellik bayrakları */
  features?: {
    allowPdfUpload?: boolean;
    showPracticeAreas?: boolean;
  };
}

export const DEFAULT_CLIENT_ID = 'lawagent-demo';
