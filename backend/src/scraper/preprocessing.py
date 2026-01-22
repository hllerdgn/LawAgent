import re


def preprocess_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"(T\.C\. Kimlik No|TC Kimlik No)\s*[:\-]?\s*\d+", "[ANONIM]", text)
    text = re.sub(r"\b\d{11}\b", "[ANONIM]", text)
    text = re.sub(
        r"\b[A-ZÇĞİÖŞÜ][a-zçğıöşü]+\s[A-ZÇĞİÖŞÜ][a-zçğıöşü]+\b", "[KISI]", text
    )
    return text.strip()


import re


def anonymize_text(text: str) -> str:

    text = re.sub(r"\b\d{11}\b", "[TC_KIMLIK_NO]", text)
    text = re.sub(r"\b0?5\d{9}\b", "[TELEFON]", text)
    text = re.sub(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", "[EMAIL]", text)
    text = re.sub(
        r"(DAVACI|DAVALI|SANIK|MÜŞTEKİ)\s*[:\-]?\s*[A-ZÇĞİÖŞÜ][A-Za-zÇĞİÖŞÜçğıöşü\s]+",
        r"\1: [KISI]",
        text,
    )
    return text
