const express = require("express");
const cors = require("cors");
const multer = require("multer");
const axios = require("axios");
const FormData = require("form-data");
const fs = require("fs");
const pool = require("./db");
const { GoogleGenerativeAI } = require("@google/generative-ai");
const { Parser } = require("json2csv");
require("dotenv").config();

const app = express();
const PORT = process.env.PORT || 5000;

// Initialize Gemini (Ensure GEMINI_API_KEY is in your .env)
const genAI = new GoogleGenerativeAI(process.env.GEMINI_API_KEY || "YOUR_API_KEY_HERE");
const model = genAI.getGenerativeModel({ model: "gemini-1.5-flash" });

app.use(cors());
app.use(express.json());

// Configure Multer for temp file usage
const upload = multer({ dest: "uploads/" });

// --- Helpers ---
const normalizeText = (text = "") =>
  text
    .toLowerCase()
    .replace(/[^a-z0-9\s]/g, " ")
    .replace(/\s+/g, " ")
    .trim();

const extractNumbers = (text = "") => {
  const matches = text.match(/\d+(?:\.\d+)?/g);
  return matches ? matches : [];
};

const levenshtein = (a = "", b = "") => {
  const m = a.length;
  const n = b.length;
  if (m === 0) return n;
  if (n === 0) return m;
  const dp = Array.from({ length: m + 1 }, () => new Array(n + 1).fill(0));
  for (let i = 0; i <= m; i += 1) dp[i][0] = i;
  for (let j = 0; j <= n; j += 1) dp[0][j] = j;
  for (let i = 1; i <= m; i += 1) {
    for (let j = 1; j <= n; j += 1) {
      const cost = a[i - 1] === b[j - 1] ? 0 : 1;
      dp[i][j] = Math.min(
        dp[i - 1][j] + 1,
        dp[i][j - 1] + 1,
        dp[i - 1][j - 1] + cost
      );
    }
  }
  return dp[m][n];
};

const similarityScore = (query, candidate) => {
  const q = normalizeText(query);
  const c = normalizeText(candidate);
  if (!q || !c) return 0;

  const distance = levenshtein(q, c);
  const maxLen = Math.max(q.length, c.length) || 1;
  const levenshteinScore = 1 - distance / maxLen;

  const qTokens = new Set(q.split(" "));
  const cTokens = new Set(c.split(" "));
  let overlap = 0;
  qTokens.forEach((token) => {
    if (cTokens.has(token)) overlap += 1;
  });
  const union = new Set([...qTokens, ...cTokens]).size || 1;
  const tokenScore = overlap / union;

  const qNums = extractNumbers(query);
  const cNums = extractNumbers(candidate);
  const hasNumberMatch = qNums.some((n) => cNums.includes(n));

  const blended = 0.6 * levenshteinScore + 0.4 * tokenScore + (hasNumberMatch ? 0.1 : 0);
  return Math.max(0, Math.min(100, Math.round(blended * 100)));
};

const ensureMappingTable = async () => {
  await pool.query(
    `CREATE TABLE IF NOT EXISTS supplier_mappings (
      id SERIAL PRIMARY KEY,
      supplier_name TEXT NOT NULL,
      supplier_name_normalized TEXT NOT NULL UNIQUE,
      product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
      supplier_id VARCHAR(100),
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );`
  );
};

const ensureInvoiceColumns = async () => {
  await pool.query(`ALTER TABLE invoices ADD COLUMN IF NOT EXISTS supplier_name TEXT;`);
  await pool.query(`ALTER TABLE invoices ADD COLUMN IF NOT EXISTS invoice_date DATE;`);
};

ensureMappingTable().catch((err) => {
  console.error("Failed to ensure mapping table:", err.message);
});

ensureInvoiceColumns().catch((err) => {
  console.error("Failed to ensure invoice columns:", err.message);
});

// --- ROUTES ---

// 1. Get Stock
app.get("/api/products", async (req, res) => {
  try {
    const result = await pool.query("SELECT * FROM products ORDER BY id DESC");
    res.json(result.rows);
  } catch (err) {
    console.error(err.message);
    res.status(500).send("Server Error");
  }
});

// 2. Upload Invoice & Extract
app.post("/api/upload-invoice", upload.single("file"), async (req, res) => {
  if (!req.file) {
    return res.status(400).json({ error: "No file uploaded" });
  }

  const filePath = req.file.path;
  const originalName = req.file.originalname;

  try {
    // 1. Prepare form data for Python API
    const formData = new FormData();
    formData.append("file", fs.createReadStream(filePath), originalName);

    // 2. Call Python API (Cloud or Local)
    const OCR_API_URL = process.env.OCR_API_URL || "http://localhost:8000/extract";
    const OCR_API_KEY = process.env.OCR_API_KEY || "test_secret_key";
    
    // Note: Python API expects multipart/form-data
    const response = await axios.post(OCR_API_URL, formData, {
      headers: {
        ...formData.getHeaders(),
        "x-api-key": OCR_API_KEY,
      },
    });

    // 3. Return Python API result to Frontend
    // The Python API returns { status: "success", data: { ... } }
    res.json(response.data);

  } catch (err) {
    console.error("Extraction API Error:", err.message);
    res.status(500).json({ error: "Failed to process invoice via OCR engine." });
  } finally {
    // Cleanup upload
    fs.unlinkSync(filePath);
  }
});

// 3. Add to Stock (Batch)
app.post("/api/add-stock", async (req, res) => {
  const { items, invoiceInfo } = req.body; // items = [{ description, qty, ... }]
  
  const client = await pool.connect();
  
  try {
    await client.query('BEGIN');

    // Optional: Save Invoice Record
    if (invoiceInfo) {
      const supplierName = invoiceInfo.supplier_name || invoiceInfo.buyer_name || null;
      const invoiceDate = invoiceInfo.invoice_date || null;
      await client.query(
        "INSERT INTO invoices (invoice_number, supplier_name, total_amount, invoice_date) VALUES ($1, $2, $3, $4)",
        [invoiceInfo.invoice_number, supplierName, parseFloat(invoiceInfo.total_ttc) || 0, invoiceDate]
      );
    }

    // Upsert items (simple version: just insert or update quantity)
    // Here we assume "description" is effectively the ID if ref is missing
    for (const item of items) {
        const qty = parseInt(item.quantity) || 0;
        const price = parseFloat(item.unit_price) || 0;
        
        // Try to verify if product exists by reference or description
        // This logic is simplified for the demo
        const check = await client.query(
            "SELECT * FROM products WHERE description = $1", 
            [item.description]
        );

        if (check.rows.length > 0) {
            // Update Stock
            const currentQty = check.rows[0].quantity;
            await client.query(
                "UPDATE products SET quantity = $1, last_updated = CURRENT_TIMESTAMP WHERE id = $2",
                [currentQty + qty, check.rows[0].id]
            );
        } else {
            // Insert New Product
            await client.query(
                "INSERT INTO products (reference, description, quantity, unit_price, unit, category) VALUES ($1, $2, $3, $4, $5, 'General')",
                [item.reference || '', item.description, qty, price, item.unit || '']
            );
        }
    }

    await client.query('COMMIT');
    res.json({ success: true, message: "Stock updated successfully" });

  } catch (err) {
    await client.query('ROLLBACK');
    console.error(err);
    res.status(500).json({ error: "Transaction failed" });
  } finally {
    client.release();
  }
});

// 6. Invoice history
app.get("/api/invoices", async (req, res) => {
  try {
    const result = await pool.query(
      "SELECT id, invoice_number, supplier_name, total_amount, invoice_date, created_at FROM invoices ORDER BY created_at DESC"
    );
    res.json(result.rows);
  } catch (err) {
    console.error(err.message);
    res.status(500).send("Server Error");
  }
});

// --- AI Helper ---
const findBestMatchWithGemini = async (invoiceItemName, candidates) => {
  if (!candidates || candidates.length === 0) return null;

  const prompt = `
    Act as a smart inventory manager.
    I have an item from an invoice: "${invoiceItemName}"
    
    Here are the possible matches from my stock database:
    ${candidates.map(c => `- ID: ${c.id} | Name: ${c.description} | Ref: ${c.reference}`).join('\n')}
    
    Task: Identify exactly which stock item corresponds to the invoice item.
    - If the invoice item is a clear match for one of the candidates (even with synonyms like "Screen" vs "Monitor"), return its ID.
    - If the invoice item is ambiguous or likely a new product not in the list, return null.
    
    Return strict JSON format:
    {
      "best_match_id": NUMBER or null,
      "confidence": NUMBER (0-100),
      "reasoning": "short explanation"
    }
  `;

  try {
    const result = await model.generateContent(prompt);
    const response = await result.response;
    let text = response.text();
    // Clean markdown if present
    text = text.replace(/```json/g, "").replace(/```/g, "").trim();
    return JSON.parse(text);
  } catch (error) {
    console.error("Gemini Error:", error.message);
    return null;
  }
};

// 4. Match OCR Items to Stock Products (Hybrid: Mapping -> Levenshtein Filter -> LLM Re-Rank)
app.post("/api/match-products", async (req, res) => {
  const { items } = req.body || {};

  if (!Array.isArray(items)) {
    return res.status(400).json({ error: "items must be an array" });
  }

  try {
    const productResult = await pool.query(
      "SELECT id, reference, description, category FROM products"
    );
    const products = productResult.rows || [];

    const matches = [];

    // Process items sequentially to avoid hitting Rate Limits (Free Tier)
    for (const item of items) {
      const description = item?.description || "";
      const normalized = normalizeText(description);

      // A. Check Explicit Mapping (Fastest, 100% Accuracy)
      if (normalized) {
        const mappingResult = await pool.query(
          `SELECT p.id, p.reference, p.description, p.category
           FROM supplier_mappings m
           JOIN products p ON p.id = m.product_id
           WHERE m.supplier_name_normalized = $1
           LIMIT 1`,
          [normalized]
        );

        if (mappingResult.rows.length > 0) {
          matches.push({
            source: "mapping",
            match: mappingResult.rows[0],
            score: 100,
            ai_reasoning: "Pre-defined manual mapping",
            suggestions: [],
          });
          continue;
        }
      }

      // B. Levenshtein Pre-Filter (Get Top 5 candidates)
      const scored = products
        .map((product) => {
          const candidate = `${product.reference || ""} ${product.description || ""}`.trim();
          return {
            ...product,
            score: similarityScore(description, candidate),
          };
        })
        .sort((a, b) => b.score - a.score)
        .slice(0, 5); // Take top 5 for the AI to consider

      // C. AI Re-Ranking (The Smart "SaaS" Feature)
      let finalMatch = null;
      let aiResponse = null;

      // Only call AI if we have candidates and the top score isn't perfect
      if (scored.length > 0 && scored[0].score < 100) {
          aiResponse = await findBestMatchWithGemini(description, scored);
          if (aiResponse && aiResponse.best_match_id) {
              finalMatch = scored.find(p => p.id === aiResponse.best_match_id);
          }
// 7. Export to CSV (For Legacy Software Integration)
app.post("/api/export-csv", (req, res) => {
  const { items } = req.body;

  if (!items || !Array.isArray(items)) {
    return res.status(400).json({ error: "No items provided" });
  }

  try {
    // Flatten the structure if "match" is nested
    const flatItems = items.map(item => ({
        original_description: item.description,
        matched_description: item.match?.description || item.description,
        matched_reference: item.match?.reference || item.reference || "",
        matched_id: item.match?.id || "",
        quantity: item.quantity,
        unit_price: item.unit_price,
        total: item.amount,
        confidence: item.score,
        source: item.source
    }));

    const fields = [
        { label: 'Original Name', value: 'original_description' },
        { label: 'Matched Name', value: 'matched_description' },
        { label: 'Reference', value: 'matched_reference' },
        { label: 'Quantity', value: 'quantity' },
        { label: 'Unit Price', value: 'unit_price' },
        { label: 'Total', value: 'total' },
        { label: 'Stock ID', value: 'matched_id' }
    ];

    const json2csvParser = new Parser({ fields });
    const csv = json2csvParser.parse(flatItems);

    res.header('Content-Type', 'text/csv');
    res.attachment('invoice_export.csv');
    return res.send(csv);

  } catch (err) {
    console.error("CSV Export Error:", err);
    res.status(500).json({ error: "Failed to generate CSV" });
  }
});

      }

      // Fallback to Levenshtein if AI fails or returns null
      if (!finalMatch) {
          finalMatch = scored[0] || null;
      }

      matches.push({
        source: aiResponse?.best_match_id ? "ai-gemini" : "suggestion",
        match: finalMatch ? {
          id: finalMatch.id,
          reference: finalMatch.reference,
          description: finalMatch.description,
          category: finalMatch.category,
        } : null,
        score: aiResponse?.confidence || finalMatch?.score || 0,
        ai_reasoning: aiResponse?.reasoning || "Mathematical similarity",
        suggestions: scored.slice(0, 3).map((s) => ({
          id: s.id,
          reference: s.reference,
          description: s.description,
          category: s.category,
          score: s.score,
        })),
      });
    }

    res.json({ matches });
  } catch (err) {
    console.error("Match Error:", err.message);
    res.status(500).json({ error: "Failed to match products" });
  }
});

// 5. Save Mapping
app.post("/api/save-mapping", async (req, res) => {
  const { supplier_name, product_id, supplier_id } = req.body || {};

  if (!supplier_name || !product_id) {
    return res.status(400).json({ error: "supplier_name and product_id are required" });
  }

  try {
    const normalized = normalizeText(supplier_name);
    await pool.query(
      `INSERT INTO supplier_mappings (supplier_name, supplier_name_normalized, product_id, supplier_id)
       VALUES ($1, $2, $3, $4)
       ON CONFLICT (supplier_name_normalized)
       DO UPDATE SET product_id = EXCLUDED.product_id, supplier_id = EXCLUDED.supplier_id`,
      [supplier_name, normalized, product_id, supplier_id || null]
    );
    res.json({ success: true });
  } catch (err) {
    console.error("Mapping Save Error:", err.message);
    res.status(500).json({ error: "Failed to save mapping" });
  }
});


app.listen(PORT, () => {
  console.log(`Backend Server running on port ${PORT}`);
});

