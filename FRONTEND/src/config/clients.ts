import type { ClientConfig } from './types';

export const DEFAULT_CLIENT: ClientConfig = {
  id: 'lawagent-demo',
  name: 'LawAgent AI',
  themeId: 'lumen',
  welcomeMessage: 'Merhaba! LawAgent AI hukuki asistanına hoş geldiniz. Size nasıl yardımcı olabilirim?',
  description: 'Türk Hukuku Yapay Zekâ Asistanı',
  contactInfo: {
    email: 'contact@lawagent.ai',
    phone: '+90 212 555 0100',
    address: 'İstanbul, Türkiye',
  },
  features: {
    allowPdfUpload: true,
    showPracticeAreas: true,
  },
};

export const PRESET_CLIENTS: Record<string, ClientConfig> = {
  'lawagent-demo': DEFAULT_CLIENT,
  'yildiz-hukuk': {
    id: 'yildiz-hukuk',
    name: 'Yıldız & Ortakları Hukuk Bürosu',
    themeId: 'cobalt',
    welcomeMessage: 'Merhaba! Yıldız Hukuk Bürosu yapay zekâ danışmanına hoş geldiniz.',
    description: 'Ticaret ve Borçlar Hukuku Uzmanlığı',
    contactInfo: {
      email: 'info@yildizhukuk.av.tr',
      phone: '+90 212 345 6789',
      address: 'Levent, İstanbul',
    },
    features: {
      allowPdfUpload: true,
      showPracticeAreas: true,
    },
  },
  'ozkan-avukatlik': {
    id: 'ozkan-avukatlik',
    name: 'Özkan Hukuk & Danışmanlık',
    themeId: 'grid',
    welcomeMessage: 'Merhaba, Özkan Hukuk Danışmanlık dijital asistanına hoş geldiniz.',
    description: 'İş ve Tüketici Hukuku Çözümleri',
    contactInfo: {
      email: 'iletisim@ozkan.av.tr',
      phone: '+90 312 987 6543',
      address: 'Çankaya, Ankara',
    },
    features: {
      allowPdfUpload: false,
      showPracticeAreas: true,
    },
  },
  'kocak-hukuk': {
    id: 'kocak-hukuk',
    name: 'Koçak Hukuk Bürosu',
    themeId: 'carnival',
    welcomeMessage: 'Merhaba! Koçak Hukuk dijital asistanı size nasıl yardımcı olabilir?',
    description: 'Editoryal Hukuki Danışmanlık',
    contactInfo: {
      email: 'danismanlik@kocakhukuk.com',
      phone: '+90 232 456 7890',
      address: 'Alsancak, İzmir',
    },
    features: {
      allowPdfUpload: true,
      showPracticeAreas: true,
    },
  },
};
