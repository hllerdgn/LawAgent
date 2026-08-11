import React, { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { ChatbotWidget } from './app/components/ChatbotWidget';
import { fetchClientConfig, resolveClientId } from './config/clientResolver';
import { applyThemeToElement } from './themes/ThemeProvider';
import { resolveTheme } from './themes/registry';
import type { ClientConfig } from './config/types';
import './styles/index.css';

/**
 * LawAgent White-Label Standalone Widget Entry Point
 * 
 * Embed Kullanımı:
 * <script src="https://lawagent.ai/widget.js" data-client="yildiz-hukuk"></script>
 */

function StandaloneWidgetApp() {
  const [clientConfig, setClientConfig] = useState<ClientConfig | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function initWidget() {
      const clientId = resolveClientId();
      const config = await fetchClientConfig(clientId);
      setClientConfig(config);

      // Tema uygula
      const theme = resolveTheme(config.themeId);
      const container = document.getElementById('lawagent-widget-root') || document.documentElement;
      applyThemeToElement(theme, container);
      setLoading(false);
    }

    initWidget();
  }, []);

  if (loading) return null;

  return (
    <div id="lawagent-widget-container" className="lawagent-widget-wrapper font-sans">
      <ChatbotWidget />
    </div>
  );
}

// Target container element oluştur veya bul
function mountWidget() {
  let target = document.getElementById('lawagent-widget-root');
  if (!target) {
    target = document.createElement('div');
    target.id = 'lawagent-widget-root';
    document.body.appendChild(target);
  }

  const root = createRoot(target);
  root.render(
    <React.StrictMode>
      <StandaloneWidgetApp />
    </React.StrictMode>
  );
}

// Otomatik mount
if (document.readyState === 'complete' || document.readyState === 'interactive') {
  mountWidget();
} else {
  window.addEventListener('DOMContentLoaded', mountWidget);
}
