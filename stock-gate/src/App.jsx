import { useState, useRef } from 'react';
import axios from 'axios';
import { UploadCloud, CheckCircle, Download, RefreshCw, Loader2, Boxes } from 'lucide-react';
import './App.css';

const API_BASE = 'http://localhost:5000/api';

function App() {
  const [status, setStatus] = useState('idle'); // idle, uploading, analyzing, success, error
  const [matchedData, setMatchedData] = useState([]);
  const [matchStats, setMatchStats] = useState({ total: 0, mapped: 0, ai: 0 });
  const [errorMsg, setErrorMsg] = useState('');
  const fileInputRef = useRef(null);

  const handleFileSelect = (e) => {
    const selected = e.target.files[0];
    if (selected) processFile(selected);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    const dropped = e.dataTransfer.files[0];
    if (dropped) processFile(dropped);
  };

  const processFile = async (currentFile) => {
    setStatus('uploading');
    setErrorMsg('');
    
    const formData = new FormData();
    formData.append('file', currentFile);

    try {
      // Step 1: Upload & OCR
      const uploadRes = await axios.post(`${API_BASE}/upload-invoice`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });

      // The backend returns the raw extraction data. 
      // Python API structure: { status: "success", data: { table: { rows: [...] } } }
      const apiData = uploadRes.data.data || uploadRes.data;
      const rawItems = apiData.items || apiData.table?.rows || [];
      
      if (!rawItems || !Array.isArray(rawItems) || rawItems.length === 0) {
        throw new Error('No items found in the invoice.');
      }

      setStatus('analyzing');

      // Step 2: Smart Matching (AI + Fuzzy)
      const matchRes = await axios.post(`${API_BASE}/match-products`, {
        items: rawItems
      });

      const matches = matchRes.data.matches;
      setMatchedData(matches);
      
      // Calculate Stats
      const perfect = matches.filter(m => m.source === 'mapping').length;
      const ai = matches.filter(m => m.source === 'ai-gemini').length;
      setMatchStats({
        total: matches.length,
        mapped: perfect,
        ai: ai
      });

      setStatus('success');
    } catch (err) {
      console.error(err);
      setStatus('error');
      setErrorMsg(err.response?.data?.error || err.message || 'Processing failed');
    }
  };

  const handleDownload = async () => {
    try {
      const response = await axios.post(`${API_BASE}/export-csv`, { items: matchedData }, {
        responseType: 'blob', // Important
      });
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `stock_gate_import_${new Date().toISOString().slice(0,10)}.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (err) {
      console.error('Download failed', err);
      alert('Failed to download CSV');
    }
  };

  const handleReset = () => {
    setStatus('idle');
    setMatchedData([]);
    setErrorMsg('');
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  return (
    <div className="layout">
      <header className="header">
        <Boxes className="logo-icon" size={48} style={{ margin: '0 auto 1rem' }} />
        <h1 className="title">StockGate</h1>
        <p className="subtitle">Enterprise Invoice Adapter & AI Bridge</p>
      </header>

      <main>
        {status === 'idle' && (
          <div 
            className="card dropzone"
            onDragOver={handleDragOver}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current.click()}
          >
            <UploadCloud size={64} color="#9ca3af" style={{ marginBottom: '1.5rem' }} />
            <h3 style={{ fontSize: '1.25rem', marginBottom: '0.5rem' }}>Drop your invoice here</h3>
            <p style={{ color: '#6b7280' }}>or click to browse local files (PDF, JPG, PNG)</p>
            <input 
              type="file" 
              ref={fileInputRef} 
              onChange={handleFileSelect} 
              style={{ display: 'none' }} 
              accept=".pdf,.jpg,.jpeg,.png"
            />
          </div>
        )}

        {(status === 'uploading' || status === 'analyzing') && (
          <div className="card processing-state">
            <Loader2 className="loader" size={48} />
            <h3 style={{ fontSize: '1.25rem' }}>
              {status === 'uploading' ? 'Extracting Data...' : 'AI Smart Matching...'}
            </h3>
            <p style={{ color: '#6b7280' }}>
              {status === 'uploading' 
                ? 'Reading text using CRNN/PaddleOCR' 
                : 'Comparing items with your stock database using Gemini 1.5'}
            </p>
          </div>
        )}

        {status === 'success' && (
          <div className="card success-state">
            <CheckCircle size={64} className="text-green-500" style={{ color: '#10b981' }} />
            <div>
              <h2 style={{ fontSize: '1.5rem', fontWeight: '600' }}>Processing Complete</h2>
              <p style={{ color: '#6b7280' }}>Your invoice has been converted and matched.</p>
            </div>
            
            <div className="stats-grid">
              <div className="stat-item">
                <span className="stat-label">Items Processed</span>
                <div className="stat-value">{matchStats.total}</div>
              </div>
              <div className="stat-item">
                <span className="stat-label">AI Matches</span>
                <div className="stat-value">{matchStats.ai}</div>
              </div>
            </div>

            <div className="actions">
              <button className="btn btn-primary" onClick={handleDownload}>
                <Download size={20} />
                Download CSV
              </button>
              <button className="btn btn-outline" onClick={handleReset}>
                <RefreshCw size={20} />
                Process Another
              </button>
            </div>
          </div>
        )}

        {status === 'error' && (
          <div className="card">
            <h3 style={{ color: '#ef4444', marginBottom: '1rem' }}>Processing Error</h3>
            <p>{errorMsg}</p>
            <button className="btn btn-outline" onClick={handleReset} style={{ marginTop: '1.5rem' }}>
              Try Again
            </button>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
