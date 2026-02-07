import re
import math
import json
from typing import List, Dict, Any, Optional

class InnovativeExtractor:
    def __init__(self):
        # 1. Define Anchors and their specific search strategies
        self.rules = [
            {
                "field": "total_ttc",
                "anchors": [
                    # French
                    "total", "total ttc", "net a payer", "montant total", "grand total", "total général", 
                    # English
                    "total", "total amount", "grand total", "net to pay", "amount due"
                ],
                "search_direction": "right",
                "validator": self._is_money,
                "max_dist_x": 600,
                "max_dist_y": 20
            },
            {
                "field": "phone",
                "anchors": [
                    # French
                    "tel", "tél", "telephone", "téléphone", "mobile", "contact", 
                    # English
                    "phone", "cell", "mob", "call"
                ],
                "search_direction": "right_or_below",
                "validator": self._is_phone,
                "max_dist_x": 400,
                "max_dist_y": 60
            },
            {
                "field": "invoice_date",
                "anchors": [
                    # French
                    "date", "le", "du", "facture du", "date facture", 
                    # English
                    "date", "invoice date", "dated", "date of issue"
                ],
                "search_direction": "right",
                "extract_from_anchor_line": True,
                "validator": self._is_date,
                "cleaner": self._clean_date_from_text,
                "max_dist_x": 300,
                "max_dist_y": 20
            },
            {
                "field": "invoice_number",
                "anchors": [
                    # French
                    "facture n", "bon de livraison", "bl n", "n°", "n 0", 
                    # English
                    "invoice no", "invoice #", "inv #", "ref :"
                ],
                "search_direction": "right_or_below", # "Bon de livraison" title is usually above the number
                "extract_from_anchor_line": True,
                "validator": self._is_alphanumeric,
                "cleaner": self._clean_invoice_number,
                "max_dist_x": 300,
                "max_dist_y": 60,
                "exclude_keywords": ["adresse", "tel", "page", "client", "rocade", "gare"] # New: exclusion keywords
            },
            {
                "field": "supplier_name",
                "anchors": [
                    # French
                    "fournisseur", "vendeur", "société", "societe", "entreprise", "expéditeur", "expediteur", "émetteur", "emetteur",
                    # English
                    "supplier", "seller", "company", "from"
                ],
                "search_direction": "right_or_below",
                "extract_from_anchor_line": True,
                "validator": self._is_text_block,
                "cleaner": self._clean_supplier_name,
                "max_dist_x": 400,
                "max_dist_y": 120,
                "exclude_keywords": ["client", "buyer", "facture", "invoice", "bon de livraison", "date", "tel", "adresse"]
            },
            {
                "field": "buyer_name",
                "anchors": [
                    # French
                    "client", "facturé à", "doit", "acheteur", "destinataire", "au nom de",
                    # English
                    "bill to", "sold to", "customer", "client", "buyer"
                ],
                "search_direction": "right_or_below", 
                "extract_from_anchor_line": True, # New: allow "Client PASSAGER"
                "validator": self._is_text_block,
                "cleaner": self._clean_buyer_name, # New cleaner for buyer
                "max_dist_x": 400, 
                "max_dist_y": 150
            }
        ]

    def extract(self, step04_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main function to extract data based on relative anchors.
        """
        lines = step04_data.get("lines", [])
        extracted_data = {}

        # Pre-normalization for easier matching
        for line in lines:
            line["text_norm"] = line["text"].lower().strip()

        # Iterate through all our extraction rules
        for rule in self.rules:
            field_name = rule["field"]
            extracted_value = None
            best_score = float('inf') # We want the closest match

            # Find all potential anchors in the document
            matching_lines = []
            for l in lines:
                text_norm = l["text_norm"]
                for k in rule["anchors"]:
                    # Strict matching for short keys to avoid "ref" matching "Reference"
                    if k in text_norm:
                        # If key is short (< 4 chars), require word boundary
                        if len(k) < 4:
                            # pattern: (start or non-alpha) key (end or non-alpha)
                            # e.g. "ref" matches "ref: 123" but not "reference"
                            if not re.search(r'(^|[^a-z])' + re.escape(k) + r'($|[^a-z])', text_norm):
                                continue
                        
                        matching_lines.append(l)
                        break

            for anchor in matching_lines:
                # 0. Check for keywords to avoid (e.g. "Adresse No 1")
                if rule.get("exclude_keywords"):
                     anchor_text_lower = anchor["text"].lower()
                     if any(ex in anchor_text_lower for ex in rule["exclude_keywords"]):
                         continue

                # 1. Check if the value is IN the anchor line itself?
                if rule.get("extract_from_anchor_line"):
                    # Basic Strategy: Remove the anchor text, see what's left
                    # This is simple but effective for "Invoice: 123"
                    val = self._extract_suffix(anchor["text"], rule["anchors"])
                    if val:
                        cleaned_val = rule["cleaner"](val) if rule.get("cleaner") else val
                        if cleaned_val and rule["validator"](cleaned_val):
                            extracted_value = cleaned_val
                            best_score = 0
                            break
                    if val and rule["validator"](val):
                        # It's a match with distance 0
                        # But we still check candidates just in case there's a better labeled one?
                        # No, usually "Label: Value" is strong.
                        extracted_value = val
                        best_score = 0
                        break

                # 1. Look for connected blocks
                candidates = self._find_candidates_in_zone(anchor, lines, rule)
                
                for cand in candidates:
                    # Validate content
                    cand_text = cand["text"]
                    if rule.get("cleaner"):
                        cleaned = rule["cleaner"](cand_text)
                        if cleaned and rule["validator"](cleaned):
                            # Calculate distance to prioritize the closest one
                            dist = self._distance(anchor, cand)
                            if dist < best_score:
                                best_score = dist
                                extracted_value = cleaned
                        continue

                    if rule["validator"](cand_text):
                        # Calculate distance to prioritize the closest one
                        dist = self._distance(anchor, cand)
                        if dist < best_score:
                            best_score = dist
                            extracted_value = cand_text

            if extracted_value:
                extracted_data[field_name] = extracted_value

        # Fallback: guess supplier name from top-left header if missing
        if "supplier_name" not in extracted_data:
            guessed_supplier = self._guess_supplier_name(lines)
            if guessed_supplier:
                extracted_data["supplier_name"] = guessed_supplier

        return extracted_data

    def _extract_suffix(self, text, anchors):
        """
        Removes the anchor keyword from text to see if there is a value left.
        e.g. "Client Passager" -> returns "Passager"
        """
        text_lower = text.lower()
        longest_anchor = ""
        for k in anchors:
            # Check for word boundary or explicit match
            # e.g. "Ref" should not match "Reference"
            # Simple check: if k is short (<4 chars), ensure it's a whole word or followed by space/:
            if k in text_lower:
                if len(k) < 4:
                    # check if followed by non-alpha or end of string
                    pattern_check = re.search(re.escape(k) + r"(\b|[^a-z])", text_lower)
                    if not pattern_check:
                         continue
                
                if len(k) > len(longest_anchor):
                    longest_anchor = k
        
        if not longest_anchor: return None
        
        # Regex to remove anchor (case insensitive)
        pattern = re.compile(re.escape(longest_anchor), re.IGNORECASE)
        remaining = pattern.sub("", text).strip()
        
        # Remove common separators like :, ., -
        remaining = re.sub(r"^[:\.\-\s]+", "", remaining).strip()
        
        return remaining if len(remaining) > 0 else None

    def _find_candidates_in_zone(self, anchor, all_lines, rule):
        """
        Finds text blocks that are geometrically related to the anchor.
        """
        candidates = []
        ax, ay, aw, ah = anchor["bbox"]["x"], anchor["bbox"]["y"], anchor["bbox"]["w"], anchor["bbox"]["h"]
        anchor_center_y = ay + (ah / 2)
        anchor_right = ax + aw

        direction = rule["search_direction"]
        max_dx = rule.get("max_dist_x", 500)
        max_dy = rule.get("max_dist_y", 50)

        for line in all_lines:
            if line == anchor: continue # Don't match self

            lx, ly, lw, lh = line["bbox"]["x"], line["bbox"]["y"], line["bbox"]["w"], line["bbox"]["h"]
            line_center_y = ly + (lh / 2)

            # Strategy: RIGHT (Same line, to the right)
            if direction == "right":
                # Check Y alignment (centers are close)
                if abs(anchor_center_y - line_center_y) < max_dy:
                    # Check X position (must be to the right)
                    if lx > anchor_right and (lx - anchor_right) < max_dx:
                        candidates.append(line)
            
            # Strategy: BELOW (Underneath, roughly aligned X)
            elif direction == "below":
                # Check Y position (must be below)
                if ly > (ay + ah) and (ly - (ay + ah)) < max_dy:
                    # Check X alignment (overlap in X range)
                    if abs(lx - ax) < max_dx:
                        candidates.append(line)

            # Strategy: RIGHT OR BELOW
            elif direction == "right_or_below":
                 # Check Right
                is_right = (abs(anchor_center_y - line_center_y) < 20) and (lx > anchor_right and (lx - anchor_right) < max_dx)
                # Check Below
                is_below = (ly > (ay + ah) and (ly - (ay + ah)) < max_dy) and (abs(lx - ax) < 100)

                if is_right or is_below:
                    candidates.append(line)

        return candidates

    def _distance(self, box1, box2):
        # Euclidean distance between centers
        c1 = (box1["bbox"]["x"], box1["bbox"]["y"])
        c2 = (box2["bbox"]["x"], box2["bbox"]["y"])
        return math.sqrt((c1[0]-c2[0])**2 + (c1[1]-c2[1])**2)

    # --- Validators ---

    def _is_money(self, text):
        # Looks for digits, maybe commas/dots, maybe currency symbols
        cleaned = re.sub(r"[^\d,\.]", "", text)
        return len(cleaned) > 0 and any(c.isdigit() for c in text)

    def _is_phone(self, text):
        # Simplistic phone check: lots of digits
        digits = re.sub(r"[^\d]", "", text)
        return len(digits) >= 8

    def _is_date(self, text):
        # Simple date regex
        return re.search(r"\d{2,4}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}", text) is not None

    def _is_alphanumeric(self, text):
        return len(text) > 1

    def _is_text_block(self, text):
        return len(text) > 3 and not self._is_money(text)

    # --- Cleaners ---

    def _clean_invoice_number(self, text):
        # Remove date info if attached (e.g. "123456 du 23/06/2025")
        # Split by " du " or " dated "
        parts = re.split(r'\s+(du|dated|le|date)\s+', text, flags=re.IGNORECASE)
        # Also strip trailing dots or spaces
        clean_text = parts[0].strip(" .:,")
        return clean_text

    def _clean_buyer_name(self, text):
        # Prevent picking "Addresse" if it accidentally matched
        if "adress" in text.lower():
            # Try to rescue? No, just drop it or return empty
            return ""
        return text

    def _clean_supplier_name(self, text):
        if not text:
            return ""
        lower = text.lower()
        if any(k in lower for k in ["client", "buyer", "facture", "invoice", "bon de livraison"]):
            return ""
        return text.strip()

    def _clean_date_from_text(self, text):
        if not text:
            return ""
        match = re.search(r"\d{1,2}[\/\-.]\d{1,2}[\/\-.]\d{2,4}", text)
        if match:
            return match.group(0)
        match = re.search(r"\d{4}[\/\-.]\d{1,2}[\/\-.]\d{1,2}", text)
        return match.group(0) if match else text

    def _guess_supplier_name(self, lines: List[Dict[str, Any]]) -> str:
        if not lines:
            return ""

        max_y = max(line["bbox"]["y"] for line in lines if line.get("bbox")) or 1
        top_threshold = max_y * 0.2

        def is_candidate(text: str) -> bool:
            if not text or len(text.strip()) < 3:
                return False
            lower = text.lower()
            if any(k in lower for k in ["bon de livraison", "facture", "invoice", "client", "adresse", "tel", "date"]):
                return False
            if re.fullmatch(r"[\d\s\-/]+", text):
                return False
            return True

        top_lines = [
            line for line in lines
            if line.get("bbox") and line["bbox"]["y"] <= top_threshold and is_candidate(line.get("text", ""))
        ]

        if not top_lines:
            return ""

        top_lines.sort(key=lambda l: (l["bbox"]["y"], l["bbox"]["x"]))
        return top_lines[0]["text"].strip()

if __name__ == "__main__":
    # Test with dummy data
    print("Testing Innovative Extractor...")
    
    # Simulate step 04 output
    test_data = {
        "lines": [
            {"text": "Facture N°", "bbox": {"x": 50, "y": 50, "w": 100, "h": 20}, "index": 0},
            {"text": "F-2023-001", "bbox": {"x": 160, "y": 50, "w": 100, "h": 20}, "index": 1}, # To the right
            
            {"text": "Total TTC", "bbox": {"x": 400, "y": 500, "w": 80, "h": 20}, "index": 2},
            {"text": "12 500.00 DA", "bbox": {"x": 500, "y": 500, "w": 100, "h": 20}, "index": 3}, # To the right
            
            {"text": "Tél:", "bbox": {"x": 50, "y": 600, "w": 50, "h": 20}, "index": 4},
            {"text": "0550 12 34 56", "bbox": {"x": 110, "y": 600, "w": 120, "h": 20}, "index": 5}, # To the right
        ]
    }

    extractor = InnovativeExtractor()
    result = extractor.extract(test_data)
    print(json.dumps(result, indent=2, ensure_ascii=False))
