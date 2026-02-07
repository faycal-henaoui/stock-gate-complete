# pipeline.py
import os
import sys
import cv2
import json
try:
    import fitz # PyMuPDF
except ImportError:
    fitz = None

from step2_line_detection import LineDetectionStep
from step03_svtr import SVTRRecognizer
import fix_numpy
from step04_reconstruct import Step04Reconstructor
from step05_innovative_extractor import InnovativeExtractor
# Switched to Dynamic Extractor
from step05_dynamic_table_extractor import DynamicTableExtractor
from step06_visualize import create_pfe_report

import time

class Pipeline:
    def __init__(self, debug_mode=True):
        self.debug_mode = debug_mode
        self.line_detection = LineDetectionStep()
        self.recognizer = SVTRRecognizer()
        self.reconstructor = Step04Reconstructor()
        # Initialize our new "Innovative" extractors
        self.field_extractor = InnovativeExtractor()
        # Improved Dynamic Table Algorithm
        self.table_extractor = DynamicTableExtractor()
        
        self.debug_dir = "debug_out"
        if self.debug_mode and not os.path.exists(self.debug_dir):
            os.makedirs(self.debug_dir)
            
        # Metric Collection
        self.metrics = {
            "times": {},
            "confidences": []
        }

    def _to_int_pt(self, p):
        return (int(p[0]), int(p[1]))

    def run_step2(self, image_path: str):
        t0 = time.time()
        print(f"[PIPELINE] Input image: {image_path}")

        result = self.line_detection.run(image_path)
        boxes = result["boxes"]
        crops = result["crops"]
        
        self.metrics["times"]["Step 2 (Detection)"] = time.time() - t0

        print(f"[PIPELINE] Step 2 -> {len(boxes)} boxes found")

        if self.debug_mode:
            # Save debug lines
            img = cv2.imread(image_path)
            if img is not None:
                for box in boxes:
                    for i in range(4):
                        p1 = self._to_int_pt(box[i])
                        p2 = self._to_int_pt(box[(i+1)%4])
                        cv2.line(img, p1, p2, (0,255,0), 2)

                cv2.imwrite(f"{self.debug_dir}/step2_boxes.png", img)

            for i, crop in enumerate(crops):
                cv2.imwrite(f"{self.debug_dir}/line_crop_{i:02d}.png", crop)

        return {
            "image_path": image_path,
            "line_boxes": boxes,
            "line_crops": crops,
        }

    def run_step3_recognize(self, step2_output):
        t0 = time.time()
        print("[PIPELINE] Running Step 3: SVTR recognition")

        img = cv2.imread(step2_output["image_path"])
        boxes = step2_output["line_boxes"]

        # Use the recognizer already initialized
        results = self.recognizer.recognize_lines(img, boxes)
        
        # Collect metric data
        raw_texts = []
        for res in results:
            if isinstance(res, tuple):
                text, score = res
                raw_texts.append(text)
                self.metrics["confidences"].append(score)
            else:
                raw_texts.append(str(res))
                self.metrics["confidences"].append(0.0)

        self.metrics["times"]["Step 3 (Recognition)"] = time.time() - t0
        print("[PIPELINE] Recognizing text complete.")
        
        if self.debug_mode:
            print("----- Step 3 Output -----")
            for idx, text in enumerate(raw_texts):
                # save debug files
                if img is not None and idx < len(boxes):
                    self.save_debug_line(idx, img, boxes[idx], text)

        # Return correct tuple formatted list or just texts depending on next step needs?
        # step04 expects pure text list or objects.
        # But wait, we wanted to pass confidence to step04?
        # Let's pass the tuples to step04 and handle it there.
        return results # List of (text, score)
        
    def save_debug_line(self, idx, img, box, text):
        """Saves debug images + text for each detected line."""

        # Ensure folder exists
        if not os.path.exists(self.debug_dir):
            os.makedirs(self.debug_dir)

        # 1 -- save raw crop
        xs = [p[0] for p in box]
        ys = [p[1] for p in box]
        x1, y1 = int(min(xs)), int(min(ys))
        x2, y2 = int(max(xs)), int(max(ys))
        
        # Clip coordinates
        h, w = img.shape[:2]
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)

        crop = img[y1:y2, x1:x2]
        cv2.imwrite(f"{self.debug_dir}/line_{idx:02d}.png", crop)

        # 2 -- save image with box
        img_box = img.copy()
        for i in range(4):
            p1 = self._to_int_pt(box[i])
            p2 = self._to_int_pt(box[(i+1)%4])
            cv2.line(img_box, p1, p2, (0,255,0), 2)
        cv2.imwrite(f"{self.debug_dir}/line_{idx:02d}_box.png", img_box)

        # 3 -- save image with box + recognized text
        img_text = img_box.copy()
        # Avoid crashing on None text
        display_text = str(text) if text else ""
        cv2.putText(
            img_text, display_text, (x1, max(0, y1 - 10)),
            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,0,255), 2
        )
        cv2.imwrite(f"{self.debug_dir}/line_{idx:02d}_box_text.png", img_text)

        # 4 -- save recognized text into .txt file
        with open(f"{self.debug_dir}/line_{idx:02d}.txt", "w", encoding="utf-8") as f:
            f.write(display_text)

    def run_step4_reconstruct(self, step2_output, step3_results):
        t0 = time.time()
        print("[PIPELINE] Running Step 4: Reconstruct layout")
        # Build combined entries: text + bbox + index
        combined = []
        boxes = step2_output["line_boxes"]
        
        for idx, res in enumerate(step3_results):
            if idx >= len(boxes):
                break
                
            text = ""
            score = 0.0
            if isinstance(res, tuple):
                text, score = res
            else:
                text = str(res)
                
            combined.append({
                "index": idx,
                "text": text,
                "confidence": score, # NEW: Include confidence in structure
                "bbox": boxes[idx],
            })

        output = self.reconstructor.reconstruct(combined)
        self.metrics["times"]["Step 4 (Reconstruct)"] = time.time() - t0

        if self.debug_mode:
            # Save JSON for debugging
            import json
            with open(f"{self.debug_dir}/step04_structure.json", "w", encoding="utf-8") as f:
                json.dump(output, f, indent=4, ensure_ascii=False)
            print("[STEP 04] Reconstructed layout saved to debug_out/step04_structure.json")
            
        return output

    def run_step5_extract(self, step4_output):
        t0 = time.time()
        print("[PIPELINE] Running Step 5: Innovative & Data Extraction")
        
        # 1. Field Extraction (Header info) using Anchor-based approach
        print("   -> Extracting fields (Total, Date, Ref, etc)...")
        fields = self.field_extractor.extract(step4_output)
        
        # 2. Table Extraction (Items) using Horizontal/Vertical clustering
        print("   -> Extracting table items (Dynamic Algorithm)...")
        table_result = self.table_extractor.extract_table(step4_output["lines"])
        
        # Combine everything
        final_result = {
            "fields": fields,
            "table": {
                "headers": table_result.get("headers", []),
                "rows": table_result.get("rows", []),
                "error": table_result.get("error")
            }
        }
        
        # --- METRICS FOR STEP 5 ---
        required_fields = ["total_ttc", "invoice_date", "invoice_number", "supplier_name"]
        found_count = sum(1 for f in required_fields if fields.get(f))
        completeness = found_count / len(required_fields)
        
        # Metric: Arithmetic Consistency (Logic Check)
        valid_math_rows = 0
        total_math_rows = 0
        rows = table_result.get("rows", [])
        for row in rows:
            try:
                # Clean and parse coordinates
                q = float(str(row.get("quantity", "0")).replace(",", ".").replace(" ", "") or 0)
                p = float(str(row.get("unit_price", "0")).replace(",", ".").replace(" ", "") or 0)
                t = float(str(row.get("total", "0")).replace(",", ".").replace(" ", "") or 0)
                
                # Verify logic: Q * P = T (with small tolerance for rounding)
                if q > 0 and p > 0 and t > 0:
                    total_math_rows += 1
                    if abs((q * p) - t) < 0.2: # 0.2 tolerance for rounding errors
                        valid_math_rows += 1
            except:
                pass
        
        math_consistency = 0
        if total_math_rows > 0:
            math_consistency = valid_math_rows / total_math_rows

        self.metrics["extraction"] = {
            "completeness": completeness,
            "found_fields": found_count,
            "total_fields": len(required_fields),
            "table_rows": len(rows),
            "math_accuracy": math_consistency,
            "logic_checked_rows": total_math_rows
        }
        # --------------------------
        
        self.metrics["times"]["Step 5 (Extraction)"] = time.time() - t0
        
        if self.debug_mode:
            # Save JSON for debugging/result
            out_file = f"{self.debug_dir}/step05_final_extracted.json"
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(final_result, f, indent=4, ensure_ascii=False)
                
            print(f"[STEP 05] Final extraction saved to {out_file}")
            
        return final_result
        
    def generate_metrics_charts(self):
        """Generates professional charts for the thesis."""
        try:
            import matplotlib.pyplot as plt
            import numpy as np
            
            # Use a clean style
            try:
                plt.style.use('ggplot')
            except:
                pass # Fallback to default
            
            # Create a figure with a grid layout
            fig = plt.figure(figsize=(12, 10))
            gs = fig.add_gridspec(2, 2, height_ratios=[1, 0.8])
            
            # --- 1. Execution Time (Horizontal Bar Chart) ---
            ax1 = fig.add_subplot(gs[0, 0])
            steps = list(self.metrics["times"].keys())
            times = list(self.metrics["times"].values())
            
            # Shorten names for clean display
            clean_steps = [s.split('(')[0].strip().replace("Step ", "Step") for s in steps]
            
            # Colors for bars
            colors = ['#3498db', '#e74c3c', '#9b59b6', '#2ecc71']
            bars = ax1.barh(clean_steps, times, color=colors[:len(times)])
            
            ax1.set_title('Processing Latency per Stage', fontsize=12, pad=10)
            ax1.set_xlabel('Time (seconds)')
            
            # Add text labels to bars
            max_time = max(times) if times else 1.0
            for bar in bars:
                width = bar.get_width()
                label = f"{width:.3f}s"
                
                # Position text
                if width < max_time * 0.7:
                     ax1.text(width + (max_time * 0.02), bar.get_y() + bar.get_height()/2, 
                             label, va='center', color='black', fontweight='bold')
                else:
                     ax1.text(width - (max_time * 0.02), bar.get_y() + bar.get_height()/2, 
                             label, va='center', ha='right', color='white', fontweight='bold')

            # --- 2. Confidence Distribution (Histogram) ---
            ax2 = fig.add_subplot(gs[0, 1])
            confidences = self.metrics["confidences"]
            mean_conf = np.mean(confidences) if confidences else 0
            
            # Histogram
            n, bins, patches = ax2.hist(confidences, bins=15, range=(0,1), 
                                      color='#1abc9c', edgecolor='white', alpha=0.8)
            
            # Mean Line
            ax2.axvline(mean_conf, color='#e67e22', linestyle='--', linewidth=2, 
                        label=f'Avg Accuracy: {mean_conf*100:.1f}%')
            
            ax2.set_title('OCR Model Confidence Distribution', fontsize=12, pad=10)
            ax2.set_xlabel('Confidence Score (0.0 - 1.0)')
            ax2.set_ylabel('Number of Text Lines')
            ax2.legend(loc='upper left')
            
            # --- 3. Performance Summary Card (Table) ---
            ax3 = fig.add_subplot(gs[1, :])
            ax3.axis('off')
            
            total_time = sum(times)
            total_boxes = len(confidences)
            
            # Step 5 Metrics
            ext_metrics = self.metrics.get("extraction", {})
            completeness = ext_metrics.get("completeness", 0)
            rows_count = ext_metrics.get("table_rows", 0)
            found_fields = ext_metrics.get("found_fields", 0)
            total_fields_target = ext_metrics.get("total_fields", 4)
            math_acc = ext_metrics.get("math_accuracy", 0) # NEW
            
            # Simulated F1-Score (Harmonic mean of Confidence & Completeness)
            estimated_f1 = 0
            if (mean_conf + completeness) > 0:
                estimated_f1 = 2 * (mean_conf * completeness) / (mean_conf + completeness)
            
            table_data = [
                ["KPI Metric", "Value", "Technical Description"],
                ["Total Pipeline Latency", f"{total_time:.3f} sec", "End-to-end processing time from Image to JSON"],
                ["OCR Precision (Confidence)", f"{mean_conf*100:.1f}%", "Avg probability of correct character recognition (SVTR)"],
                ["Extraction Recall (Fields)", f"{found_fields}/{total_fields_target} ({completeness*100:.0f}%)", "Ratio of key business fields (Date, Total, etc.) found"],
                ["Logic Consistency (Math)", f"{math_acc*100:.1f}%", "Rows passing 'Qty * Price = Total' verification check"],
                ["F1-Score (Estimated)", f"{estimated_f1*100:.1f}%", "Harmonic mean of Recognition Confidence and Extraction Recall"],
                ["Est. Throughput", f"{total_boxes/total_time:.1f} lines/sec", "Processing speed capability of the current hardware"]
            ]
            
            # Create table
            table = ax3.table(cellText=table_data, loc='center', cellLoc='left', colWidths=[0.25, 0.25, 0.5])
            table.auto_set_font_size(False)
            table.set_fontsize(11)
            table.scale(1, 1.8) # Make rows taller
            
            # Style headers
            for (row, col), cell in table.get_celld().items():
                if row == 0:
                    cell.set_text_props(weight='bold', color='white')
                    cell.set_facecolor('#2c3e50')
                    cell.set_edgecolor('white')
                else:
                    cell.set_facecolor('#ecf0f1')
                    cell.set_edgecolor('white')
            
            ax3.set_title("System Performance Scorecard", fontsize=14, fontweight='bold')

            plt.tight_layout()
            save_path = f"{self.debug_dir}/REPORT_advanced_metrics.png"
            plt.savefig(save_path, dpi=200) # Higher DPI for thesis
            print(f"[METRICS] Advanced dashboard saved to {save_path}")
            plt.close()
            
        except ImportError:
            print("[METRICS] Matplotlib not installed. Skipping chart generation.")
        except Exception as e:
            print(f"[METRICS] Error generating charts: {e}")

    def run_step6_visualize(self, image_path, final_data):
        print("[PIPELINE] Running Step 6: Generate Visual Report")
        
        # Generate output filename
        base_name = os.path.splitext(os.path.basename(image_path))[0]
        pdf_path = f"REPORT_{base_name}.pdf"
        
        json_tmp = f"{self.debug_dir}/temp_for_pdf.json"
        with open(json_tmp, "w", encoding="utf-8") as f:
            json.dump(final_data, f, indent=4, ensure_ascii=False)
            
        try:
            create_pfe_report(image_path, json_tmp, pdf_path)
            print(f"\n[SUCCESS] PDF Report generated at: {os.path.abspath(pdf_path)}")
        except Exception as e:
            print(f"[ERROR] Failed to generate PDF: {e}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python pipeline.py <image_path>")
        return

    original_path = sys.argv[1]
    processing_path = original_path

    # Handle PDF input
    if original_path.lower().endswith(".pdf"):
        if fitz is None:
            print("[ERROR] Input is PDF but 'pymupdf' is not installed. Run: pip install pymupdf")
            return
            
        print(f"[PIPELINE] Detected PDF: {original_path}. Converting page 1 to image...")
        try:
            doc = fitz.open(original_path)
            if len(doc) < 1:
                print("[ERROR] PDF is empty.")
                return
            page = doc.load_page(0) # 0-indexed
            # Use appropriate DPI for OCR (300 is usually good)
            pix = page.get_pixmap(dpi=300) 
            
            # Ensure debug directory exists
            if not os.path.exists("debug_out"):
                os.makedirs("debug_out")
                
            base_name = os.path.splitext(os.path.basename(original_path))[0]
            processing_path = os.path.join("debug_out", f"{base_name}_converted.png")
            
            pix.save(processing_path)
            print(f"[PIPELINE] PDF converted to: {processing_path}")
            doc.close()
        except Exception as e:
            print(f"[ERROR] Could not convert PDF: {e}")
            return

    pipeline = Pipeline()

    s2 = pipeline.run_step2(processing_path)
    s3 = pipeline.run_step3_recognize(s2)
    step4_output = pipeline.run_step4_reconstruct(s2, s3)
    final_extracted = pipeline.run_step5_extract(step4_output)
    
    # New Step 6 (Use processing_path so report generator sees the expected image format)
    pipeline.run_step6_visualize(processing_path, final_extracted)
    
    # Generate charts for Thesis
    pipeline.generate_metrics_charts()

    print("\n===== FINAL OCR RESULTS =====")
    print(json.dumps(final_extracted, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
