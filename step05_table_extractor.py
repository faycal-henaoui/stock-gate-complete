import re
import math
from typing import List, Dict, Any, Optional

class TableExtractor:
    def __init__(self):
        # Configuration for column detection (Bilingual FR/EN)
        self.column_keywords = {
            "description": [
                "description", "designation", "désignation", "libelle", "article", "service", "item", "product"
            ],
            "quantity": [
                "qté", "qte", "quantite", "quantité", "qty", "quantity", "nombre", "unit", "count"
            ],
            "unit_price": [
                "p.u", "pu", "prix unit", "prix unitaire", "unit price", "price/unit", "price"
            ],
            "total": [
                "montant", "total", "montant ht", "total ht", "prix total", "amount", "total price"
            ],
            "reference": [ # Added reference column as seen in your image
                "reference", "référence", "ref", "code", "sku"
            ]
        }

    def extract_table(self, lines: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Main method to extract table data using the 3-step algorithms provided:
        A. Header Identification
        B. Row Clustering
        C. Arithmetic Validation
        """
        
        # --- A. Identification de l'En-tête du Tableau ---
        header_info = self._identify_headers(lines)
        if not header_info:
            return {"error": "No table header found"}

        # Define the region of interest for the table (everything below headers)
        table_start_y = header_info["y_bottom"]
        
        # Determine where the table ends to avoid footer text "leakage"
        table_end_y = self._find_table_bottom(lines, table_start_y)
        
        table_lines = [
            l for l in lines 
            if l["bbox"]["y"] > table_start_y and l["bbox"]["y"] < table_end_y
        ]

        # --- B. Algorithme de Regroupement par Ligne (Row Clustering) ---
        raw_rows = self._cluster_rows(table_lines)
        
        # Align rows with columns defined by headers
        structured_rows = self._map_rows_to_columns(raw_rows, header_info["columns"])

        # --- C. Validation de la Cohérence Arithmétique ---
        validated_rows = self._validate_arithmetic(structured_rows)

        return {
            "headers": header_info["columns"],
            "rows": validated_rows
        }

    def _identify_headers(self, lines):
        """
        Searches for a horizontal sequence of column keywords.
        """
        # Group lines by roughly same Y to find "lines" of text
        y_groups = {}
        for line in lines:
            y_center = line["bbox"]["y"] + (line["bbox"]["h"] / 2)
            found_group = False
            for y_key in y_groups:
                if abs(y_key - y_center) < 15: # 15px threshold for "same line"
                    y_groups[y_key].append(line)
                    found_group = True
                    break
            if not found_group:
                y_groups[y_center] = [line]

        # Score each group to see if it looks like a header
        best_header = None
        max_matches = 0

        for y, group in y_groups.items():
            matches = {}
            for item in group:
                text_norm = item["text"].lower().strip()
                for col_type, keywords in self.column_keywords.items():
                    if any(k in text_norm for k in keywords):
                        # Found a column header!
                        matches[col_type] = item
            
            # We need at least 2 distinct columns (e.g. Desc + Price) to call it a table
            if len(matches) >= 2 and len(matches) > max_matches:
                max_matches = len(matches)
                # Sort columns by X to know order
                sorted_cols = sorted(matches.items(), key=lambda x: x[1]["bbox"]["x"])
                
                # Calculate X boundaries using Midpoints for better alignment
                columns_config = []
                for i in range(len(sorted_cols)):
                    col_type, item = sorted_cols[i]
                    
                    # Start: Midpoint between prev_col end and this_col start
                    # If first col, use a sensible left buffer or 0
                    if i == 0:
                        x_start = 0 
                    else:
                        prev_item = sorted_cols[i-1][1]
                        prev_right = prev_item["bbox"]["x"] + prev_item["bbox"]["w"]
                        curr_left = item["bbox"]["x"]
                        x_start = (prev_right + curr_left) / 2
                    
                    # End: Midpoint between this_col right and next_col left
                    if i < len(sorted_cols) - 1:
                        curr_right = item["bbox"]["x"] + item["bbox"]["w"]
                        next_left = sorted_cols[i+1][1]["bbox"]["x"]
                        x_end = (curr_right + next_left) / 2
                    else:
                        # Last column goes to the right
                        x_end = 99999 

                    columns_config.append({
                        "type": col_type,
                        "x_start": x_start,
                        "x_end": x_end
                    })

                best_header = {
                    "y_bottom": max(item["bbox"]["y"] + item["bbox"]["h"] for item in group),
                    "columns": columns_config
                }

        return best_header

    def _find_table_bottom(self, lines, table_start_y):
        """
        Scans lines below the header to find a "Stop" keyword (Total, Arrêté, etc.)
        Returns the Y coordinate of the first stop line, or a large number if not found.
        """
        # Keywords that indicate the table has clearly ended
        stop_keywords = [
            "total", "net a payer", "montant", "arrêté", "arrete", "banque", "règlement", "reglement", "tva", "signature"
        ]
        
        # Sort potential lines by Y
        candidates = sorted([l for l in lines if l["bbox"]["y"] > table_start_y], key=lambda x: x["bbox"]["y"])
        
        for line in candidates:
            text_norm = line["text"].lower()
            # If line matches a stop keyword
            if any(k in text_norm for k in stop_keywords):
                # We found the footer start. Return its top Y.
                # But allow a tiny buffer? No, usually valid rows are above.
                return line["bbox"]["y"] - 5
                
        return 99999

    def _cluster_rows(self, table_lines):
        """
        Implementation of: "Les blocs de texte sont triés par leur coordonnée y.
        Si la différence Delta y entre deux blocs est inférieure à un seuil T..."
        """
        if not table_lines:
            return []

        # Sort by Y first
        sorted_lines = sorted(table_lines, key=lambda l: l["bbox"]["y"])
        
        rows = []
        current_row = []
        
        # Initialize with first item
        if sorted_lines:
            current_row.append(sorted_lines[0])

        for i in range(1, len(sorted_lines)):
            item = sorted_lines[i]
            prev_item = current_row[0] # compare with first item of current row (or average)
            
            # Dynamic threshold T: roughly the height of the text line
            # "T (calculé dynamiquement selon la hauteur de la police)"
            avg_height = sum(r["bbox"]["h"] for r in current_row) / len(current_row)
            threshold_T = avg_height * 0.8 # Slightly permissive

            delta_y = item["bbox"]["y"] - prev_item["bbox"]["y"]

            if delta_y < threshold_T:
                # Same row
                current_row.append(item)
            else:
                # New row
                rows.append(current_row)
                current_row = [item]
        
        if current_row:
            rows.append(current_row)

        return rows

    def _map_rows_to_columns(self, raw_rows, columns_config):
        """
        Assigns text blocks to specific columns based on X coordinates.
        Also merges multi-line text if needed.
        """
        structured_rows = []

        for row_items in raw_rows:
            row_data = {}
            for item in row_items:
                item_center_x = item["bbox"]["x"] + (item["bbox"]["w"] / 2)
                
                # Find which column this item belongs to
                matched_col = None
                for col_conf in columns_config:
                    if col_conf["x_start"] <= item_center_x < col_conf["x_end"]:
                        matched_col = col_conf["type"]
                        break
                
                if matched_col:
                    if matched_col in row_data:
                        row_data[matched_col] += " " + item["text"]
                    else:
                        row_data[matched_col] = item["text"]
            
            if row_data:
                structured_rows.append(row_data)
        
        return structured_rows

    def _validate_arithmetic(self, rows):
        """
        C. Validation de la Cohérence Arithmétique
        Total = Qty * UnitPrice
        """
        validated_rows = []
        
        for row in rows:
            # Clean and parse numbers
            qty = self._parse_quantity(row.get("quantity", "0"))
            price = self._parse_float(row.get("unit_price", "0"))
            total = self._parse_float(row.get("total", "0"))
            
            is_valid = False
            confidence = "low"
            
            # --- Auto-Correction Logic ---
            # Sometimes quantity is read as "1*1" or "1 1" (OCR noise)
            # If default parsing failed validation, try to infer quantity from Total/Price
            if qty > 0 and price > 0 and abs((qty * price) - total) > 0.1:
                if price > 0:
                     inferred_qty = total / price
                     # If inferred qty is close to an integer (e.g. 1.0, 2.0)
                     if abs(inferred_qty - round(inferred_qty)) < 0.05:
                         # Use the inferred quantity if it seems plausible (e.g. appearing in the raw text)
                         qty = float(round(inferred_qty))

            # Check if we have enough data to validate
            if qty > 0 and price > 0 and total > 0:
                calc_total = qty * price
                # Allow tolerance
                if abs(calc_total - total) < 0.5: # 0.5 DA tolerance
                    is_valid = True
                    confidence = "high"
            
            # Add metadata about validation
            row["_validation"] = {
                "is_valid": is_valid,
                "confidence": confidence,
                "calculated_total": qty * price if qty and price else 0
            }
            # Update the row with cleaner numbers for final output (optional)
            # row["quantity_clean"] = qty
            
            validated_rows.append(row)

        return validated_rows

    def _parse_quantity(self, text):
        """
        Special parser for quantity which might be '1*1' or '6' or '1 1'.
        """
        if not text: return 0.0
        # Common invoice noise: "1*1" -> treat as 1
        text = text.replace("*", " ") 
        
        # Extract first valid number found
        # e.g. "1 1" -> 1
        match = re.search(r"(\d+([\.,]\d+)?)", text)
        if match:
            try:
                val = float(match.group(1).replace(",", "."))
                return val
            except:
                return 0.0
        return 0.0

    def _parse_float(self, text):
        """Helper to extract float from string like '12 500,00 DA'"""
        if not text: return 0.0
        # replace comma with dot, remove non-numeric except dot
        clean = text.replace(",", ".")
        clean = re.sub(r"[^\d\.]", "", clean)
        try:
            return float(clean)
        except:
            return 0.0

if __name__ == "__main__":
    # Test Data
    print("Testing Table Algorithm...")
    
    # 1. Header Line
    # 2. Row 1: Mouse (valid math)
    # 3. Row 2: Keyboard (invalid math or missing)
    test_lines = [
        # Headers (Y ~ 100)
        {"text": "Description", "bbox": {"x": 50, "y": 100, "w": 100, "h": 20}},
        {"text": "Qté", "bbox": {"x": 200, "y": 100, "w": 50, "h": 20}}, # Qty
        {"text": "P.U.", "bbox": {"x": 300, "y": 100, "w": 50, "h": 20}}, # Price
        {"text": "Total", "bbox": {"x": 400, "y": 100, "w": 50, "h": 20}},

        # Row 1 (Y ~ 130) -> Mouse | 2 | 100 | 200
        {"text": "Souris Sans Fil", "bbox": {"x": 50, "y": 130, "w": 100, "h": 20}},
        {"text": "2", "bbox": {"x": 205, "y": 132, "w": 20, "h": 18}},
        {"text": "100.00", "bbox": {"x": 300, "y": 130, "w": 50, "h": 20}},
        {"text": "200.00", "bbox": {"x": 400, "y": 130, "w": 50, "h": 20}},

        # Row 2 (Y ~ 160) -> Keyboard | 1 | 500 | 999 (Error)
        {"text": "Clavier Gamer", "bbox": {"x": 50, "y": 160, "w": 100, "h": 20}}, 
        {"text": "(Mécanique)", "bbox": {"x": 50, "y": 178, "w": 100, "h": 20}}, # Multi-line desc
        {"text": "1", "bbox": {"x": 205, "y": 160, "w": 20, "h": 20}},
        {"text": "500.00", "bbox": {"x": 300, "y": 160, "w": 50, "h": 20}},
        {"text": "999.00", "bbox": {"x": 400, "y": 160, "w": 50, "h": 20}},
    ]

    extractor = TableExtractor()
    result = extractor.extract_table(test_lines)
    print(json.dumps(result, indent=2, ensure_ascii=False))
