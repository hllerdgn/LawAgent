import { useState, useEffect } from 'react';

/**
 * localStorage'dan site adını okur ve gerçek zamanlı güncellemeleri dinler.
 * Navbar ve Footer gibi birden fazla bileşende ortak kullanım için.
 */
export function useSiteName(): string {
  const [siteName, setSiteName] = useState<string>(() => {
    return localStorage.getItem('lawagent_site_name') || 'lawagent';
  });

  useEffect(() => {
    const handleUpdate = () => {
      const saved = localStorage.getItem('lawagent_site_name');
      if (saved) setSiteName(saved);
    };

    window.addEventListener('storage', handleUpdate);
    window.addEventListener('lawagent_settings_updated', handleUpdate);
    return () => {
      window.removeEventListener('storage', handleUpdate);
      window.removeEventListener('lawagent_settings_updated', handleUpdate);
    };
  }, []);

  return siteName;
}
