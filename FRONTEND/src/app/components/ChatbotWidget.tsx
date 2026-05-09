import React, { useState, useEffect, useRef, useCallback } from "react";
import {
  X,
  Send,
  Loader2,
  Scale,
  Info,
  Maximize2,
  Minimize2,
  StopCircle,
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

// ---------- UTILS ----------
const cn = (...classes: (string | boolean | undefined)[]) =>
  classes.filter(Boolean).join(" ");

// Intent detection (meta vs legal)
function detectIntent(query: string): "meta" | "legal" | "chitchat" {
  const lower = query.toLowerCase();
  if (
    lower.includes("ne sorabilirim") ||
    lower.includes("nasıl kullan") ||
    lower.includes("hangi sorular") ||
    lower.includes("örnek soru") ||
    lower.includes("yardım edebilir") ||
    lower.includes("yapabilirsin") ||
    lower.includes("yetkilerin") ||
    lower.includes("capabilities") ||
    (lower.includes("soru") && lower.includes("sorabilirim"))
  ) {
    return "meta";
  }
  if (lower.match(/^(merhaba|selam|hey|hi|hello|naber|iyi misin)/)) {
    return "chitchat";
  }
  return "legal";
}

// Meta sorular için zengin cevap (örnek sorular + action chiplear)
function getMetaResponse(): {
  content: string;
  actions: string[];
} {
  return {
    content: `Size şu konularda yardımcı olabilirim:

• Kira sözleşmesi feshi  
• Borçlu temerrüdü  
• Tüketici hakları (iade, cayma hakkı)  
• Şirketler hukuku (TTK)  

İsterseniz aşağıdaki örnek sorulardan birini seçebilirsiniz:

`,
    actions: [
      "Kira sözleşmesi nasıl feshedilir?",
      "İnternetten alınan ürün iade edilir mi?",
      "Temerrüt faizi nasıl hesaplanır?",
      "Limited şirket kurmak için gerekenler?",
    ],
  };
}

// Chitchat için basit cevap
function getChitchatResponse(): {
  content: string;
  actions: string[];
} {
  return {
    content: `Merhaba! Ben LawAgent AI, hukuki konularda size yardımcı olmak için buradayım. Size kira hukuku, borçlar hukuku, tüketici hakları ve şirketler hukuku gibi konularda destek sağlayabilirim.

Nasıl yardımcı olabilirim?`,
    actions: [
      "Kira sözleşmesi örneği",
      "Tüketici hakları nelerdir?",
      "Borç temerrüdü nedir?",
    ],
  };
}

// Legal linkleri zenginleştir (inline kaynak için)
function enrichLegalLinks(text: string): string {
  return text
    .replace(
      /\bTBK\s*m\.?\s*(\d+)\b/gi,
      "[TBK m.$1](https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=6098&Klm=$1)",
    )
    .replace(
      /\bTTK\s*m\.?\s*(\d+)\b/gi,
      "[TTK m.$1](https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=6102&Klm=$1)",
    )
    .replace(
      /\bBK\s*m\.?\s*(\d+)\b/gi,
      "[BK m.$1](https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=6098&Klm=$1)",
    )
    .replace(
      /\bTBK\b/g,
      "[TBK](https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=6098)",
    )
    .replace(
      /\bTTK\b/g,
      "[TTK](https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=6102)",
    );
}

// Cevap içindeki gereksiz kalın başlıkları yumuşat
function softenMarkdownHeadings(content: string): string {
  return content
    .replace(/###\s*Hukuki\s*Değerlendirme/gi, "### Kısa Hukuki Bilgi")
    .replace(/###\s*Durum/gi, "### Özet")
    .replace(/###\s*Öneri/gi, "### Size Önerimiz")
    .replace(/\*\*Hukuki Değerlendirme\*\*/gi, "**Kısa Hukuki Bilgi**");
}

interface ParsedMessage {
  content: string;
  actions: string[];
}
function parseMessage(rawText: string): ParsedMessage {
  let actions: string[] = [];
  let content = rawText;
  const mainMatch = rawText.match(/<MAIN>([\s\S]*?)<\/MAIN>/i);
  const actionsMatch = rawText.match(/<ACTIONS>([\s\S]*?)<\/ACTIONS>/i);
  if (mainMatch && actionsMatch) {
    content = mainMatch[1].trim();
    actions = extractActionsList(actionsMatch[1]);
    return {
      content: softenMarkdownHeadings(content.trim()),
      actions: deduplicateActions(actions),
    };
  }
  const fallbackSplit = rawText.split(/###ÖNERİLER###/i);
  if (fallbackSplit.length > 1) {
    content = fallbackSplit[0].trim();
    actions = extractActionsList(fallbackSplit[1]);
    return {
      content: softenMarkdownHeadings(content.trim()),
      actions: deduplicateActions(actions),
    };
  }
  const fallbackSplit2 = rawText.split(
    /\*\*Sizin için önerilerim:\*\*|Sizin için önerilerim:/i,
  );
  if (fallbackSplit2.length > 1) {
    content = fallbackSplit2[0].trim();
    actions = extractActionsList(fallbackSplit2[1]);
    return {
      content: softenMarkdownHeadings(content.trim()),
      actions: deduplicateActions(actions),
    };
  }
  return { content: softenMarkdownHeadings(content.trim()), actions: [] };
}
function extractActionsList(text: string): string[] {
  return text
    .split("\n")
    .map((l) => l.trim())
    .filter((l) => l.startsWith("-"))
    .map((l) => l.substring(1).trim())
    .slice(0, 3);
}
function deduplicateActions(actions: string[]) {
  return Array.from(new Set(actions));
}

function condenseActionText(original: string): string {
  if (original.length <= 40) return original;
  let cleaned = original
    .replace(
      /^(Hakkında|Hakkında bilgi almak ister misiniz\?|Bilgi almak ister misiniz\?|Nasıl yapılır\?|Ne anlama gelir\?|Nedir\?|Hakkında bilgi|Hakkında yardım)\s*/i,
      "",
    )
    .replace(
      /öğrenmek istiyorum|detaylı bilgi|hakkında bilgi almak|ister misiniz|bilgi almak/gi,
      "",
    )
    .trim();
  if (cleaned.length > 35) cleaned = cleaned.substring(0, 35).trim() + "…";
  return cleaned || original.substring(0, 35);
}

// ---------- TYPES ----------
interface LawSource {
  kanun: string;
  madde: string;
  ozet: string;
}
interface Message {
  id: number;
  text: string;
  sender: "bot" | "user" | "system";
  sources?: LawSource[];
  isLoading?: boolean;
  content?: string;
  actions?: string[];
  actionsDisabled?: boolean;
}

// ---------- TYPEWRITER ----------
function useTypewriter(text: string, speed = 15, shouldStop = false) {
  const [displayed, setDisplayed] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    if (!text) {
      setDisplayed("");
      setIsTyping(false);
      return;
    }

    let i = 0;
    setDisplayed("");
    setIsTyping(true);

    intervalRef.current = setInterval(() => {
      setDisplayed(text.slice(0, i + 1));
      i++;
      if (i >= text.length) {
        if (intervalRef.current) clearInterval(intervalRef.current);
        setIsTyping(false);
      }
    }, speed);

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
      setIsTyping(false);
    };
  }, [text, speed]);

  useEffect(() => {
    if (shouldStop && intervalRef.current) {
      clearInterval(intervalRef.current);
      setDisplayed(text);
      setIsTyping(false);
    }
  }, [shouldStop, text]);

  return { displayed, isTyping };
}

// ---------- BOT MESSAGE CONTENT ----------
const BotMessageContent = ({
  content,
  enableTypewriter = true,
  shouldStopTyping = false,
  onTypingStatusChange,
}: {
  content: string;
  enableTypewriter?: boolean;
  shouldStopTyping?: boolean;
  onTypingStatusChange?: (isTyping: boolean) => void;
}) => {
  const { displayed, isTyping } = useTypewriter(
    enableTypewriter ? content : "",
    15,
    shouldStopTyping,
  );
  const displayText = enableTypewriter ? displayed : content;

  useEffect(() => {
    onTypingStatusChange?.(isTyping);
  }, [isTyping, onTypingStatusChange]);

  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        h3: ({ children }) => (
          <h3 className="font-semibold text-[#0B1F3B] text-sm mt-2 mb-1">
            {children}
          </h3>
        ),
        p: ({ children }) => (
          <p className="mb-2 leading-relaxed text-[13px] last:mb-0">
            {children}
          </p>
        ),
        strong: ({ children }) => (
          <strong className="font-semibold text-[#0B1F3B]">{children}</strong>
        ),
        li: ({ children }) => (
          <li className="ml-4 list-disc text-[13px]">{children}</li>
        ),
        ul: ({ children }) => <ul className="mb-2">{children}</ul>,
        a: ({ href, children }) => (
          <a
            href={href}
            target="_blank"
            rel="noopener noreferrer"
            className="text-[#C89C5D] underline hover:opacity-80"
          >
            {children}
          </a>
        ),
      }}
    >
      {displayText}
    </ReactMarkdown>
  );
};

// ---------- MESSAGE BUBBLE ----------
const MessageBubble = ({
  message,
  isSystem,
  shouldStopTyping,
  activeTypingMessageId,
  onTypingStatusChange,
  visibleActions,
  selectedAction,
  onActionClick,
}: {
  message: Message;
  isSystem: boolean;
  shouldStopTyping: boolean;
  activeTypingMessageId: number | null;
  onTypingStatusChange: (isTyping: boolean) => void;
  onSourceClick?: (source: LawSource) => void;
  visibleActions: Record<number, boolean>;
  selectedAction: Record<number, number>;
  onActionClick: (action: string, messageId: number, index: number) => void;
}) => {
  return (
    <div
      className={cn(
        "flex animate-messageIn gap-2",
        message.sender === "user" ? "justify-end" : "justify-start",
        isSystem && "justify-center",
      )}
    >
      {message.sender === "bot" && !isSystem && (
        <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-gradient-to-br from-[#C89C5D] to-[#B38A4D] flex items-center justify-center shadow-md mt-1">
          <Scale className="w-4 h-4 text-white" />
        </div>
      )}

      <div
        className={cn(
          "flex flex-col gap-2",
          message.sender === "user"
            ? "max-w-[85%]"
            : isSystem
              ? "max-w-[90%]"
              : "max-w-[85%]",
        )}
      >
        <div
          className={cn(
            "rounded-2xl text-[13px] leading-relaxed shadow-sm",
            message.sender === "user"
              ? "bg-gradient-to-br from-[#0B1F3B] to-[#071628] text-white rounded-br-md px-3 py-2"
              : isSystem
                ? "bg-gray-100 text-gray-600 text-center rounded-xl border border-gray-200 px-4 py-2"
                : "bg-white/90 backdrop-blur-sm text-gray-800 rounded-bl-md border border-gray-100 px-3 py-2",
          )}
        >
          {message.isLoading ? (
            <div className="flex items-center gap-2.5 text-gray-600">
              <Loader2 className="w-4 h-4 animate-spin text-[#C89C5D]" />
              <span className="italic font-medium text-[13px]">
                {message.text || "Hukuki analiz yapılıyor..."}
              </span>
            </div>
          ) : (
            <>
              {message.sender === "bot" && !isSystem ? (
                <BotMessageContent
                  content={message.content || message.text || ""}
                  enableTypewriter={true}
                  shouldStopTyping={
                    shouldStopTyping && activeTypingMessageId === message.id
                  }
                  onTypingStatusChange={onTypingStatusChange}
                />
              ) : (
                <div className="whitespace-pre-wrap">
                  {message.content || message.text}
                </div>
              )}
            </>
          )}
        </div>
        {message.sender === "bot" &&
          !isSystem &&
          message.actions &&
          message.actions.length > 0 &&
          !message.isLoading &&
          !message.actionsDisabled &&
          visibleActions[message.id] && (
            <div className="flex flex-wrap gap-2 mt-3">
              {message.actions.map((action, idx) => {
                const isSelected = selectedAction[message.id] === idx;
                const shouldHide =
                  selectedAction[message.id] !== undefined && !isSelected;
                const condensed = condenseActionText(action);
                return (
                  <button
                    key={idx}
                    onClick={() => onActionClick(action, message.id, idx)}
                    className={cn(
                      "transition-all duration-200 ease-out px-3 py-1.5 rounded-lg text-xs font-semibold leading-snug max-w-[80%] truncate animate-fadeSlideIn",
                      "focus:outline-none focus:ring-2 focus:ring-[#C89C5D]/50 active:scale-95",
                      idx === 0
                        ? "bg-[#C89C5D] text-white hover:bg-[#B38A4D] hover:scale-105 shadow-sm"
                        : "bg-gray-100 text-gray-700 hover:bg-gray-200 hover:scale-105 border border-gray-200",
                      shouldHide && "opacity-0 scale-95 pointer-events-none",
                    )}
                    title={action}
                  >
                    {condensed}
                  </button>
                );
              })}
            </div>
          )}
      </div>
    </div>
  );
};

// ---------- MAIN COMPONENT ----------
export function ChatbotWidget() {
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    const handleToggle = () => setIsOpen((prev) => !prev);
    window.addEventListener("toggle-chatbot", handleToggle);
    return () => window.removeEventListener("toggle-chatbot", handleToggle);
  }, []);
  const [showSourceModal, setShowSourceModal] = useState(false);
  const [selectedSource, setSelectedSource] = useState<LawSource | null>(null);
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 1,
      text: "Merhaba! LawAgent AI hukuki asistanına hoş geldiniz. Size nasıl yardımcı olabilirim?",
      sender: "bot",
      content:
        "Merhaba! LawAgent AI hukuki asistanına hoş geldiniz. Size nasıl yardımcı olabilirim?",
      actions: [],
    },
  ]);
  const [inputValue, setInputValue] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);
  const [visibleActions, setVisibleActions] = useState<Record<number, boolean>>(
    {},
  );
  const [selectedAction, setSelectedAction] = useState<Record<number, number>>(
    {},
  );

  const [connectionStatus, setConnectionStatus] = useState<
    "online" | "offline"
  >("online");
  const [offlineBannerShown, setOfflineBannerShown] = useState(false);

  const [isFullscreen, setIsFullscreen] = useState(false);
  const [dimensions, setDimensions] = useState({
    width: 420,
    height: 600,
  });

  const [shouldStopTyping, setShouldStopTyping] = useState(false);
  const [activeTypingMessageId, setActiveTypingMessageId] = useState<
    number | null
  >(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const [isDesktop, setIsDesktop] = useState(
    typeof window !== "undefined" && window.innerWidth >= 640,
  );

  const loadingTips = [
    "Mevzuat taranıyor...",
    "Yargıtay kararları inceleniyor...",
    "İçtihatlar analiz ediliyor...",
    "Hukuki emsaller değerlendiriliyor...",
    "Kanun maddeleri kontrol ediliyor...",
  ];
  const [currentLoadingTip, setCurrentLoadingTip] = useState(loadingTips[0]);

  useEffect(() => {
    const handleResize = () => {
      setIsDesktop(window.innerWidth >= 640);
    };
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  useEffect(() => {
    if (scrollRef.current)
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages]);

  useEffect(() => {
    if (messages.some((m) => m.isLoading)) {
      const interval = setInterval(() => {
        setCurrentLoadingTip((prev) => {
          const currentIndex = loadingTips.indexOf(prev);
          const nextIndex = (currentIndex + 1) % loadingTips.length;
          return loadingTips[nextIndex];
        });
      }, 2000);
      return () => clearInterval(interval);
    }
  }, [messages]);

  const showOfflineSystemMessage = () => {
    if (offlineBannerShown) return;
    setOfflineBannerShown(true);
    const systemMsg: Message = {
      id: Date.now(),
      text: "Geçici bir teknik aksaklık nedeniyle yanıt veremiyoruz. En kısa sürede tekrar aktif olacağız.",
      sender: "system",
      content:
        "Geçici bir teknik aksaklık nedeniyle yanıt veremiyoruz. En kısa sürede tekrar aktif olacağız.",
      actions: [],
    };
    setMessages((prev) => [...prev, systemMsg]);
  };

  const handleActionClick = (
    action: string,
    messageId: number,
    index: number,
  ) => {
    setSelectedAction((prev) => ({
      ...prev,
      [messageId]: index,
    }));
    handleSend(action);
  };

  const handleSend = async (text?: string) => {
    const messageText = text || inputValue.trim();
    if (!messageText) return;

    const userMessage: Message = {
      id: Date.now(),
      text: messageText,
      sender: "user",
      content: messageText,
      actions: [],
    };
    const botLoadingId = Date.now() + 1;
    const botLoadingMessage: Message = {
      id: botLoadingId,
      text: currentLoadingTip,
      sender: "bot",
      isLoading: true,
      content: currentLoadingTip,
      actions: [],
    };

    setMessages((prev) => [...prev, userMessage, botLoadingMessage]);
    setInputValue("");

    const intent = detectIntent(messageText);
    if (intent === "meta") {
      const meta = getMetaResponse();
      setMessages((prev) => prev.filter((msg) => msg.id !== botLoadingId));
      const newMessageId = botLoadingId;
      setMessages((prev) => [
        ...prev,
        {
          id: newMessageId,
          text: meta.content,
          content: meta.content,
          sender: "bot",
          actions: meta.actions,
          sources: [],
          isLoading: false,
          actionsDisabled: false,
        },
      ]);
      setActiveTypingMessageId(newMessageId);
      setShouldStopTyping(false);
      setTimeout(() => {
        setVisibleActions((prev) => ({ ...prev, [newMessageId]: true }));
      }, 500);
      return;
    }

    if (intent === "chitchat") {
      const chit = getChitchatResponse();
      setMessages((prev) => prev.filter((msg) => msg.id !== botLoadingId));
      const newMessageId = botLoadingId;
      setMessages((prev) => [
        ...prev,
        {
          id: newMessageId,
          text: chit.content,
          content: chit.content,
          sender: "bot",
          actions: chit.actions,
          sources: [],
          isLoading: false,
          actionsDisabled: false,
        },
      ]);
      setActiveTypingMessageId(newMessageId);
      setShouldStopTyping(false);
      setTimeout(() => {
        setVisibleActions((prev) => ({ ...prev, [newMessageId]: true }));
      }, 500);
      return;
    }

    const sessionId =
      localStorage.getItem("chatbot_session_id") || `session_${Date.now()}`;
    localStorage.setItem("chatbot_session_id", sessionId);

    const sendRequest = async () => {
      try {
        const apiUrl = `${import.meta.env.VITE_API_URL || "https://hllerdgn-lawagent-backend.hf.space"}/ask`;
        const controller = new AbortController();
        abortControllerRef.current = controller;
        const timeoutId = setTimeout(() => controller.abort(), 15000);
        const response = await fetch(apiUrl, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "bypass-tunnel-reminder": "69420",
            Accept: "application/json",
          },
          body: JSON.stringify({
            query: messageText,
            session_id: sessionId,
            k: 7,
          }),
          signal: controller.signal,
          mode: "cors",
        });
        clearTimeout(timeoutId);
        abortControllerRef.current = null;
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();
        let rawAnswer =
          data.answer || data.response || data.text || "Yanıt alınamadı.";
        let parsed = parseMessage(rawAnswer);
        const enrichedContent = enrichLegalLinks(parsed.content);

        setMessages((prev) => prev.filter((msg) => msg.id !== botLoadingId));
        const newMessageId = botLoadingId;
        setMessages((prev) => [
          ...prev,
          {
            id: newMessageId,
            text: enrichedContent,
            content: enrichedContent,
            sender: "bot",
            actions: parsed.actions,
            sources: [],
            isLoading: false,
            actionsDisabled: false,
          },
        ]);
        setActiveTypingMessageId(newMessageId);
        setShouldStopTyping(false);
        setTimeout(() => {
          setVisibleActions((prev) => ({ ...prev, [newMessageId]: true }));
        }, 500);

        if (connectionStatus === "offline") setConnectionStatus("online");
        return true;
      } catch (error) {
        console.error("API hatası:", error);
        if (connectionStatus !== "offline") {
          setConnectionStatus("offline");
          showOfflineSystemMessage();
        }
        const friendlyMessages = [
          "Şu anda hizmet veremiyoruz. Lütfen biraz sonra tekrar deneyin.",
          "Geçici bir teknik aksaklık oluştu.",
          "Bağlantıda kısa süreli bir sorun oluştu. Sorunuz kaybolmadı, tekrar deneyebilirsiniz.",
        ];
        const fallbackText =
          friendlyMessages[Math.floor(Math.random() * friendlyMessages.length)];
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === botLoadingId
              ? {
                  ...msg,
                  text: fallbackText,
                  content: fallbackText,
                  actions: [],
                  sources: [],
                  isLoading: false,
                  actionsDisabled: false,
                }
              : msg,
          ),
        );
        return false;
      }
    };
    await sendRequest();
  };

  const handleSourceClick = (source: LawSource) => {
    setSelectedSource(source);
    setShowSourceModal(true);
  };

  const handleStopGeneration = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setShouldStopTyping(true);
    setTimeout(() => {
      setActiveTypingMessageId(null);
      setShouldStopTyping(false);
    }, 300);
  }, []);

  const toggleFullscreen = useCallback(() => {
    setIsFullscreen((prev) => !prev);
  }, []);

  const handleTypingStatusChange = useCallback(
    (messageId: number) => (isTyping: boolean) => {
      if (!isTyping && activeTypingMessageId === messageId) {
        setActiveTypingMessageId(null);
      }
    },
    [activeTypingMessageId],
  );

  // Resize logic
  const resizeRef = useRef<HTMLDivElement>(null);
  const [isResizing, setIsResizing] = useState(false);
  const resizeStartRef = useRef({
    x: 0,
    y: 0,
    width: 0,
    height: 0,
  });

  const handleResizeStart = useCallback(
    (e: React.MouseEvent) => {
      if (isFullscreen || !isDesktop) return;
      e.preventDefault();
      setIsResizing(true);
      resizeStartRef.current = {
        x: e.clientX,
        y: e.clientY,
        width: dimensions.width,
        height: dimensions.height,
      };
    },
    [isFullscreen, isDesktop, dimensions],
  );

  useEffect(() => {
    if (!isResizing) return;
    const handleResizeMove = (e: MouseEvent) => {
      const deltaX = resizeStartRef.current.x - e.clientX;
      const deltaY = e.clientY - resizeStartRef.current.y;
      const newWidth = Math.max(
        320,
        Math.min(
          window.innerWidth * 0.9,
          resizeStartRef.current.width + deltaX,
        ),
      );
      const newHeight = Math.max(
        400,
        Math.min(
          window.innerHeight * 0.9,
          resizeStartRef.current.height + deltaY,
        ),
      );
      setDimensions({ width: newWidth, height: newHeight });
    };
    const handleResizeEnd = () => setIsResizing(false);
    document.addEventListener("mousemove", handleResizeMove);
    document.addEventListener("mouseup", handleResizeEnd);
    return () => {
      document.removeEventListener("mousemove", handleResizeMove);
      document.removeEventListener("mouseup", handleResizeEnd);
    };
  }, [isResizing]);

  return (
    <>
      <div className="fixed bottom-6 right-6 z-50 group/tooltip">
        {!isOpen && (
          <div className="absolute bottom-full right-0 mb-2 opacity-0 group-hover/tooltip:opacity-100 transition-opacity duration-200 pointer-events-none">
            <div className="bg-gray-900 text-white px-4 py-2 rounded-lg text-sm font-medium whitespace-nowrap shadow-lg">
              AI Hukuk Asistanı ile konuş
              <div className="absolute top-full right-6 w-0 h-0 border-l-8 border-r-8 border-t-8 border-transparent border-t-gray-900"></div>
            </div>
          </div>
        )}
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="w-14 h-14 sm:w-16 sm:h-16 rounded-full shadow-2xl flex items-center justify-center bg-gradient-to-tr from-[#0B1F3B] to-[#071628] text-white transition-all duration-300 hover:scale-110 active:scale-95 group"
          aria-label="AI Chatbot"
        >
          {isOpen ? (
            <X className="w-7 h-7" />
          ) : (
            <>
              <Scale className="w-7 h-7 group-hover:scale-110 transition-transform" />
              <span className="absolute -top-1 -right-1 w-3 h-3 bg-[#C89C5D] rounded-full animate-ping" />
              <span className="absolute -top-1 -right-1 w-3 h-3 bg-[#C89C5D] rounded-full" />
            </>
          )}
        </button>
      </div>

      {isOpen && (
        <div
          className={cn(
            "fixed z-50 flex flex-col overflow-hidden bg-white shadow-2xl animate-fadeIn border border-gray-100 transition-all duration-300",
            isFullscreen
              ? "inset-0 rounded-none"
              : "inset-0 sm:inset-auto sm:bottom-24 sm:right-6 sm:rounded-2xl",
          )}
          style={
            !isFullscreen && isDesktop
              ? {
                  width: `${dimensions.width}px`,
                  height: `${dimensions.height}px`,
                  maxWidth: "90vw",
                  maxHeight: "90vh",
                }
              : undefined
          }
        >
          <div className="bg-gradient-to-r from-[#0B1F3B] to-[#071628] p-4 flex items-center justify-between shadow-lg">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-gradient-to-br from-[#C89C5D] to-[#B38A4D] rounded-lg flex items-center justify-center">
                <Scale className="w-5 h-5 text-white" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="text-white font-semibold text-sm">
                    LawAgent AI
                  </h2>
                  <span
                    className={`w-2 h-2 rounded-full ${
                      connectionStatus === "online"
                        ? "bg-green-500 animate-pulse"
                        : "bg-red-500"
                    }`}
                  />
                </div>
                <p className="text-gray-400 text-xs">Hukuki Asistan</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              {activeTypingMessageId !== null && (
                <button
                  onClick={handleStopGeneration}
                  className="text-white hover:bg-white/20 p-2 rounded-lg transition-all group flex items-center gap-1.5 bg-red-500/20 border border-red-400/30"
                  title="Yanıtı Durdur"
                >
                  <StopCircle className="w-4 h-4 text-red-400 group-hover:text-red-300" />
                  <span className="text-xs font-medium text-red-300">
                    Durdur
                  </span>
                </button>
              )}
              {isDesktop && (
                <button
                  onClick={toggleFullscreen}
                  className="text-white hover:bg-white/20 p-2 rounded-lg transition-all"
                  title={isFullscreen ? "Normal Boyut" : "Tam Ekran"}
                >
                  {isFullscreen ? (
                    <Minimize2 className="w-4 h-4" />
                  ) : (
                    <Maximize2 className="w-4 h-4" />
                  )}
                </button>
              )}
              <button
                onClick={() => setIsOpen(false)}
                className="text-white hover:bg-white/20 p-2 rounded-lg transition-all"
                title="Kapat"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>
          <div className="bg-blue-50/50 border-b border-blue-100 px-4 py-2 text-[10px] text-blue-800 leading-tight flex items-start gap-2">
            <Info className="w-3 h-3 text-blue-600 flex-shrink-0 mt-0.5" />
            <span>
              <strong>Önemli Bilgilendirme:</strong> Bu AI asistan genel bilgi
              amaçlıdır. Detaylı hukuki danışmanlık için lütfen ekibimizle
              iletişime geçin.
            </span>
          </div>
          <div
            ref={scrollRef}
            className="flex-1 overflow-y-auto p-4 space-y-4 bg-gray-50"
          >
            {messages.map((message) => {
              const isSystem = message.sender === "system";
              return (
                <MessageBubble
                  key={message.id}
                  message={message}
                  isSystem={isSystem}
                  shouldStopTyping={shouldStopTyping}
                  activeTypingMessageId={activeTypingMessageId}
                  onTypingStatusChange={handleTypingStatusChange(message.id)}
                  onSourceClick={handleSourceClick}
                  visibleActions={visibleActions}
                  selectedAction={selectedAction}
                  onActionClick={handleActionClick}
                />
              );
            })}
          </div>
          {!isFullscreen && isDesktop && (
            <div
              ref={resizeRef}
              onMouseDown={handleResizeStart}
              className="absolute bottom-0 right-0 w-6 h-6 cursor-nwse-resize group z-10"
              title="Sürükleyerek boyutlandır"
            >
              <div className="absolute bottom-1 right-1 w-4 h-4 flex flex-col gap-0.5 items-end justify-end opacity-40 group-hover:opacity-70 transition-opacity">
                <div className="flex gap-0.5">
                  <div className="w-1 h-1 bg-gray-400 rounded-full"></div>
                  <div className="w-1 h-1 bg-gray-400 rounded-full"></div>
                </div>
                <div className="flex gap-0.5">
                  <div className="w-1 h-1 bg-gray-400 rounded-full"></div>
                </div>
              </div>
            </div>
          )}
          <div className="p-4 border-t bg-white relative">
            <div className="flex items-center gap-2 bg-gradient-to-r from-gray-50 to-gray-100 rounded-xl px-3 py-2 border border-gray-200 focus-within:border-[#0B1F3B]">
              <input
                type="text"
                placeholder="Hukuki sorunuzu yazın…"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSend()}
                className="flex-1 bg-transparent outline-none text-sm text-gray-700"
                disabled={connectionStatus === "offline"}
              />
              <button
                onClick={() => handleSend()}
                disabled={!inputValue.trim() || connectionStatus === "offline"}
                className="w-9 h-9 flex items-center justify-center rounded-lg bg-gradient-to-br from-[#0B1F3B] to-[#071628] text-white hover:scale-105 disabled:opacity-40 disabled:cursor-not-allowed"
              >
                <Send className="w-4 h-4" />
              </button>
            </div>
            <p className="text-[10px] text-gray-400 mt-2 text-center">
              LawAgent AI | Hukuki Asistan
            </p>
          </div>
        </div>
      )}
      {showSourceModal && selectedSource && (
        <div
          className="fixed inset-0 z-[60] bg-black/50 backdrop-blur-sm flex items-center justify-center p-4 animate-fadeIn"
          onClick={() => setShowSourceModal(false)}
        >
          <div
            className="bg-white rounded-2xl shadow-2xl max-w-lg w-full p-6 animate-scaleIn"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-start justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 bg-gradient-to-br from-[#C89C5D] to-[#B38A4D] rounded-lg flex items-center justify-center">
                  <Scale className="w-6 h-6 text-white" />
                </div>
                <div>
                  <h3 className="text-[#0B1F3B] font-bold">
                    {selectedSource.kanun} - Madde {selectedSource.madde}
                  </h3>
                  <p className="text-xs text-gray-500">Hukuki Kaynak Detayı</p>
                </div>
              </div>
              <button
                onClick={() => setShowSourceModal(false)}
                className="text-gray-400 hover:text-gray-700"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-5 bg-gradient-to-br from-slate-50 to-blue-50 rounded-xl border-l-4 border-[#C89C5D]">
              <p className="text-sm text-slate-700">"{selectedSource.ozet}"</p>
            </div>
            <div className="mt-5 flex justify-end">
              <button
                onClick={() => setShowSourceModal(false)}
                className="px-5 py-2.5 bg-gradient-to-r from-[#0B1F3B] to-[#071628] text-white rounded-lg"
              >
                Anladım
              </button>
            </div>
          </div>
        </div>
      )}

      <style>{`
        @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
        @keyframes messageIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
        @keyframes scaleIn { from { opacity: 0; transform: scale(0.95); } to { opacity: 1; transform: scale(1); } }
        @keyframes fadeSlideIn { from { opacity: 0; transform: translateY(5px); } to { opacity: 1; transform: translateY(0); } }
        .animate-fadeSlideIn { animation: fadeSlideIn 0.2s ease-out forwards; }
        .animate-fadeIn { animation: fadeIn 0.3s ease-out; }
        .animate-messageIn { animation: messageIn 0.25s ease-out forwards; }
        .animate-scaleIn { animation: scaleIn 0.2s ease-out; }
        .overflow-y-auto::-webkit-scrollbar { width: 6px; }
        .overflow-y-auto::-webkit-scrollbar-track { background: #f0f2f5; border-radius: 10px; }
        .overflow-y-auto::-webkit-scrollbar-thumb { background: #C89C5D; border-radius: 10px; }
        .cursor-nwse-resize { cursor: nwse-resize; }
        ${isResizing ? "body { user-select: none; }" : ""}
      `}</style>
    </>
  );
}

export default ChatbotWidget;

