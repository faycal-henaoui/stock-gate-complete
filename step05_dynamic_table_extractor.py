import re
import math
import json
from typing import List, Dict, Any, Optional

class DynamicTableExtractor:
    def __init__(self):
        # We classify columns into "Standard Types" (for logic/math) and "Others" (just data)
        # ORDER MATTERS: Specific columns (Total, Price) are checked before generic ones (Description)
        self.standard_map = {
            "total": ["montant", "total", "prix total", "amount", "valeur", "net a payer"],
            "unit_price": ["p.u", "pu", "prix", "price", "unitaire", "u.p"],
            "quantity": ["qté", "qte", "quantite", "qty", "quantity", "nombre", "q.te"],
            "unit": ["unité", "unite", "u", "carton", "boite", "colis"],
            "extra_n": ["n°", "no", "num", "#"],
            "reference": ["reference", "référence", "ref", "code"],
            "description": ["description", "designation", "désignation", "libelle", "article", "produit", "nature"]
        }

    def _refine_headers(self, columns):
        """
        Enhance column logic based on what headers co-exist.
        Rule 1: If 'Reference' exists but 'Description' is missing, Reference IS the Description/Product.
        Rule 2: If 'Reference' and 'Description' both exist, Reference is likely a Code or Index (N).
        """
        types_found = set(c["type"] for c in columns)
        
        has_desc = "description" in types_found
        has_ref = "reference" in types_found
        
        # Case 1: Reference -> Description
        # e.g. Table: [ N | Reference | Price | Total ] -> Reference holds product names
        if has_ref and not has_desc:
            print("[DynamicTable] Context Rule: No 'Description' header. Treating 'Reference' as 'Description'.")
            for c in columns:
                if c["type"] == "reference":
                    c["type"] = "description"
            return columns
            
        # Case 2: Reference + Description
        # e.g. Table: [ N | Reference | Designation | ... ]
        # The 'self.standard_map' logic already correctly separates them.
        # But we confirm that Reference expects Codes/Ints, not Names.
        
        # Note: We also separated "n°" into "extra_n" broadly, but let's ensure "Reference" doesn't catch N unless N is missing.
        
        return columns

    def extract_table(self, lines: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Dynamic extraction strategy:
        1. Find a Header Line containing at least one strong anchor.
        2. Treat ALL text blocks on that line as columns.
        3. Map rows based on these dynamic columns.
        """
        
        # 1. Identify Header Line & Dynamic Columns configuration
        header_info = self._find_dynamic_header(lines)
        if not header_info:
            print("[DynamicTable] No clear header found.")
            return {"error": "No table header found", "headers": [], "rows": []}

        # 1b. Refine Column Types based on Context (User Logic)
        header_info["columns"] = self._refine_headers(header_info["columns"])

        # 2. Define Table Borders
        table_start_y = header_info["y_bottom"]
        table_end_y = self._find_table_bottom(lines, table_start_y)
        
        print(f"[DynamicTable] Table detected Y range: {table_start_y:.1f} to {table_end_y:.1f}")

        # 3. Filter Row Candidates
        # Use a small margin (e.g. 5px) because sometimes row items start exactly where header ends
        # or slightly overlap in Y-coordinates.
        table_lines = [
            l for l in lines 
            if l["bbox"]["y"] > (table_start_y - 5) and l["bbox"]["y"] < table_end_y
        ]

        # 4. Cluster Text into Rows
        raw_rows = self._cluster_rows(table_lines)
        
        # 5. Map Row Text to the detected Columns
        structured_rows = self._map_to_columns(raw_rows, header_info["columns"])
        
        # 5b. Apply Semantic Corrections (User Rule: Ref should be integer, Descr matches text)
        structured_rows = self._apply_semantic_correction(structured_rows)

        # 6. Validate Math (using the columns we identified as standard types)
        validated_rows = self._validate_arithmetic(structured_rows)

        return {
            "headers": header_info["columns"],
            "rows": validated_rows
        }

    def _apply_semantic_correction(self, rows):
        """
        Fixes common misalignments based on data types:
        - Reference column capturing Description text (Ref should be int/code, Descr text)
        - Ensure numeric fields are clean
        """
        for row in rows:
            # Rule 1: Fix Reference stealing Description
            ref_val = row.get("reference", "").strip()
            desc_val = row.get("description", "").strip()
            
            # If Reference has value but Description is empty
            if ref_val and not desc_val:
                # Check if Ref looks like a Description (has alphabets, spaces, length > 3)
                # And Ref does NOT look like a simple integer index
                has_alpha = any(c.isalpha() for c in ref_val)
                is_simple_int = ref_val.isdigit()
                
                if has_alpha and not is_simple_int:
                    # Move Content
                    print(f"[SemanticFix] Moving '{ref_val}' from Reference to Description")
                    row["description"] = ref_val
                    row["reference"] = ""

            # Rule 2: Clean types (User request: Qty, Unit should be integers/clean)
             # Note: 'unit' column in this invoice ("Carton") contains "10*1", so we keep it as string
             # But 'quantity' should be integer.

            # Rule 3: If 'Reference' is empty but 'extra_n' (N) exists, and we're in a mode where
            # Reference should be an index/code, then Reference = extra_n.
            # This handles cases where "N" and "Ref" columns are redundant.
            ref_val = row.get("reference", "").strip()
            extra_n_val = row.get("extra_n", "").strip()
            
            if not ref_val and extra_n_val:
                row["reference"] = extra_n_val

            # Rule 4: If description is empty and extra_ columns contain text, move the best one
            desc_val = row.get("description", "").strip()
            if not desc_val:
                extra_candidates = []
                for key, value in row.items():
                    if key.startswith("extra_") and key != "extra_n":
                        text = str(value).strip()
                        if text and any(c.isalpha() for c in text):
                            extra_candidates.append((key, text))

                if extra_candidates:
                    # Choose the longest alpha candidate as description
                    best_key, best_text = max(extra_candidates, key=lambda x: len(x[1]))
                    row["description"] = best_text
                    # Keep the original extra field but clear it to avoid duplication
                    row[best_key] = ""
            
        return rows

    def _find_dynamic_header(self, lines):
        # Group lines by Y coordinate
        y_groups = {}
        for line in lines:
            y_center = line["bbox"]["y"] + (line["bbox"]["h"] / 2)
            found = False
            for y_key in y_groups:
                if abs(y_key - y_center) < 15: # 15px tolerance
                    y_groups[y_key].append(line)
                    found = True
                    break
            if not found:
                y_groups[y_center] = [line]

        # Evaluate groups
        best_header = None
        max_score = 0
        
        # We need identifying keywords to be sure it's a header
        # Flatten all keywords
        all_keywords = set()
        for k_list in self.standard_map.values():
            all_keywords.update(k_list)

        for y, group in y_groups.items():
            # Count how many recognized keywords are in this group
            score = 0
            # Also track which keywords matched
            matches = []
            
            for item in group:
                txt = item["text"].lower().strip()
                # Check for match
                is_key = False
                for k in all_keywords:
                    # Loose check: is the keyword inside the text?
                    if k in txt: 
                        score += 1
                        is_key = True
                        break
            
            # Heuristic: Valid header needs at least 2 known keywords (e.g. Ref + Total)
            # Or 1 very strong one + multiple items? 
            # Let's stick to score >= 2 to avoid noise lines
            if score >= 2:
                if score > max_score:
                    max_score = score
                    # Create Configuration
                    best_header = self._build_header_config(group)

        return best_header

    def _build_header_config(self, group):
        # Sort items left to right
        sorted_cols = sorted(group, key=lambda x: x["bbox"]["x"])
        
        columns_config = []
        
        for i in range(len(sorted_cols)):
            item = sorted_cols[i]
            x_center = item["bbox"]["x"] + item["bbox"]["w"] / 2
            
            # Determine type
            txt = item["text"].lower().strip()
            col_type = "extra_" + self._clean_header_name(txt) # default
            
            # Try to map to standard type
            found_std = False
            for std_type, keywords in self.standard_map.items():
                if any(k in txt for k in keywords):
                    col_type = std_type
                    found_std = True
                    break
            
            # Calculate X Boundaries (Midpoint strategy)
            
            # Left bound
            if i == 0:
                x_start = 0
            else:
                prev = sorted_cols[i-1]
                prev_right = prev["bbox"]["x"] + prev["bbox"]["w"]
                curr_left = item["bbox"]["x"]
                x_start = (prev_right + curr_left) / 2
                
            # Right bound
            if i == len(sorted_cols) - 1:
                x_end = 99999
            else:
                curr_right = item["bbox"]["x"] + item["bbox"]["w"]
                next_left = sorted_cols[i+1]["bbox"]["x"]
                x_end = (curr_right + next_left) / 2
                
            columns_config.append({
                "type": col_type,
                "label": item["text"], # Keep original label
                "x_start": x_start,
                "x_end": x_end
            })
            
        return {
            "y_bottom": max(i["bbox"]["y"] + i["bbox"]["h"] for i in group),
            "columns": columns_config
        }

    def _clean_header_name(self, text):
        return re.sub(r'[^a-zA-Z0-9]', '', text).lower()

    def _find_table_bottom(self, lines, start_y):
        stop_words = ["total", "net a payer", "montant", "arrête", "arrete", "banque", "règlement", "tva", "signature"]
        candidates = sorted([l for l in lines if l["bbox"]["y"] > start_y], key=lambda x: x["bbox"]["y"])
        
        for l in candidates:
            t = l["text"].lower()
            if any(w in t for w in stop_words):
                return l["bbox"]["y"] - 5
        return 99999

    def _cluster_rows(self, lines):
        # Same robust logic as before
        if not lines: return []
        sorted_lines = sorted(lines, key=lambda l: l["bbox"]["y"])
        rows = []
        current = [sorted_lines[0]]
        
        for i in range(1, len(sorted_lines)):
            item = sorted_lines[i]
            avg_h = sum(r["bbox"]["h"] for r in current) / len(current)
            prev_y = current[0]["bbox"]["y"]
            
            if abs(item["bbox"]["y"] - prev_y) < (avg_h * 0.7):
                current.append(item)
            else:
                rows.append(current)
                current = [item]
        if current: rows.append(current)
        return rows

    def _map_to_columns(self, rows, config):
        structured = []
        for row_items in rows:
            entry = {}
            for item in row_items:
                cx = item["bbox"]["x"] + item["bbox"]["w"]/2
                
                # Find matching column
                target_col = None
                for col in config:
                    if col["x_start"] <= cx < col["x_end"]:
                        target_col = col["type"]
                        break
                
                if target_col:
                    if target_col in entry:
                        entry[target_col] += " " + item["text"]
                    else:
                        entry[target_col] = item["text"]
            if entry:
                structured.append(entry)
        return structured

    def _validate_arithmetic(self, rows):
        # Validates only if we found the necessary standard columns
        validated = []
        for row in rows:
            # Safely parse
            qty = self._parse_qty(row.get("quantity", "0"))
            price = self._parse_float(row.get("unit_price", "0"))
            total = self._parse_float(row.get("total", "0"))
            
            # Logic: Auto-recover quantity if missing
            if qty == 0 and price > 0 and total > 0:
                 inferred = total / price
                 if abs(inferred - round(inferred)) < 0.05:
                     qty = float(round(inferred))
            
            valid = False
            if qty > 0 and price > 0 and total > 0:
                if abs((qty * price) - total) < 1.0: # 1 DA tolerance
                    valid = True
            
            row["_validation"] = {
                "is_valid": valid,
                "calculated_total": qty * price if qty else 0
            }
            # Clean values for output
            # row["quantity"] = qty
            
            validated.append(row)
        return validated

    def _parse_float(self, t):
        if not t: return 0.0
        clean = t.replace(",", ".").replace(" ", "")
        # keep digits and dot
        clean = re.sub(r"[^\d\.]", "", clean)
        try: return float(clean)
        except: return 0.0

    def _parse_qty(self, t):
        if not t: return 0.0
        t = str(t).replace("*", " ")
        match = re.search(r"(\d+([\.,]\d+)?)", t)
        if match:
             try: return float(match.group(1).replace(",", "."))
             except: return 0.0
        return 0.0
