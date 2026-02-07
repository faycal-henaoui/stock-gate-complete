"""
step05_field_extractor_prod.py
Production-grade invoice extractor (semantic + layout hybrid).

MAIN GOALS:
- Extremely stable item extraction
- Header-independent layout detection
- Multi-line descriptions
- Robust money parsing
- Clear supplier/customer/document/totals

This extractor does NOT rely purely on bounding boxes.
It uses semantic cues + regex + numeric patterns + layout fallback.
"""

import re
import json
import unidecode
from typing import Dict, List, Any, Optional


# ============================================================
# Utility Helpers
# ============================================================

def normalize(txt: str) -> str:
    """Lowercase, strip, and remove accents."""
    if not txt:
        return ""
    return unidecode.unidecode(txt.lower().strip())


def parse_money(txt: str) -> Optional[float]:
    """Parse any money-like value: 25000,00 | 25 000.00 | 25.000,00 | 25000."""
    if not txt:
        return None

    t = txt.replace(" ", "").replace("\u202f", "")
    t = t.replace(",", ".")  # unify decimal separator

    # Remove thousands separators like "27.500.00" -> "27500.00"
    if t.count(".") > 1:
        parts = t.split(".")
        # last part = decimals, previous = thousand groups
        if len(parts[-1]) == 2:  # decimals present
            t = "".join(parts[:-1]) + "." + parts[-1]

    # Must be numeric
    try:
        return float(t)
    except Exception:
        return None


def is_money_like(txt: str) -> bool:
    """Check if text looks like a price/total."""
    return parse_money(txt) is not None


def looks_like_qty(txt: str) -> bool:
    """Qty is usually a small integer."""
    if not txt:
        return False
    txt = txt.strip()
    if not txt.isdigit():
        return False
    v = int(txt)
    return 1 <= v <= 9999


# ============================================================
# Main Extractor Class
# ============================================================

class InvoiceFieldExtractor:
    def __init__(self, lang: str = "fr"):
        self.lang = lang

        # Core keyword sets
        self.header_keywords = {
            "desc": ["designation", "description", "libelle", "désignation"],
            "qty": ["qte", "quantite", "quantité", "qty"],
            "price": ["prix", "p.u", "unitaire"],
            "total": ["total", "montant"]
        }

        self.total_keywords = ["total", "net a payer", "montant", "arrete", "net à payer"]

        self.payment_keywords = ["especes", "espèces", "cheque", "chèque", "virement", "carte"]

    # ============================================================
    # MAIN ENTRY
    # ============================================================

    def extract_from_step04(self, step04_json: Dict[str, Any]) -> Dict[str, Any]:
        lines = step04_json.get("lines", [])
        if not lines:
            return {}

        # Sort lines by Y then X (only for readability grouping)
        lines = sorted(lines, key=lambda k: (k["bbox"]["y"], k["bbox"]["x"]))

        full_text = "\n".join([l.get("text", "") for l in lines])

        return {
            "supplier": self._extract_supplier(lines),
            "customer": self._extract_customer(lines),
            "document": self._extract_document_info(lines, full_text),
            "items": self._extract_items(lines),   # <── NEW LOGIC
            "totals": self._extract_totals(lines),
            "payment": self._extract_payment(full_text)
        }

    # ============================================================
    # SUPPLIER EXTRACTION (ROBUST)
    # ============================================================

    def _extract_supplier(self, lines: List[Dict[str, Any]]):
        top_block = lines[:8]
        name = None
        address = []
        phone = None

        for l in top_block:
            t = l["text"].strip()
            low = normalize(t)

            if not name:
                # Supplier names are usually:
                # - longer than 5 chars
                # - mostly alphabetic
                if len(t) > 5 and re.search(r"[A-Za-z]", t):
                    name = t
                    continue

            # Address detection
            if "adresse" in low or re.search(r"\d{2,5}", t):
                address.append(t)

            # Phone detection
            m = re.search(r"(0[0-9]{8,10})", t.replace(" ", ""))
            if m:
                phone = m.group(1)

        return {
            "name": name,
            "address": " ".join(address) if address else None,
            "phone": phone
        }

    # ============================================================
    # CUSTOMER EXTRACTION
    # ============================================================

    def _extract_customer(self, lines: List[Dict[str, Any]]):
        customer = {"name": None, "address": None, "phone": None}

        for i, l in enumerate(lines):
            low = normalize(l["text"])
            if "client" in low:

                # Try inline form: "Client: JOHN DOE"
                m = re.search(r"client[:\s\.]+(.+)$", l["text"], re.IGNORECASE)
                if m:
                    customer["name"] = m.group(1).strip()

                # Next 3 lines form block
                for j in range(i+1, min(i+4, len(lines))):
                    txt = lines[j]["text"].strip()

                    # Stop if reaching items
                    if parse_money(txt):
                        break

                    # Phone?
                    m2 = re.search(r"(0[0-9]{8,10})", txt.replace(" ", ""))
                    if m2:
                        customer["phone"] = m2.group(1)
                        continue

                    # Address building
                    if not customer["address"]:
                        customer["address"] = txt
                    else:
                        customer["address"] += " " + txt

                break

        return customer

    # ============================================================
    # DOCUMENT INFO
    # ============================================================

    def _extract_document_info(self, lines, full_text):
        doc = {"type": "invoice", "number": None, "date": None}

        # Type guess
        low = normalize(full_text)
        if "livraison" in low:
            doc["type"] = "delivery_note"

        # Document number
        mnum = re.search(r"N['°º]?\s*([A-Za-z0-9\-\/\.]+)", full_text)
        if mnum:
            doc["number"] = mnum.group(1).strip()

        # Date
        mdate = re.search(r"(\d{1,2}[\/\-.]\d{1,2}[\/\-.]\d{2,4})", full_text)
        if mdate:
            doc["date"] = mdate.group(1)

        return doc

    # ============================================================
    # PAYMENT
    # ============================================================

    def _extract_payment(self, full_text: str):
        low = normalize(full_text)
        for p in self.payment_keywords:
            if p in low:
                return {"method": p}
        return {"method": None}

    # ============================================================
    # TOTALS
    # ============================================================

    def _extract_totals(self, lines: List[Dict[str, Any]]):
        totals = {"total_amount": None, "currency": "DA"}

        # Search bottom-up for money
        for l in reversed(lines):
            txt = l["text"]
            val = parse_money(txt)
            if val is not None:
                # Ensure line contains keyword or is big amount
                low = normalize(txt)
                if any(k in low for k in self.total_keywords) or val > 1000:
                    totals["total_amount"] = val
                    # Currency
                    m = re.search(r"(DA|DZD|EUR|€)", txt, re.IGNORECASE)
                    if m:
                        totals["currency"] = m.group(1)
                    break

        return totals

    # ============================================================
    # ⭐⭐⭐ PRODUCTION-GRADE ITEM EXTRACTION ⭐⭐⭐
    # ============================================================

    def _extract_items(self, lines: List[Dict[str, Any]]):
        """
        Hybrid semantic + layout item extraction.

        Strategy:
        1. Detect the first row where prices appear → table start.
        2. Group rows by Y proximity.
        3. For each row:
           - description = all non-money, non-qty text
           - qty = small integers
           - unit price + total = money fields sorted by X
        """

        groups = self._group_rows(lines)

        items = []

        for g in groups:
            parsed = self._parse_item_row(g)
            if parsed:
                items.append(parsed)

        return items

    # ------------------------------------------------------------
    # ROW GROUPING (layout)
    # ------------------------------------------------------------

    def _group_rows(self, lines: List[Dict[str, Any]]):
        """Groups text into visual rows based on Y-distance."""
        groups = []
        current = []
        last_y = None

        for l in lines:
            y = l["bbox"]["y"]
            t = l["text"].strip()

            # Skip empty / non-item
            if not t:
                continue

            # Item section starts once we see a price-like text
            # We detect ONLY after first price appears.
            if is_money_like(t):
                break

        # We start grouping AFTER detecting table header or price
        table_started = False
        groups = []
        current = []
        last_y = None

        for l in lines:
            txt = l["text"].strip()
            low = normalize(txt)

            # detect table area:
            if not table_started and is_money_like(txt):
                table_started = True

            if not table_started:
                continue

            # break when reaching totals area
            if any(k in low for k in self.total_keywords):
                break

            # group by Y
            y = l["bbox"]["y"]

            if last_y is None or abs(y - last_y) <= 18:
                current.append(l)
            else:
                if current:
                    groups.append(current)
                current = [l]

            last_y = y

        if current:
            groups.append(current)

        return groups

    # ------------------------------------------------------------
    # ROW PARSING (semantic)
    # ------------------------------------------------------------

    def _parse_item_row(self, group: List[Dict[str, Any]]) -> Optional[Dict]:
        """Parse a single invoice item row dynamically."""

        desc_fragments = []
        qty = None
        money_vals = []  # (x_center, value)

        for l in group:
            txt = l["text"].strip()
            xmid = l["bbox"]["x"] + l["bbox"]["w"] / 2

            if looks_like_qty(txt):
                # qty candidate
                if qty is None:
                    qty = int(txt)
                continue

            val = parse_money(txt)
            if val is not None:
                money_vals.append((xmid, val))
                continue

            # Otherwise → part of description
            desc_fragments.append(txt)

        if not desc_fragments and not money_vals:
            return None

        description = " ".join(desc_fragments).strip()

        # Money values: sorted left→right
        money_vals.sort(key=lambda x: x[0])

        unit_price = None
        total = None

        if len(money_vals) == 1:
            total = money_vals[0][1]
            if qty:
                unit_price = round(total / qty, 2)
        elif len(money_vals) >= 2:
            unit_price = money_vals[0][1]
            total = money_vals[-1][1]

        if not description or total is None:
            return None

        if qty is None:
            qty = 1  # assume 1 if missing

        return {
            "description": description,
            "quantity": qty,
            "unit_price": unit_price,
            "line_total": total
        }
