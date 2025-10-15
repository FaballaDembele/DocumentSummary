# summarizer_service.py
import io
import re
import tempfile
from typing import List, Dict, Any, Optional
import os
import pdfplumber
from PIL import Image
import pytesseract
from transformers import pipeline

# Modèle public adapté au français
HF_MODEL = "models/t5-base-fr"

#HF_MODEL = os.path.join(os.getcwd(), "models", "models--plguillou--t5-base-fr-sum-cnndm")

# Charger du pipeline 
_SUMMARIZER = None
def get_summarizer():
    global _SUMMARIZER
    if _SUMMARIZER is None:
        _SUMMARIZER = pipeline("summarization", model=HF_MODEL, tokenizer=HF_MODEL)
    return _SUMMARIZER

# Extraction texte
def extract_text_with_pdfplumber(path_or_file) -> List[Dict[str,Any]]:
    """
    Retourne une liste de dict: [{'page': 1, 'text': '...'}, ...]
    path_or_file peut être un chemin ou un file-like (BytesIO / UploadFile).
    """
    pages = []
    # pdfplumber accepte path OR file-like (si file-like, convert to BytesIO)
    with pdfplumber.open(path_or_file) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            text = page.extract_text()
            if text:
                text = re.sub(r'\s+', ' ', text).strip()
            else:
                text = "" 
            pages.append({"page": i, "text": text, "page_obj": page})
    return pages

def ocr_page_image(page) -> str:
    """
    page : pdfplumber page object
    Renvoie texte OCR de la page (Pytesseract).
    """
    pil = page.to_image(resolution=300).original
    if pil.mode != "RGB":
        pil = pil.convert("RGB")
    text = pytesseract.image_to_string(pil, lang="fra")
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def extract_text_with_ocr_fallback(path_or_file) -> List[Dict[str,Any]]:
    pages = extract_text_with_pdfplumber(path_or_file)
    for p in pages:
        if not p["text"] or len(p["text"]) < 20:
            try:
                p["text"] = ocr_page_image(p["page_obj"])
            except Exception:
                p["text"] = p["text"] or ""
        # remove page_obj to keep sérialisable
        p.pop("page_obj", None)
    return pages

# Détection type doc (courrier / facture)
def detect_doc_type(full_text: str) -> str:
    txt = full_text.lower()
    # mots-clés facture
    factura_keywords = ["facture", "montant", "total ttc", "ht", "numéro facture", "n° facture", "quantité", "prix unitaire"]
    courrier_keywords = ["objet", "monsieur", "madame", "je vous informe", "j’ai l’honneur", "tél :", "réf", "attest","Avis de reunion","Concours","Monsieur", "Madame"]
    score_f = sum(1 for k in factura_keywords if k in txt)
    score_c = sum(1 for k in courrier_keywords if k in txt)
    if score_f > score_c and score_f >= 1:
        return "facture"
    # if neither strong match, return 'unknown' so we can handle generically
    if score_c > 0:
        return "courrier"
    return "unknown"

# Extraction champs simples
def extract_fields_for_courrier(text: str) -> Dict[str, Optional[str]]:
    fields = {"expediteur": None, "destinataire": None, "objet": None, "date": None, "signature": None}
    # Objet
    m = re.search(r"(Objet|OBJECT|Ministere|reunion|Objet\s*[:\-])\s*[:\-]?\s*(.{1,200})", text, re.IGNORECASE)
    if m:
        fields["objet"] = m.group(2).strip()
    # Date (format simple: 13 août 2025)
    m = re.search(r"(\d{1,2}\s*(janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s*\d{4})", text, re.IGNORECASE)
    if m:
        fields["date"] = m.group(0).strip()
    # Destinataire (séquences après 'Monsieur' ou 'À l’attention de')
    m = re.search(r"(À l’attention de|A l’attention de|Monsieur|Madame)\s*[:\-\s]*([A-ZÉÀÂÈÊÎÔÛÇ0-9\-\s,.]{2,120})", text, re.IGNORECASE)
    if m:
        fields["destinataire"] = m.group(2).strip()
    # Expéditeur simple: recherche d'en-tête ou MINISTERE etc.
    if "ministere" in text.lower() or "république" in text.lower():
        m = re.search(r"^(.*?MINIST[EÈ]RE.*?$)", text, re.IGNORECASE | re.MULTILINE)
        if m:
            fields["expediteur"] = m.group(1).strip()
    # Signature (prénom nom en fin de document)
    m = re.search(r"(Le Directeur|Directeur Général|Signé|Cordialement|Signature|Fait à)\s*[,]?\s*(.*)$", text, re.IGNORECASE | re.DOTALL)
    if m:
        candidate = m.group(2).strip()
        # keep short snippet
        fields["signature"] = candidate.split("\n")[0][:120].strip()
    return fields

def extract_fields_for_facture(text: str) -> Dict[str, Optional[str]]:
    fields = {"numero_facture": None, "date": None, "total_ttc": None, "client": None}
    # Numéro facture
    m = re.search(r"(Facture n[°º]?|N° facture|Numéro facture|Référence)\s*[:\-\s]*([A-Z0-9\/\-]+)", text, re.IGNORECASE)
    if m:
        fields["numero_facture"] = m.group(2).strip()
    # Date simple
    m = re.search(r"(Date)\s*[:\-\s]*(\d{1,2}[\/\-\.\s]\d{1,2}[\/\-\.\s]\d{2,4}|\d{1,2}\s*(janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s*\d{4})", text, re.IGNORECASE)
    if m:
        fields["date"] = m.group(2).strip()
    # Total TTC
    m = re.search(r"(Total TTC|TOTAL TTC|Total à payer|Montant TTC|Total)\s*[:\-\s]*([0-9\.,\s]+)€?", text, re.IGNORECASE)
    if m:
        fields["total_ttc"] = m.group(2).strip()
    # Client / destinataire
    m = re.search(r"(Client|Facturé à|À l’attention de|Bill To)\s*[:\-\s]*(.{2,120})", text, re.IGNORECASE)
    if m:
        fields["client"] = m.group(2).strip()
    return fields

def extract_generic_fields(text: str) -> Dict[str, Optional[str]]:
    """Tentative d'extraction générique de métadonnées: date, titre/objet, auteurs, emails, numéros."""
    fields = {"titre": None, "date": None, "emails": None, "telephones": None, "auteur": None}
    # Date (ISO-ish or french spelled)
    m = re.search(r"(\d{4}-\d{2}-\d{2}|\d{1,2}\s*(janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s*\d{4}|\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})", text, re.IGNORECASE)
    if m:
        fields["date"] = m.group(0).strip()
    # Title / premier en-tête: prendre la première ligne non vide
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if lines:
        fields["titre"] = lines[0][:200]
    # emails
    emails = re.findall(r"[\w\.-]+@[\w\.-]+", text)
    if emails:
        fields["emails"] = ", ".join(sorted(set(emails)))
    # phones (simple patterns)
    telephones = re.findall(r"\+?\d[\d\s\-]{6,}\d", text)
    if telephones:
        fields["telephones"] = ", ".join(sorted(set(telephones)))
    # authors: look for 'par' or 'auteur'
    m = re.search(r"(?:par|auteur[s]?|rédigé par)\s*[:\-]?\s*([A-ZÉÀÂÈÊÎÔÛÇ][\w\s,.-]{1,120})", text, re.IGNORECASE)
    if m:
        fields["auteurs"] = m.group(1).strip()
    return fields

# Résumé
def summarize_text(text: str, max_length: int = 180, min_length: int = 40, language: str = "fr", structured: bool = False) -> str:
    """Résumé du texte.

    Params:
      - text: texte à résumer
      - language: code langue (ex: 'fr') — utilisé pour construire la consigne
      - structured: si True, demander des « points clés » plutôt qu'un paragraphe
    """
    summarizer = get_summarizer()
    # découpage si trop long
    text = text.strip()
    if len(text) == 0:
        return ""
    chunks = [text[i:i+2000] for i in range(0, len(text), 2000)]
    parts = []
    for c in chunks:
        # construire une consigne pour orienter la langue et le format
        if structured:
            prompt = f"Résumez en {language} et fournissez 5 points clés concis:\n\n" + c
        else:
            prompt = f"Résumez en {language} de manière concise:\n\n" + c
        out = summarizer(prompt, max_length=max_length, min_length=min_length, do_sample=False)
        if isinstance(out, list):
            parts.append(out[0]["summary_text"])
        else:
            parts.append(str(out))
    # fusionner et nettoyer
    final = " ".join(parts)
    final = re.sub(r'\s+', ' ', final).strip()
    return final

# Pipeline complet
def analyze_pdf(path_or_file, language: str = "fr", structured: bool = False) -> Dict[str,Any]:
    """
    Entrée : path ou file-like (UploadFile)
    Retour : dict avec:
      - pages: [{page, text_snippet}]
      - full_text
      - doc_type
      - fields
      - summary
    """
    pages = extract_text_with_ocr_fallback(path_or_file)
    full_text = " ".join([p["text"] for p in pages if p["text"]])
    doc_type = detect_doc_type(full_text)
    # champs
    if doc_type == "facture":
        fields = extract_fields_for_facture(full_text)
    elif doc_type == "courrier":
        fields = extract_fields_for_courrier(full_text)
    else:
        fields = extract_generic_fields(full_text)
    # résumé global
    instr = "Résumez le texte suivant en français de manière concise et claire :\n\n"
    summary = summarize_text(instr + full_text, max_length=130, min_length=50, language=language, structured=structured)
    # résumé par page (court)
    page_summaries = []
    for p in pages:
        txt = p["text"][:1800]
        if len(txt.strip()) < 20:
            page_summary = ""
        else:
            page_summary = summarize_text(f"Résumez en {language} :\n\n" + txt, max_length=180, min_length=30, language=language, structured=False)
        page_summaries.append({"page": p["page"], "summary": page_summary})
    return {
        "pages": [{"page": p["page"], "text_snippet": p["text"][:400]} for p in pages],
        #"full_text": full_text[:5000],   # limit pour API response (échantillon)
        "doc_type": doc_type,
        #"fields": fields,
        "summary": summary,
        # "page_summaries": page_summaries
    }
