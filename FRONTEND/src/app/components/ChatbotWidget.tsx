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
  Home,
  BookOpen,
  FileText,
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useNavigate } from "react-router-dom";

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

function enrichLegalLinks(text: string): string {
  return text;
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

interface ParsedBotResponse {
  explanation: string;
  closingQuestion: string;
}

function parseBotResponse(text: string): ParsedBotResponse {
  let cleaned = text.trim();
  
  // If the response is not a structured legal response (does not contain standard headers),
  // we do not attempt to split it. We return it as is.
  const isStructured = 
    cleaned.includes("**Hukuki Değerlendirme**") || 
    cleaned.includes("**Kısa Bilgi**") || 
    cleaned.includes("**Dayanak Mevzuat**") || 
    cleaned.includes("**Dayanak Belge**");
    
  if (!isStructured) {
    return {
      explanation: cleaned,
      closingQuestion: "",
    };
  }

  // 1. Remove starting title like "**Hukuki Değerlendirme**" or "**Kısa Bilgi**"
  cleaned = cleaned.replace(/^(\*\*Hukuki Değerlendirme\*\*|\*\*Kısa Bilgi\*\*)\s*/i, "");
  
  // 2. Extract closing question
  let closingQuestion = "";
  
  // Try splitting by "---" first
  const separatorIndex = cleaned.lastIndexOf("---");
  if (separatorIndex !== -1) {
    closingQuestion = cleaned.substring(separatorIndex + 3).trim();
    cleaned = cleaned.substring(0, separatorIndex).trim();
  } else {
    // If no separator, look for typical closing questions
    const paragraphs = cleaned.split("\n\n");
    if (paragraphs.length > 1) {
      const lastParagraph = paragraphs[paragraphs.length - 1].trim();
      if (
        lastParagraph.endsWith("?") || 
        lastParagraph.toLowerCase().includes("ister misiniz") || 
        lastParagraph.toLowerCase().includes("başka bir sorunuz var mı")
      ) {
        closingQuestion = lastParagraph;
        paragraphs.pop();
        cleaned = paragraphs.join("\n\n").trim();
      }
    }
  }
  
  // 3. Remove "**Dayanak Mevzuat**" or "**Dayanak Belge**" and everything after it
  const dayanakRegex = /\*\*Dayanak (Mevzuat|Belge)\*\*/i;
  const match = cleaned.match(dayanakRegex);
  if (match && match.index !== undefined) {
    cleaned = cleaned.substring(0, match.index).trim();
  }

  return {
    explanation: cleaned.trim(),
    closingQuestion: closingQuestion.trim(),
  };
}

function formatSourceLabel(source: LawSource): string {
  let kanun = source.kanun.trim();
  const madde = source.madde ? source.madde.trim() : "";
  
  if (kanun === "TKHK" || kanun === "6502 sayılı Tüketicinin Korunması Hakkında Kanun") {
    kanun = "6502 sayılı TKHK";
  } else if (kanun === "TBK" || kanun === "6098 sayılı Türk Borçlar Kanunu") {
    kanun = "6098 sayılı TBK";
  } else if (kanun === "TTK" || kanun === "6102 sayılı Türk Ticaret Kanunu") {
    kanun = "6102 sayılı TTK";
  }
  
  if (!madde) return kanun;
  
  if (kanun.toLowerCase().includes("yargıtay")) {
    return `${kanun} ${madde}`;
  }
  
  if (kanun.toLowerCase().includes("belge") || kanun.toLowerCase().includes("site_document")) {
    return `${kanun}: ${madde}`;
  }
  
  return `${kanun} m. ${madde}`;
}

function formatChipLabel(source: LawSource): string {
  let kanun = source.kanun.trim();
  const madde = source.madde ? source.madde.trim() : "";
  
  if (kanun === "6502 sayılı Tüketicinin Korunması Hakkında Kanun" || kanun === "6502 sayılı TKHK") {
    kanun = "TKHK";
  } else if (kanun === "6098 sayılı Türk Borçlar Kanunu" || kanun === "6098 sayılı TBK") {
    kanun = "TBK";
  } else if (kanun === "6102 sayılı Türk Ticaret Kanunu" || kanun === "6102 sayılı TTK") {
    kanun = "TTK";
  }
  
  if (!madde) return kanun;
  
  if (kanun.toLowerCase().includes("yargıtay")) {
    const shortMadde = madde.length > 20 ? madde.substring(0, 20) + "…" : madde;
    return `${kanun} ${shortMadde}`;
  }
  
  if (kanun.toLowerCase().includes("belge") || kanun.toLowerCase().includes("site_document")) {
    return `${kanun}: ${madde}`;
  }
  
  return `${kanun} m. ${madde}`;
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

// ---------- LAW CATEGORIES ----------
const LAW_CATEGORIES = [
  { label: "Borçlar Hukuku", query: "Borçlar hukuku kapsamında temel haklarım nelerdir?" },
  { label: "Ticaret Hukuku", query: "Ticaret hukuku kapsamında şirket kuruluşu nasıl yapılır?" },
  { label: "Tüketici Hukuku", query: "Tüketici hakları nelerdir?" },
];

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
            className="text-[#C89C5D] underline hover:opacity-80 font-semibold"
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

// ---------- SOURCE CHIP ----------
const SourceChip = ({
  source,
  onClick,
}: {
  source: LawSource;
  onClick: (source: LawSource) => void;
}) => {
  const label = formatChipLabel(source);

  return (
    <button
      onClick={() => onClick(source)}
      className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[10px] font-semibold transition-all duration-200 hover:scale-105 active:scale-95 cursor-pointer"
      style={{
        fontFamily: "var(--font-label)",
        letterSpacing: "0.08em",
        textTransform: "uppercase",
        background: "var(--color-paper-2)",
        color: "var(--color-accent)",
        border: "1px solid var(--color-rule)",
      }}
      title={source.ozet}
    >
      <FileText className="w-3 h-3 flex-shrink-0" />
      <span className="truncate max-w-[140px]">{label}</span>
    </button>
  );
};

// ---------- MESSAGE BUBBLE ----------
const MessageBubble = ({
  message,
  isSystem,
  shouldStopTyping,
  activeTypingMessageId,
  onTypingStatusChange,
  onSourceClick,
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
        <div
          className="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center shadow-xs mt-1"
          style={{ background: "var(--color-paper-2)", border: "1px solid var(--color-rule)" }}
        >
          <Scale className="w-4 h-4" style={{ color: "var(--color-accent)" }} />
        </div>
      )}

      <div
        className={cn(
          "flex flex-col gap-1",
          message.sender === "user"
            ? "max-w-[85%]"
            : isSystem
              ? "max-w-[90%]"
              : "max-w-[85%]",
        )}
      >
        <div
          className={cn(
            "rounded-2xl text-[13px] leading-relaxed shadow-xs",
            message.sender === "user"
              ? "bg-[var(--color-accent)] text-[var(--color-paper)] rounded-br-md px-3.5 py-2.5"
              : isSystem
                ? "bg-[var(--color-paper-2)] text-[var(--color-muted)] text-center rounded-xl border border-[var(--color-rule)] px-4 py-2"
                : "bg-[var(--color-paper)] text-[var(--color-ink)] rounded-2xl rounded-tl-none border border-[var(--color-rule)] px-4 py-3.5",
          )}
          style={{ fontFamily: "var(--font-body)", textTransform: "lowercase" }}
        >
          {message.isLoading ? (
            <div className="flex items-center gap-2.5" style={{ color: "var(--color-ink-2)" }}>
              <Loader2 className="w-4 h-4 animate-spin" style={{ color: "var(--color-accent)" }} />
              <span className="italic font-medium text-[13px]">
                {message.text || "hukuki analiz yapılıyor..."}
              </span>
            </div>
          ) : (
            <>
              {message.sender === "bot" && !isSystem && (
                <div
                  className="font-bold text-[11px] mb-1.5"
                  style={{
                    fontFamily: "var(--font-label)",
                    letterSpacing: "0.10em",
                    textTransform: "uppercase",
                    color: "var(--color-accent)",
                  }}
                >
                  LAWAGENT AI
                </div>
              )}
              {message.sender === "bot" && !isSystem ? (() => {
                const botResponse = parseBotResponse(message.content || message.text || "");
                const isCurrentTyping = activeTypingMessageId === message.id;
                return (
                  <>
                    <BotMessageContent
                      content={botResponse.explanation}
                      enableTypewriter={true}
                      shouldStopTyping={
                        shouldStopTyping && isCurrentTyping
                      }
                      onTypingStatusChange={onTypingStatusChange}
                    />
                    
                    {/* Unique Sources list inside card */}
                    {message.sources && message.sources.length > 0 && !isCurrentTyping && (
                      <div
                        className="mt-3 pt-3 border-t animate-fadeSlideIn"
                        style={{ borderColor: "var(--color-rule)" }}
                      >
                        <div
                          className="font-bold text-[10px] mb-1.5"
                          style={{
                            fontFamily: "var(--font-label)",
                            letterSpacing: "0.10em",
                            textTransform: "uppercase",
                            color: "var(--color-accent)",
                          }}
                        >
                          KAYNAKLAR:
                        </div>
                        <ul className="space-y-1.5">
                          {message.sources
                            .filter(
                              (s, i, arr) =>
                                arr.findIndex(
                                  (x) => x.kanun === s.kanun && x.madde === s.madde,
                                ) === i,
                            )
                            .slice(0, 4)
                            .map((source, idx) => (
                              <li
                                key={idx}
                                onClick={() => onSourceClick?.(source)}
                                className="flex items-start gap-1.5 text-[12px] font-semibold hover:opacity-80 active:scale-[0.99] cursor-pointer transition-all"
                                style={{
                                  fontFamily: "var(--font-label)",
                                  textTransform: "uppercase",
                                  color: "var(--color-accent)",
                                }}
                              >
                                <span style={{ color: "var(--color-accent-2)" }}>•</span>
                                <span>{formatSourceLabel(source)}</span>
                              </li>
                            ))}
                        </ul>
                      </div>
                    )}
                    
                    {/* Closing question */}
                    {botResponse.closingQuestion && !isCurrentTyping && (
                      <div
                        className="mt-3 text-[12px] leading-relaxed animate-fadeSlideIn"
                        style={{ color: "var(--color-muted)" }}
                      >
                        {botResponse.closingQuestion}
                      </div>
                    )}
                  </>
                );
              })() : (
                <div className="whitespace-pre-wrap">
                  {message.content || message.text}
                </div>
              )}
            </>
          )}
        </div>

        {/* Source chips - poster style */}
        {message.sender === "bot" &&
          !isSystem &&
          !message.isLoading &&
          message.sources &&
          message.sources.length > 0 && (
            <div className="flex flex-wrap gap-1.5 mt-1 ml-1">
              {message.sources
                .filter(
                  (s, i, arr) =>
                    arr.findIndex(
                      (x) => x.kanun === s.kanun && x.madde === s.madde,
                    ) === i,
                )
                .slice(0, 4)
                .map((source, idx) => (
                  <SourceChip
                    key={idx}
                    source={source}
                    onClick={onSourceClick || (() => {})}
                  />
                ))}
            </div>
          )}

        {/* Action buttons */}
        {message.sender === "bot" &&
          !isSystem &&
          message.actions &&
          message.actions.length > 0 &&
          !message.isLoading &&
          !message.actionsDisabled &&
          visibleActions[message.id] && (
            <div className="flex flex-wrap gap-2 mt-2">
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
  const navigate = useNavigate();
  const [isOpen, setIsOpen] = useState(() => {
    if (typeof window !== "undefined") {
      const isMobile = window.innerWidth < 640;
      const manuallyClosed = sessionStorage.getItem("chatbot_closed");
      if (isMobile && !manuallyClosed) {
        return true;
      }
    }
    return false;
  });

  const handleClose = () => {
    sessionStorage.setItem("chatbot_closed", "true");
    setIsOpen(false);
  };

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
      sources: [],
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

  const handleCategoryClick = (query: string) => {
    handleSend(query);
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
        const timeoutId = setTimeout(() => controller.abort(), 30000); // 30s: HF Space cold start
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

        // Extract sources from API response
        const apiSources: LawSource[] = (data.sources || []).map(
          (s: { kanun?: string; madde?: string; ozet?: string }) => ({
            kanun: s.kanun || "Mevzuat",
            madde: s.madde || "",
            ozet: s.ozet || "",
          }),
        );

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
            sources: apiSources,
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
      } catch (error: any) {
        console.error("API hatası:", error);
        // Cold start tespiti: AbortError = timeout (HF Space uykudan uyanıyor)
        const isColdStart =
          error?.name === "AbortError" || error?.message?.includes("aborted");
        const friendlyMessages = isColdStart
          ? [
              "⏳ Sunucu başlatılıyor, lütfen birkaç saniye bekleyin ve tekrar deneyin.",
              "⏳ Sistem şu an uyanıyor. 10-15 saniye sonra tekrar deneyebilirsiniz.",
            ]
          : [
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
          className="w-14 h-14 sm:w-16 sm:h-16 rounded-full shadow-lg flex items-center justify-center transition-all duration-300 hover:scale-105 active:scale-95 group cursor-pointer"
          style={{
            background: "var(--color-paper)",
            border: "1px solid var(--color-rule)",
            color: "var(--color-ink)",
          }}
          aria-label="AI Chatbot"
        >
          {isOpen ? (
            <X className="w-6 h-6" style={{ color: "var(--color-ink)" }} />
          ) : (
            <>
              <Scale className="w-6 h-6 group-hover:scale-110 transition-transform" style={{ color: "var(--color-accent)" }} />
              <span className="absolute -top-1 -right-1 w-3 h-3 rounded-full animate-ping" style={{ background: "var(--color-accent)" }} />
              <span className="absolute -top-1 -right-1 w-3 h-3 rounded-full" style={{ background: "var(--color-accent)" }} />
            </>
          )}
        </button>
      </div>

      {isOpen && (
        <div
          className={cn(
            "fixed z-50 flex flex-col overflow-hidden shadow-2xl animate-fadeIn transition-all duration-300",
            isFullscreen
              ? "inset-0 rounded-none"
              : "inset-0 sm:inset-auto sm:bottom-24 sm:right-6 sm:rounded-2xl",
          )}
          style={{
            background: "var(--color-paper)",
            border: "1px solid var(--color-rule)",
            fontFamily: "var(--font-body)",
            ...(!isFullscreen && isDesktop
              ? {
                  width: `${dimensions.width}px`,
                  height: `${dimensions.height}px`,
                  maxWidth: "90vw",
                  maxHeight: "90vh",
                }
              : {}),
          }}
        >
          {/* Header — Lumen style */}
          <div
            className="p-4 flex items-center justify-between shadow-xs"
            style={{
              background: "var(--color-paper)",
              borderBottom: "1px solid var(--color-rule)",
            }}
          >
            <div className="flex items-center gap-3">
              <div
                className="w-9 h-9 rounded-xl flex items-center justify-center"
                style={{
                  background: "var(--color-paper-2)",
                  border: "1px solid var(--color-rule)",
                }}
              >
                <Scale className="w-4 h-4" style={{ color: "var(--color-accent)" }} />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h2
                    style={{
                      fontFamily: "var(--font-display)",
                      fontWeight: 400,
                      fontSize: "var(--text-lg)",
                      color: "var(--color-ink)",
                      textTransform: "lowercase",
                    }}
                  >
                    lawagent ai
                  </h2>
                  <span
                    className={`w-2 h-2 rounded-full ${
                      connectionStatus === "online"
                        ? "bg-emerald-500 animate-pulse"
                        : "bg-red-500"
                    }`}
                  />
                </div>
                <p
                  style={{
                    fontFamily: "var(--font-label)",
                    fontSize: "9px",
                    letterSpacing: "0.10em",
                    textTransform: "uppercase",
                    color: "var(--color-muted)",
                  }}
                >
                  00 · HUKUKİ YANIT MOTORU
                </p>
              </div>
            </div>

            <div className="flex items-center gap-1.5">
              {!isDesktop && (
                <div className="flex items-center gap-1.5 mr-1">
                  <button
                    onClick={() => {
                      handleClose();
                      navigate("/");
                    }}
                    className="p-2 rounded-lg transition-all"
                    style={{ color: "var(--color-ink)" }}
                    title="Ana Sayfa"
                  >
                    <Home className="w-4 h-4" />
                  </button>
                </div>
              )}
              {activeTypingMessageId !== null && (
                <button
                  onClick={handleStopGeneration}
                  className="px-2.5 py-1.5 rounded-lg transition-all flex items-center gap-1.5"
                  style={{
                    background: "oklch(90% 0.08 25 / 0.3)",
                    border: "1px solid oklch(65% 0.15 25 / 0.4)",
                    color: "oklch(40% 0.15 25)",
                    fontFamily: "var(--font-label)",
                    fontSize: "10px",
                    textTransform: "uppercase",
                  }}
                  title="Yanıtı Durdur"
                >
                  <StopCircle className="w-3.5 h-3.5" />
                  <span>Durdur</span>
                </button>
              )}
              {isDesktop && (
                <button
                  onClick={toggleFullscreen}
                  className="p-2 rounded-lg transition-all"
                  style={{ color: "var(--color-muted)" }}
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
                onClick={handleClose}
                className="p-2 rounded-lg transition-all"
                style={{ color: "var(--color-muted)" }}
                title="Kapat"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Law Category Chips */}
          <div
            className="px-4 py-2.5 flex-shrink-0"
            style={{
              background: "var(--color-paper-2)",
              borderBottom: "1px solid var(--color-rule)",
            }}
          >
            <div
              style={{
                fontFamily: "var(--font-label)",
                fontSize: "9px",
                letterSpacing: "0.10em",
                textTransform: "uppercase",
                color: "var(--color-muted)",
                marginBottom: "6px",
              }}
            >
              HUKUK KATEGORİLERİ
            </div>
            <div className="flex gap-2 flex-wrap">
              {LAW_CATEGORIES.map((cat, idx) => (
                <button
                  key={idx}
                  onClick={() => handleCategoryClick(cat.query)}
                  className="px-3 py-1 rounded-full text-[11px] font-medium transition-all duration-200 cursor-pointer"
                  style={{
                    fontFamily: "var(--font-body)",
                    textTransform: "lowercase",
                    background: "var(--color-paper)",
                    color: "var(--color-ink-2)",
                    border: "1px solid var(--color-rule)",
                  }}
                >
                  {cat.label}
                </button>
              ))}
            </div>
          </div>

          {/* Info banner */}
          <div
            className="px-4 py-2 text-[10px] leading-tight flex items-start gap-2"
            style={{
              background: "var(--color-paper-2)",
              borderBottom: "1px solid var(--color-rule)",
              color: "var(--color-muted)",
              fontFamily: "var(--font-body)",
              textTransform: "lowercase",
            }}
          >
            <Info className="w-3 h-3 flex-shrink-0 mt-0.5" style={{ color: "var(--color-accent)" }} />
            <span>
              <strong>bilgilendirme:</strong> bu ai asistan genel bilgi
              amaçlıdır, kişisel verileriniz saklanmaz.
            </span>
          </div>

          {/* Messages area — blueprint grid background */}
          <div
            ref={scrollRef}
            className="flex-1 overflow-y-auto p-4 space-y-4"
            style={{
              background: `
                linear-gradient(var(--rule-blueprint) 1px, transparent 1px) 0 0 / 32px 32px,
                linear-gradient(90deg, var(--rule-blueprint) 1px, transparent 1px) 0 0 / 32px 32px,
                var(--color-paper)
              `,
            }}
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

          {/* Input area — Lumen style */}
          <div
            className="p-3.5"
            style={{
              background: "var(--color-paper)",
              borderTop: "1px solid var(--color-rule)",
            }}
          >
            <div className="flex items-center gap-2.5">
              <div
                className="flex-1 flex items-center rounded-xl px-3.5 py-2.5 transition-colors"
                style={{
                  background: "var(--color-paper-2)",
                  border: "1px solid var(--color-rule)",
                }}
              >
                <input
                  type="text"
                  placeholder="hukuki sorunuzu yazın..."
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleSend()}
                  className="flex-1 bg-transparent outline-none text-sm placeholder:text-[var(--color-muted)]"
                  style={{
                    fontFamily: "var(--font-body)",
                    color: "var(--color-ink)",
                    textTransform: "lowercase",
                  }}
                  disabled={connectionStatus === "offline"}
                />
              </div>
              <button
                onClick={() => handleSend()}
                disabled={!inputValue.trim() || connectionStatus === "offline"}
                className="w-10 h-10 flex items-center justify-center rounded-full transition-all cursor-pointer disabled:opacity-40"
                style={{
                  background: "var(--color-accent)",
                  color: "var(--color-paper)",
                }}
              >
                <Send className="w-4 h-4" />
              </button>
            </div>
            <p
              className="text-[9px] mt-2 text-center"
              style={{
                fontFamily: "var(--font-label)",
                letterSpacing: "0.08em",
                textTransform: "uppercase",
                color: "var(--color-muted)",
              }}
            >
              LAWAGENT AI · MEVZUAT KAYNAKLI YANIT MOTORU
            </p>
          </div>
        </div>
      )}

      {/* Source Modal */}
      {showSourceModal && selectedSource && (
        <div
          className="fixed inset-0 z-[60] backdrop-blur-xs flex items-center justify-center p-4 animate-fadeIn"
          style={{ background: "oklch(0% 0 0 / 0.4)" }}
          onClick={() => setShowSourceModal(false)}
        >
          <div
            className="rounded-2xl shadow-2xl max-w-lg w-full p-6 animate-scaleIn"
            style={{
              background: "var(--color-paper)",
              border: "1px solid var(--color-rule)",
              fontFamily: "var(--font-body)",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-start justify-between mb-4">
              <div className="flex items-center gap-3">
                <div
                  className="w-10 h-10 rounded-xl flex items-center justify-center"
                  style={{
                    background: "var(--color-paper-2)",
                    border: "1px solid var(--color-rule)",
                  }}
                >
                  <Scale className="w-5 h-5" style={{ color: "var(--color-accent)" }} />
                </div>
                <div>
                  <h3
                    style={{
                      fontFamily: "var(--font-display)",
                      fontWeight: 400,
                      fontSize: "var(--text-xl)",
                      color: "var(--color-ink)",
                      textTransform: "lowercase",
                    }}
                  >
                    {selectedSource.kanun}
                    {selectedSource.madde && ` · madde ${selectedSource.madde}`}
                  </h3>
                  <p
                    style={{
                      fontFamily: "var(--font-label)",
                      fontSize: "9px",
                      letterSpacing: "0.10em",
                      textTransform: "uppercase",
                      color: "var(--color-muted)",
                    }}
                  >
                    HUKUKİ KAYNAK METNİ
                  </p>
                </div>
              </div>
              <button
                onClick={() => setShowSourceModal(false)}
                style={{ color: "var(--color-muted)" }}
                className="hover:opacity-75 transition-opacity cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <div
              className="p-5 rounded-xl border-l-3"
              style={{
                background: "var(--color-paper-2)",
                borderColor: "var(--color-accent)",
              }}
            >
              <p
                className="text-sm leading-relaxed"
                style={{ color: "var(--color-ink)", textTransform: "lowercase" }}
              >
                "{selectedSource.ozet}"
              </p>
            </div>
            <div className="mt-5 flex justify-end">
              <button
                onClick={() => setShowSourceModal(false)}
                className="lumen-btn lumen-btn--primary"
                style={{ padding: "8px 20px" }}
              >
                kapat
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

        /* Source chip styles - poster design */
        .source-chip-btn {
          background: #fef3c7;
          color: #92400e;
          border: 1px solid #fde68a;
        }
        .source-chip-btn:hover {
          background: #fde68a;
          border-color: #C89C5D;
          box-shadow: 0 2px 8px rgba(200, 156, 93, 0.2);
        }

        /* Category chip hover effect */
        .category-chip:hover {
          transform: translateY(-1px);
        }
      `}</style>
    </>
  );
}

export default ChatbotWidget;
