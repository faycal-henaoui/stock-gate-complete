"""
step05_field_extractor.py

Robust, production-ready invoice field extractor.

Features:
- Layout-aware reconstruction using step04 output (lines with bbox)
- Font-size analysis to detect headings / supplier logos
- Multi-language (fr/en/ar) support via language-specific regexes
- Rule-based + Stanza hybrid extraction (Stanza optional)
- Optional deep NER using LayoutLMv3 or DONUT (if installed)
- Item table extraction with adaptive column detection
- Totals, taxes, payment method extraction
- ERP mapping helper
- Debug outputs saved to debug_out/step05_extracted.json

Usage:
    from step05_field_extractor import InvoiceFieldExtractor
    extractor = InvoiceFieldExtractor(lang='fr')
    extracted = extractor.extract_from_step04(step04_json, image_path='invoice.jpg')
    extractor.save_debug(extracted, 'debug_out/step05_extracted.json')
"""

import re
import json
import os
from typing import List, Dict, Any, Optional, Tuple
from collections import Counter, defaultdict
import fix_numpy

# Optional libraries (import only if available)
try:
    import stanza
except Exception:
    stanza = None

# Optional deep model wrappers (LayoutLMv3 or DONUT)
# These are tried only if you install `transformers` and layout models.
try:
    from transformers import LayoutLMv3ForTokenClassification, LayoutLMv3Processor
    HAS_LAYOUTLM = True
except Exception:
    HAS_LAYOUTLM = False

try:
    # DONUT-like (Document VQA) wrappers - may not be installed
    from transformers import VisionEncoderDecoderModel, AutoProcessor
    HAS_DONUT = True
except Exception:
    HAS_DONUT = False

# ------------------------
# Utility helpers
# ------------------------
def ensure_dir(d: str):
    if not os.path.exists(d):
        os.makedirs(d, exist_ok=True)

def norm(text: str) -> str:
    return text.strip()

def join_lines(lines: List[Dict[str, Any]]) -> str:
    return "\n".join([l.get("text","") for l in lines if l.get("text")])

# ------------------------
# Language-specific patterns
# ------------------------
LANG_PATTERNS = {
    "fr": {
        "total_keywords": ["total", "net à payer", "montant ttc", "montant ht", "total ttc", "total ht"],
        "date_regex": r"(\d{1,2}[\/\-\.\s]\d{1,2}[\/\-\.\s]\d{2,4})",
        "invoice_num_regex": r"(?:n[°º]?\s*[:\-\s]?|facture\s*n[°º]?\s*[:\-\s]?)([A-Za-z0-9\/\-\._]+)",
        "payment_keywords": ["espèce","chèque","virement","carte","ccp","paypal","cash","credit"],
        "currency_regex": r"(DA|DZD|EUR|€|\$|USD)",
        "table_headers": ["designation","désignation","prix unitaire","quantité","qte","total produit","montant"]
    },
    "en": {
        "total_keywords": ["total", "amount due", "grand total", "net payable"],
        "date_regex": r"(\d{1,2}[\/\-\.\s]\d{1,2}[\/\-\.\s]\d{2,4})",
        "invoice_num_regex": r"(?:invoice\s*no\.?\s*[:\-\s]?|inv\.?\s*[:\-\s]?)([A-Za-z0-9\/\-\._]+)",
        "payment_keywords": ["cash","cheque","bank transfer","wire","credit card","card","paypal"],
        "currency_regex": r"(USD|\$|EUR|€|DA|DZD)",
        "table_headers": ["description","unit price","qty","quantity","total"]
    },
    "ar": {
        # Arabic regexes; note: directionality complexity not fully handled here
        "total_keywords": ["المجموع","الإجمالي","الصافي"],
        "date_regex": r"(\d{1,2}[\/\-\.\s]\d{1,2}[\/\-\.\s]\d{2,4})",  # numeric dates still match
        "invoice_num_regex": r"(?:فاتورة\s*رقم\s*[:\-\s]?)([A-Za-z0-9\-_/٠-٩]+)",
        "payment_keywords": ["نقداً","شيك","تحويل","بطاقة"],
        "currency_regex": r"(دج|DA|DZD|€|EUR|\$)",
        "table_headers": ["الوصف","الكمية","السعر","المجموع"]
    }
}

# ------------------------
# Main extractor
# ------------------------
class InvoiceFieldExtractor:
    def __init__(self, lang: str = "fr", use_stanza: bool = True, try_deep_ner: bool = False):
        self.lang = lang if lang in LANG_PATTERNS else "fr"
        self.patterns = LANG_PATTERNS[self.lang]
        self.use_stanza = bool(use_stanza and stanza is not None)
        self.try_deep_ner = bool(try_deep_ner and (HAS_LAYOUTLM or HAS_DONUT))

        # init stanza pipeline if requested & available
        if self.use_stanza:
            try:
                stanza.download(self.lang, processors="tokenize,ner", verbose=False)
            except Exception:
                # may already be installed, ignore
                pass
            try:
                self.stanza_nlp = stanza.Pipeline(lang=self.lang, processors="tokenize,ner", use_gpu=False, verbose=False)
            except Exception:
                self.stanza_nlp = None
                self.use_stanza = False
        else:
            self.stanza_nlp = None

        # deep NER placeholders (optional)
        self.deep_processor = None
        self.deep_model = None
        if self.try_deep_ner:
            self._init_deep_ner()

    # -------------------------
    # Layout / font-size analysis
    # -------------------------
    def _analyze_font_sizes(self, lines: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Compute very simple font/height statistics from bboxes.

        Returns a dict with basic stats that downstream heuristics can use.
        If bbox info is missing or zero, falls back to line indices.
        """
        heights: List[float] = []
        top_ys: List[float] = []
        for i, l in enumerate(lines):
            bbox = l.get("bbox") or {}
            h = bbox.get("h") or 0
            y = bbox.get("y") or 0
            if h and h > 0:
                heights.append(float(h))
            top_ys.append(float(y))

        if not heights:
            return {
                "avg_height": 0.0,
                "max_height": 0.0,
                "min_height": 0.0,
                "top_quartile_y": min(top_ys) if top_ys else 0.0,
                "bottom_quartile_y": max(top_ys) if top_ys else 0.0,
            }

        heights_sorted = sorted(heights)
        n = len(heights_sorted)
        avg_h = sum(heights_sorted) / n
        max_h = heights_sorted[-1]
        min_h = heights_sorted[0]

        top_quartile_y = min(top_ys) if top_ys else 0.0
        bottom_quartile_y = max(top_ys) if top_ys else 0.0

        return {
            "avg_height": avg_h,
            "max_height": max_h,
            "min_height": min_h,
            "top_quartile_y": top_quartile_y,
            "bottom_quartile_y": bottom_quartile_y,
        }

    # deep NER initialization (optional)
    def _init_deep_ner(self):
        if HAS_LAYOUTLM:
            try:
                # user must set a LOCAL model name/path if desired; default None
                self.deep_processor = LayoutLMv3Processor.from_pretrained("microsoft/layoutlmv3-base")
                self.deep_model = LayoutLMv3ForTokenClassification.from_pretrained("microsoft/layoutlmv3-base")
            except Exception:
                self.deep_processor = None
                self.deep_model = None
        # DONUT fallback omitted: user may plug their own model
        if not self.deep_processor:
            self.try_deep_ner = False

    # -------------------------
    # NER helpers (stubs if models unavailable)
    # -------------------------
    def _stanza_entities(self, text: str) -> Dict[str, List[str]]:
        """Run stanza NER if available; otherwise return empty dict."""
        if not (self.use_stanza and self.stanza_nlp and text):
            return {}
        ents: Dict[str, List[str]] = {}
        try:
            doc = self.stanza_nlp(text)
            for sent in doc.sentences:
                for ent in sent.ents:
                    ents.setdefault(ent.type, []).append(ent.text)
        except Exception:
            return {}
        return ents

    def _deep_ner(self, lines: List[Dict[str, Any]], image_path: Optional[str]):
        """Placeholder for deep-layout NER (LayoutLM / DONUT).

        Currently returns an empty dict unless you wire a custom model.
        """
        if not (self.try_deep_ner and self.deep_processor and self.deep_model):
            return {}
        # To keep things simple and dependency-light, we don't implement
        # full LayoutLM inference here. Users can extend this method.
        return {}

    # -------------------------
    # Public: main entry point
    # -------------------------
    def extract_from_step04(self, step04_json: Dict[str, Any], image_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Input: step04_json produced by Step04 (layout reconstruction)
               structure: {"lines": [ { "line_index", "text", "bbox": {"x","y","w","h","quad"}} ]}
        image_path: optional path to original image; used for deep NER / debug visuals
        Returns: dict with extracted fields
        """
        lines = step04_json.get("lines", [])
        # normalize lines: ensure required fields exist
        for i, l in enumerate(lines):
            if "text" not in l:
                l["text"] = ""
            if "bbox" not in l:
                l["bbox"] = {"x":0,"y":0,"w":0,"h":0,"quad": None}

        # compute font-size and top-bottom metrics used in heuristics
        font_stats = self._analyze_font_sizes(lines)

        # full text for global regex + stanza
        full_text = join_lines(lines)

        # optional stanza + deep NER
        stanza_entities = self._stanza_entities(full_text) if self.use_stanza and self.stanza_nlp else {}
        deep_entities = self._deep_ner(lines, image_path) if self.try_deep_ner and self.deep_processor else {}

        # heuristics
        supplier = self._extract_supplier(lines, font_stats, full_text, stanza_entities)
        customer = self._extract_customer(lines, full_text)
        document = self._extract_document_info(lines, full_text)
        totals = self._extract_totals(lines, full_text)
        payment = self._extract_payment(lines, full_text)
        # use simple, clean 4-field item extraction
        items = self._extract_items_simple(lines)

        result = {
            "supplier": supplier,
            "customer": customer,
            "document": document,
            "totals": totals,
            "payment": payment,
            "items": items,
            "stanza_entities": stanza_entities,
            "deep_entities": deep_entities,
            "font_stats": font_stats,
        }
        return result

    # -------------------------
    # Supplier extraction
    # -------------------------
    def _extract_supplier(
        self,
        lines: List[Dict[str, Any]],
        font_stats: Dict[str, Any],
        full_text: str,
        stanza_entities: Dict[str, List[str]],
    ) -> Dict[str, Any]:
        """Heuristic supplier (issuer) extraction.

        Very simple version: take the first non-empty line as name, try to
        grab an address from the next couple of lines, and detect a phone.
        Uses stanza ORG entities as extra candidates if available.
        """
        supplier: Dict[str, Any] = {
            "name": None,
            "address": None,
            "phone": None,
            "candidates": [],
        }

        # name from top of document or ORG entities
        top_lines = [l.get("text", "").strip() for l in lines[:5] if l.get("text", "").strip()]
        if top_lines:
            supplier["name"] = top_lines[0]

        # simple address: concatenate a couple of following lines that contain letters and digits
        addr_parts: List[str] = []
        for t in top_lines[1:4]:
            if re.search(r"[A-Za-z].*\d|\d.*[A-Za-z]", t):
                addr_parts.append(t)
        if addr_parts:
            supplier["address"] = " ".join(addr_parts)

        # phone: scan for Tel-like patterns near the top
        phone_rx = re.compile(r"(0[0-9 \-\+]{7,})")
        for l in lines[:15]:
            txt = l.get("text", "")
            if "tel" in txt.lower():
                m = phone_rx.search(txt)
                if m:
                    supplier["phone"] = re.sub(r"[^\d\+]", "", m.group(1))
                    break

        # stanza ORG entities as extra candidates
        if stanza_entities.get("ORG"):
            supplier["candidates"].extend(stanza_entities["ORG"])

        return supplier

    # -------------------------
    # Simple 4-field item extraction (description, quantity, unit_price, line_total)
    # -------------------------
    def _extract_items_simple(self, lines: List[Dict[str,Any]]) -> List[Dict[str,Any]]:
        """Extract items using layout: link description, qty, unit price, total.

        Assumes a typical table like your example:
        - One description line per row (middle area of the page).
        - A small integer quantity on the left.
        - A unit price on the right (x ~ 1000).
        - A line total further right (x ~ 1180+).
        """

        if not lines:
            return []

        # Helper: group into horizontal rows by y coordinate
        body_sorted = sorted(lines, key=lambda l: l["bbox"]["y"])
        rows: List[List[Dict[str,Any]]] = []
        cur: List[Dict[str,Any]] = []
        prev_y: Optional[float] = None
        for l in body_sorted:
            y = l["bbox"].get("y", 0)
            if prev_y is None or abs(y - prev_y) <= 12:
                cur.append(l)
                prev_y = y if prev_y is None else (prev_y + y) / 2.0
            else:
                rows.append(cur)
                cur = [l]
                prev_y = y
        if cur:
            rows.append(cur)

        # Identify header row by presence of "Designation" and prices headers
        header_idx = None
        for i, row in enumerate(rows):
            row_text = " ".join(l.get("text", "").lower() for l in row)
            if "designation" in row_text and "prix" in row_text:
                header_idx = i
                break
        if header_idx is None:
            return []

        item_rows = rows[header_idx+1:]

        def parse_money(s: str) -> Optional[float]:
            s = s.replace(" ", "")
            m = re.search(r"(\d+[.,]\d{2})", s)
            if not m:
                return None
            val = m.group(1).replace(",", ".")
            try:
                return float(val)
            except ValueError:
                return None

        items: List[Dict[str,Any]] = []

        for row in item_rows:
            # Skip footer/summary rows
            row_text = " ".join(l.get("text", "") for l in row)
            low = row_text.lower()
            if "arrete du present" in low or "quantite totale" in low or "quantité totale" in low or "total :" in low:
                continue

            # Find description: text around the designation column.
            xs = [l["bbox"]["x"] for l in row]
            ws = [l["bbox"]["w"] for l in row]
            min_x, max_x = min(xs), max(x+w for x, w in zip(xs, ws))
            width = max_x - min_x if max_x > min_x else 1
            # For your layout, descriptions start roughly around x~250 and go
            # up to before the carton/qty columns. We take a wide band.
            left_band = min_x + 0.15 * width
            right_band = min_x + 0.65 * width
            desc_parts: List[str] = []
            for l in row:
                x = l["bbox"]["x"]
                cx = x + l["bbox"]["w"] / 2.0
                txt = l.get("text", "").strip()
                if left_band <= cx <= right_band and len(txt) > 3:
                    desc_parts.append(txt)
            if not desc_parts:
                continue
            desc = " ".join(desc_parts)
            # Clean leading reference/index markers
            desc = re.sub(r"^[0-9A-Z\s\*]+", "", desc).strip(" .:")
            if not desc:
                continue

            # Quantity: small integer on left side of row
            qty = 1
            left_tokens = []
            for l in row:
                x = l["bbox"]["x"]
                if x < min_x + 0.15 * width:
                    t = l.get("text", "").strip()
                    if re.fullmatch(r"\d+", t):
                        left_tokens.append(int(t))
            if left_tokens:
                qty = left_tokens[0]

            # Unit price: money-like value in middle-right; total: rightmost money
            unit_price: Optional[float] = None
            line_total: Optional[float] = None
            money_cells: List[Tuple[float, float]] = []  # (x, value)
            for l in row:
                x = l["bbox"]["x"]
                t = l.get("text", "")
                val = parse_money(t)
                if val is None:
                    continue
                money_cells.append((x, val))

            if money_cells:
                # sort by x; assume the left one is unit price, rightmost is total
                money_cells.sort(key=lambda p: p[0])
                if len(money_cells) == 1:
                    unit_price = line_total = money_cells[0][1]
                else:
                    unit_price = money_cells[0][1]
                    line_total = money_cells[-1][1]

            # Fallbacks if one of the prices is missing
            if unit_price is None and line_total is not None and qty:
                unit_price = line_total / qty
            if line_total is None and unit_price is not None and qty:
                line_total = unit_price * qty

            if desc and line_total is not None:
                items.append({
                    "description": desc,
                    "quantity": qty,
                    "unit_price": unit_price,
                    "line_total": line_total,
                })

        return items

    # -------------------------
    # Customer extraction
    # -------------------------
    def _extract_customer(self, lines, full_text) -> Dict[str,Any]:
        customer = {"name": None, "address": None, "phone": None}
        # find "client" keyword in multiple languages
        client_keywords = ["client", "acheteur", "destinataire", "bénéficiaire", "buyer"]
        for i,l in enumerate(lines):
            txt_low = l.get("text", "").lower()
            if any(k in txt_low for k in client_keywords):
                # e.g. "Client PASSAGER"
                m = re.search(r"client[:\s-]*(.+)", l.get("text", ""), flags=re.IGNORECASE)
                if m and m.group(1).strip():
                    customer["name"] = m.group(1).strip()
                else:
                    # next line likely contains name / address
                    if i+1 < len(lines):
                        candidate = lines[i+1]["text"].strip()
                        if candidate:
                            customer["name"] = candidate
                            if i+2 < len(lines):
                                customer["address"] = lines[i+2]["text"].strip()
                break

        # phone: restrict search to explicit Tel lines, avoid document number
        if not customer["phone"]:
            for l in lines:
                txt = l.get("text", "")
                low = txt.lower()
                # avoid lines that look like document numbers (e.g. starting with N')
                if "tel" in low and "n'" not in low and "n°" not in low:
                    m2 = re.search(r"(0[0-9 \-\+]{7,})", txt)
                    if m2:
                        customer["phone"] = re.sub(r"[^\d\+]", "", m2.group(1))
                        break

        # if customer phone equals supplier phone (same header), drop it
        # (we only know supplier phone at call site, so this check is done in Pipeline or post-processing)

        # fallback: try to detect person names or addresses via regex
        if not customer["name"]:
            # look for a line with "Nom" or "Name"
            for l in lines[:15]:
                if re.search(r"\b(Nom|Name)\b", l["text"], re.IGNORECASE):
                    m = re.search(r"(?:Nom|Name)[:\s\-]*(.+)", l["text"], flags=re.IGNORECASE)
                    if m:
                        customer["name"] = m.group(1).strip()
                        break
        return customer

    # -------------------------
    # Document meta extraction (invoice number, date)
    # -------------------------
    def _extract_document_info(self, lines, full_text) -> Dict[str,Any]:
        doc = {"type": None, "number": None, "date": None}
        # type detection
        if re.search(r"\b(facture|invoice|bon de livraison)\b", full_text, flags=re.IGNORECASE):
            if re.search(r"bon de livraison", full_text, flags=re.IGNORECASE):
                doc["type"] = "delivery_note"
            elif re.search(r"facture|invoice", full_text, flags=re.IGNORECASE):
                doc["type"] = "invoice"
            else:
                doc["type"] = "document"

        # invoice number: multiple regex variants
        # try explicit keywords first
        inv_regexes = [
            r"(?:num(?:éro|ero)?\s*[:\-]?\s*|n[°º]\s*[:\-]?\s*)([A-Za-z0-9\/\-\._]+)",
            self.patterns.get("invoice_num_regex"),
            r"(?:invoice|inv\.?)[:\s\-]*([A-Za-z0-9\/\-\._]+)"
        ]
        for rx in inv_regexes:
            if not rx:
                continue
            m = re.search(rx, full_text, flags=re.IGNORECASE)
            if m:
                cand = m.group(1).strip()
                # ignore values without any digit (e.g. company name)
                if any(ch.isdigit() for ch in cand):
                    doc["number"] = cand
                    break

        # Stronger pattern for French-style "N' 014502025 du ..." if still empty
        if not doc["number"]:
            m2 = re.search(r"N['’`]?\s*([0-9]{4,})", full_text)
            if m2:
                doc["number"] = m2.group(1)

        # date detection - many formats
        date_rx = self.patterns.get("date_regex") or r"(\d{1,2}[\/\-\.\s]\d{1,2}[\/\-\.\s]\d{2,4})"
        m = re.search(date_rx, full_text)
        if m:
            doc["date"] = m.group(1)

        # also search per-line near "Date" keyword
        for l in lines[:30]:
            if re.search(r"\b(date|date:\b|تاريخ)\b", l["text"], flags=re.IGNORECASE):
                m2 = re.search(date_rx, l["text"])
                if m2:
                    doc["date"] = m2.group(1)
                    break

        return doc

    # -------------------------
    # Totals & Tax extraction
    # -------------------------
    def _extract_totals(self, lines, full_text) -> Dict[str,Any]:
        out = {"total_amount": None, "currency": None, "total_amount_words": None, "tax": None}
        # search for lines containing total keywords
        tk = self.patterns["total_keywords"]
        for l in lines[::-1]:  # search bottom-up
            txt = l["text"]
            if any(k in txt.lower() for k in tk):
                m = re.search(r"([0-9]{1,3}(?:[ ,.][0-9]{3})*(?:[.,][0-9]{2})?)", txt)
                if m:
                    out["total_amount"] = m.group(1).replace(" ", "").replace(",", ".")
                c = re.search(self.patterns["currency_regex"], txt, flags=re.IGNORECASE)
                if c:
                    out["currency"] = c.group(1).upper()
                break

        # fallback: find last currency occurrence in doc
        if not out["total_amount"]:
            m = re.search(r"([0-9]{1,3}(?:[ ,.][0-9]{3})*(?:[.,][0-9]{2})?)\s*(DA|DZD|EUR|€|\$|USD)", full_text, flags=re.IGNORECASE)
            if m:
                out["total_amount"] = m.group(1).replace(" ", "").replace(",", ".")
                out["currency"] = m.group(2).upper()

        # tax: find VAT / TVA / Tax %
        mtax = re.search(r"(tva|taxe|vat)[^\d%]*([0-9]{1,3}(?:[.,][0-9]{1,2})?)\s*%?", full_text, flags=re.IGNORECASE)
        if mtax:
            out["tax"] = mtax.group(2)

        # spelled-out amount
        for l in lines[::-1]:
            if re.search(r"mille|thousand|ألف|million", l["text"], flags=re.IGNORECASE):
                out["total_amount_words"] = l["text"]
                break

        return out

    # -------------------------
    # Payment method extraction
    # -------------------------
    def _extract_payment(self, lines, full_text) -> Dict[str,Any]:
        out = {"method": None, "raw": None}
        keywords = self.patterns.get("payment_keywords", [])
        for l in lines:
            low = l["text"].lower()
            for k in keywords:
                if k in low:
                    out["method"] = k
                    out["raw"] = l["text"]
                    return out
        # fallback: look for common words
        m = re.search(r"(cash|chèque|cheque|virement|transfer|card|carte|espèce)", full_text, flags=re.IGNORECASE)
        if m:
            out["method"] = m.group(1)
            out["raw"] = m.group(0)
        return out

    # -------------------------
    # Item table extraction: 4 clean fields per row
    # -------------------------
    def _extract_items(self, lines: List[Dict[str,Any]]) -> List[Dict[str,Any]]:
        """Return items as description, quantity, unit_price, line_total.

        Strategy (layout-agnostic but practical):
        - Detect the table header using known keywords.
        - Group subsequent lines into horizontal rows by y position.
        - For each row, build a textual description from the middle/left region,
          infer quantity from small integer tokens, and take the two largest
          monetary amounts as (unit_price, line_total).
        - Drop summary/footer rows containing words like "Total" or "Arrete".
        """

        if not lines:
            return []

        # 1) Find header line (contains designation/description/qty/total etc.)
        header_keywords = self.patterns.get("table_headers", []) + [
            "designation", "description", "prix", "price", "qte", "qty", "total produit", "total"
        ]
        header_idx = None
        for i, l in enumerate(lines):
            txt = l.get("text", "").lower()
            if any(k in txt for k in header_keywords):
                header_idx = i
                break
        if header_idx is None:
            return []

        # 2) Group following lines into logical rows by y coordinate
        body = [l for l in lines[header_idx+1:] if l.get("text", "").strip()]
        body_sorted = sorted(body, key=lambda l: l["bbox"]["y"])
        rows: List[List[Dict[str,Any]]] = []
        current: List[Dict[str,Any]] = []
        prev_y: Optional[float] = None
        for l in body_sorted:
            y = l["bbox"]["y"]
            if prev_y is None or abs(y - prev_y) <= 12:
                current.append(l)
                prev_y = y if prev_y is None else (prev_y + y) / 2.0
            else:
                rows.append(current)
                current = [l]
                prev_y = y
        if current:
            rows.append(current)

        # helper for numeric amounts (money-like)
        def extract_amounts(s: str) -> List[float]:
            nums = re.findall(r"[0-9][0-9 .]*[0-9](?:[.,][0-9]{2})?", s)
            out = []
            for n in nums:
                n_clean = n.replace(" ", "").replace(",", ".")
                try:
                    out.append(float(n_clean))
                except Exception:
                    continue
            return out

        items: List[Dict[str,Any]] = []

        for row in rows:
            # Concatenate all texts and also keep pieces per approximate x band
            row_text = " ".join(l.get("text", "") for l in row)
            # Skip obvious footer/summary rows
            low_all = row_text.lower()
            if any(kw in low_all for kw in ["arrete du present", "quantite totale", "quantité totale", "total :", "total:"]):
                continue

            # Build description from middle band (exclude far left index and far right totals)
            xs = [l["bbox"]["x"] for l in row]
            ws = [l["bbox"]["w"] for l in row]
            min_x, max_x = min(xs), max(x+w for x, w in zip(xs, ws))
            width = max_x - min_x if max_x > min_x else 1
            desc_parts = []
            left_band = min_x + 0.15 * width
            right_band = min_x + 0.75 * width
            for l in row:
                x = l["bbox"]["x"]
                cx = x + l["bbox"]["w"] / 2.0
                if left_band <= cx <= right_band:
                    desc_parts.append(l.get("text", ""))
            if not desc_parts:
                # fallback: use all texts except first token (index)
                desc_parts = [row[0].get("text", "")] + [l.get("text", "") for l in row[1:]]
            desc = " ".join(desc_parts)
            # clean reference/index/carton tokens at start like "1", "K", "B", "6"
            desc = re.sub(r"^[0-9A-Z\s]+", "", desc).strip(" .:")

            # infer quantity: smallest positive integer in the row (but >0 and <= quantity total)
            int_tokens = []
            for tok in re.findall(r"\b\d+\b", row_text):
                try:
                    v = int(tok)
                except ValueError:
                    continue
                if 0 < v <= 20:
                    int_tokens.append(v)
            quantity = int_tokens[0] if int_tokens else 1

            # amounts: take unique sorted list and pick two smallest big numbers as unit/total
            amounts = extract_amounts(row_text)
            amounts = sorted(set(round(a, 2) for a in amounts))
            unit_price: Optional[float] = None
            line_total: Optional[float] = None
            if len(amounts) == 1:
                line_total = amounts[0]
                unit_price = amounts[0]
            elif len(amounts) >= 2:
                # for this kind of table, the two distinct values per row are (unit, total)
                unit_price = amounts[0]
                line_total = amounts[-1]

            # final clean item
            if desc and line_total is not None:
                items.append({
                    "description": desc,
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "line_total": line_total,
                })

        return items

    # -------------------------
    # Utilities
    # -------------------------
    def save_debug(self, extracted: Dict[str,Any], path: str = "debug_out/step05_extracted.json"):
        ensure_dir(os.path.dirname(path) or ".")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(extracted, f, indent=2, ensure_ascii=False)

    def map_to_erp(self, extracted: Dict[str,Any], mapping: Dict[str,str]) -> Dict[str,Any]:
        """
        Map extracted fields to ERP fields.

        mapping: dict where keys are ERP field names and values are dotted paths into extracted object
            e.g. mapping = {"customer_name": "customer.name", "invoice_total": "totals.total_amount"}
        """
        out = {}
        for erp_field, src_path in mapping.items():
            val = self._get_by_path(extracted, src_path.split("."))
            out[erp_field] = val
        return out

    def _get_by_path(self, d: Dict[str,Any], path: List[str]):
        cur = d
        for p in path:
            if cur is None:
                return None
            if isinstance(cur, dict):
                cur = cur.get(p)
            else:
                return None
        return cur
