import React, { useEffect, useMemo, useRef, useState } from 'react';
import styled from 'styled-components';
import { Upload, Plus, Trash2, Save, Calendar, User, Hash, Loader2 } from 'lucide-react';
import axios from 'axios';

const PageContainer = styled.div`
  max-width: 1200px;
  margin: 0 auto;
  padding: 32px;
  background-color: #f8fafc;
  min-height: 100vh;
  font-family: 'Inter', sans-serif;
`;

const Header = styled.div`
  margin-bottom: 24px;
`;

const PageTitle = styled.h1`
  font-size: 1.5rem;
  font-weight: 700;
  color: #0f172a;
  margin-bottom: 8px;
`;

const PageMeta = styled.div`
  font-size: 0.875rem;
  color: #64748b;
`;

const MainCard = styled.div`
  background: white;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
  overflow: hidden;
`;

const HistoryCard = styled.div`
  margin-top: 24px;
  background: white;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
  overflow: hidden;
`;

const HistoryHeader = styled.div`
  padding: 16px 24px;
  border-bottom: 1px solid #e2e8f0;
  font-weight: 600;
  color: #0f172a;
`;

const HistoryTable = styled.table`
  width: 100%;
  border-collapse: collapse;
`;

const HistoryTh = styled.th`
  text-align: left;
  padding: 12px 24px;
  font-size: 0.75rem;
  text-transform: uppercase;
  color: #64748b;
  background-color: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
`;

const HistoryTd = styled.td`
  padding: 12px 24px;
  border-bottom: 1px solid #f1f5f9;
  font-size: 0.9rem;
  color: #334155;
`;

const Toolbar = styled.div`
  background-color: #f8fafc;
  padding: 16px 24px;
  border-bottom: 1px solid #e2e8f0;
  display: flex;
  gap: 12px;
  justify-content: flex-end;
`;

const TabButton = styled.button`
  padding: 8px 16px;
  border-radius: 6px;
  font-size: 0.875rem;
  font-weight: 500;
  border: 1px solid ${props => props.active ? '#0f172a' : 'transparent'};
  background-color: ${props => props.active ? 'white' : 'transparent'};
  color: ${props => props.active ? '#0f172a' : '#64748b'};
  cursor: pointer;
  
  &:hover {
    color: #0f172a;
  }
`;

const FormSection = styled.div`
  padding: 32px;
  border-bottom: 1px solid #f1f5f9;
`;

const GridForm = styled.div`
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 24px;
  margin-bottom: 12px;
`;

const Field = styled.div``;

const Label = styled.label`
  display: block;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  color: #64748b;
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 6px;
`;

const Input = styled.input`
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  font-size: 0.9rem;
  color: #0f172a;
  
  &:focus {
    outline: none;
    border-color: #3b82f6;
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
  }
`;

// Invoice Scan Area
const ScanArea = styled.div`
  border: 2px dashed #cbd5e1;
  border-radius: 12px;
  padding: 48px;
  text-align: center;
  background-color: #f8fafc;
  cursor: pointer;
  transition: all 0.2s;
  margin: 32px;

  &:hover {
    border-color: #3b82f6;
    background-color: #eff6ff;
  }
`;

// Items Table
const ItemsTable = styled.table`
  width: 100%;
  border-collapse: collapse;
`;

const ItemTh = styled.th`
  text-align: left;
  padding: 12px 24px;
  font-size: 0.75rem;
  text-transform: uppercase;
  color: #64748b;
  background-color: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
  border-top: 1px solid #e2e8f0;
`;

const ItemTd = styled.td`
  padding: 12px 24px;
  border-bottom: 1px solid #f1f5f9;
  vertical-align: middle;
`;

const InlineInput = styled.input`
  border: 1px solid transparent;
  padding: 8px;
  border-radius: 4px;
  width: 100%;
  font-size: 0.9rem;
  background: transparent;

  &:hover {
    background: #f8fafc;
    border-color: #e2e8f0;
  }
  
  &:focus {
    background: white;
    border-color: #3b82f6;
    outline: none;
  }
`;

const ActionButton = styled.button`
  background: #0f172a;
  color: white;
  border: none;
  padding: 12px 24px;
  border-radius: 6px;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.9rem;

  &:hover {
    background: #1e293b;
  }
`;

const Footer = styled.div`
  padding: 24px 32px;
  background-color: #f8fafc;
  display: flex;
  justify-content: flex-end;
  gap: 16px;
  align-items: center;
  border-top: 1px solid #e2e8f0;
`;

const TotalDisplay = styled.div`
  text-align: right;
  margin-right: 24px;
  
  small {
    display: block;
    color: #64748b;
    font-size: 0.8rem;
  }
  strong {
    font-size: 1.5rem;
    color: #0f172a;
  }
`;


const Purchase = () => {
  const [mode, setMode] = useState('manual'); // 'manual' | 'scan'
  const [supplier, setSupplier] = useState('');
  const [reference, setReference] = useState('');
  const [orderDate, setOrderDate] = useState('');
  const [items, setItems] = useState([]);
  const [newItem, setNewItem] = useState({ description: '', quantity: '', unit_price: '', unit: '' });
  const [scanLoading, setScanLoading] = useState(false);
  const [saveLoading, setSaveLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [invoiceInfo, setInvoiceInfo] = useState(null);
  const [invoices, setInvoices] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const fileInputRef = useRef(null);

  const total = useMemo(() => {
    return items.reduce((acc, item) => acc + (Number(item.quantity) || 0) * (Number(item.unit_price) || 0), 0);
  }, [items]);

  const handleAddItem = () => {
    if (!newItem.description) {
      setError('Please enter an item description.');
      return;
    }
    const item = {
      id: Date.now(),
      description: newItem.description,
      quantity: Number(newItem.quantity) || 0,
      unit_price: Number(newItem.unit_price) || 0,
      unit: newItem.unit || '',
    };
    setItems((prev) => [...prev, item]);
    setNewItem({ description: '', quantity: '', unit_price: '', unit: '' });
    setError('');
  };

  const handleItemChange = (id, field, value) => {
    setItems((prev) => prev.map((item) => item.id === id ? { ...item, [field]: value } : item));
  };

  const handleRemoveItem = (id) => {
    setItems((prev) => prev.filter((item) => item.id !== id));
  };

  const handleScanClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    try {
      setScanLoading(true);
      setError('');
      setMessage('');
      const formData = new FormData();
      formData.append('file', file);
      const response = await axios.post('/api/upload-invoice', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      const payload = response.data?.data || response.data || {};
      const extractedItems = payload.table?.rows || payload.items || [];
      const normalized = extractedItems.map((item, index) => ({
        id: Date.now() + index,
        description: item.description || '',
        raw_description: item.description || '',
        quantity: Number(item.quantity) || 0,
        unit_price: Number(item.unit_price) || 0,
        unit: item.unit || '',
      }));
      const matchResponse = await axios.post('/api/match-products', {
        items: extractedItems.map((item) => ({ description: item.description || '' })),
      });
      const matches = matchResponse.data?.matches || [];
      const merged = normalized.map((item, index) => {
        const match = matches[index];
        if (match?.source === 'mapping' && match.match) {
          return {
            ...item,
            description: match.match.description || item.description,
            reference: match.match.reference || '',
            match_score: match.score,
            match_source: 'mapping',
            confirmed: true,
          };
        }
        if (match?.suggestions?.length) {
          const top = match.suggestions[0];
          return {
            ...item,
            suggested: top,
            suggestions: match.suggestions,
            match_score: top.score,
            match_source: 'suggestion',
          };
        }
        return item;
      });
      setItems(merged);
      setSupplier(payload.fields?.supplier_name || payload.supplier?.name || supplier);
      setReference(payload.fields?.invoice_number || payload.document?.number || reference);
      setOrderDate(normalizeInvoiceDate(payload.fields?.invoice_date || payload.document?.date) || orderDate);
      setInvoiceInfo({
        invoice_number: payload.fields?.invoice_number || payload.document?.number || '',
        supplier_name: payload.fields?.supplier_name || payload.supplier?.name || '',
        total_ttc: payload.fields?.total_ttc || payload.totals?.total_amount || '',
        invoice_date: normalizeInvoiceDate(payload.fields?.invoice_date || payload.document?.date || ''),
      });
      setMessage('Invoice processed successfully. Review and confirm items.');
      setMode('manual');
    } catch (err) {
      setError('Invoice scan failed. Please try again.');
    } finally {
      setScanLoading(false);
      event.target.value = '';
    }
  };

  const handleConfirmSuggestion = async (itemId, suggestion, rawDescription) => {
    setItems((prev) => prev.map((item) => {
      if (item.id !== itemId) return item;
      return {
        ...item,
        description: suggestion.description,
        reference: suggestion.reference || '',
        confirmed: true,
        match_source: 'confirmed',
      };
    }));

    try {
      await axios.post('/api/save-mapping', {
        supplier_name: rawDescription,
        product_id: suggestion.id,
      });
      setMessage('Mapping saved for future invoices.');
    } catch (err) {
      console.error('Failed to save mapping', err);
    }
  };

  const handleSubmit = async () => {
    if (items.length === 0) {
      setError('Please add at least one item before confirming.');
      return;
    }
    try {
      setSaveLoading(true);
      setError('');
      setMessage('');

      const invoicePayload = invoiceInfo || {
        invoice_number: reference,
        supplier_name: supplier,
        total_ttc: total.toFixed(2),
        invoice_date: normalizeInvoiceDate(orderDate),
      };

      const payloadItems = items.map((item) => ({
        description: item.description,
        quantity: item.quantity,
        unit_price: item.unit_price,
        unit: item.unit,
        reference: item.reference || '',
      }));
      await axios.post('/api/add-stock', {
        items: payloadItems,
        invoiceInfo: invoicePayload,
      });
      setMessage('Stock updated successfully.');
      await loadInvoices();
    } catch (err) {
      setError('Failed to update stock.');
    } finally {
      setSaveLoading(false);
    }
  };

  const normalizeInvoiceDate = (value) => {
    if (!value) return '';
    // Fix: Python might return DD/MM/YYYY or DD-MM-YYYY, but input type="date" needs YYYY-MM-DD
    // If it's already YYYY-MM-DD
    if (value.match(/^\d{4}-\d{2}-\d{2}$/)) return value;
    
    // Check DD/MM/YYYY or DD-MM-YYYY or DD.MM.YYYY
    const parts = value.split(/[\/\-\.]/);
    if (parts.length === 3) {
      const [p1, p2, p3] = parts;
      // Heuristic: If p1 is > 12, it's definitely day. Or if p3 is year.
      if (p3.length === 4) {
         // Assume DD-MM-YYYY
         return `${p3}-${p2.padStart(2, '0')}-${p1.padStart(2, '0')}`;
      }
      if (p1.length === 4) {
         // Assume YYYY-MM-DD (but split by / or .)
         return `${p1}-${p2.padStart(2, '0')}-${p3.padStart(2, '0')}`;
      }
    }
    return '';
  };

  const loadInvoices = async () => {
    try {
      setHistoryLoading(true);
      const response = await axios.get('/api/invoices');
      setInvoices(response.data || []);
    } catch (err) {
      setError('Unable to load invoice history.');
    } finally {
      setHistoryLoading(false);
    }
  };

  useEffect(() => {
    loadInvoices();
  }, []);

    return (
        <PageContainer>
            <Header>
                 <PageTitle>Inbound Purchase Order</PageTitle>
                 <PageMeta>Create new stock entry or scan supplier invoice.</PageMeta>
            </Header>

          {(error || message) && (
            <div
              style={{
                marginBottom: '16px',
                padding: '12px 16px',
                borderRadius: '6px',
                backgroundColor: error ? '#fef2f2' : '#f0fdf4',
                color: error ? '#b91c1c' : '#166534',
                border: `1px solid ${error ? '#fecaca' : '#bbf7d0'}`,
                fontSize: '0.875rem',
                fontWeight: 600,
              }}
            >
              {error || message}
            </div>
          )}

            <MainCard>
                <Toolbar>
                    <TabButton active={mode === 'manual'} onClick={() => setMode('manual')}>Manual Entry</TabButton>
                    <TabButton active={mode === 'scan'} onClick={() => setMode('scan')}>Scan Invoice</TabButton>
                </Toolbar>

                {mode === 'scan' ? (
                  <>
                    <ScanArea onClick={handleScanClick}>
                      {scanLoading ? (
                        <Loader2 size={48} color="#94a3b8" style={{marginBottom: 16}} />
                      ) : (
                        <Upload size={48} color="#94a3b8" style={{marginBottom: 16}} />
                      )}
                      <h3 style={{color: '#0f172a', marginBottom: 8}}>
                        {scanLoading ? 'Processing invoice...' : 'Drop Invoice PDF / Image'}
                      </h3>
                      <p style={{color: '#64748b', fontSize: '0.9rem'}}>
                        {scanLoading ? 'Wait for the infos to be extracted.' : 'System will auto-extract items using OCR'}
                      </p>
                    </ScanArea>
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept=".pdf,.png,.jpg,.jpeg"
                      style={{display: 'none'}}
                      onChange={handleFileChange}
                    />
                    {items.length > 0 && (
                      <div style={{padding: '0 32px 32px'}}>
                        <div style={{marginTop: '16px', border: '1px solid #e2e8f0', borderRadius: '8px', overflow: 'hidden'}}>
                          <ItemsTable>
                            <thead>
                              <tr>
                                <ItemTh style={{width: '40%'}}>Item Description</ItemTh>
                                <ItemTh style={{width: '15%'}}>Quantity</ItemTh>
                                <ItemTh style={{width: '15%'}}>Unit Cost</ItemTh>
                                <ItemTh style={{width: '20%'}}>Line Total</ItemTh>
                                <ItemTh style={{width: '10%'}}></ItemTh>
                              </tr>
                            </thead>
                            <tbody>
                              {items.map((item) => (
                                <tr key={item.id}>
                                  <ItemTd>
                                    <div style={{display: 'flex', flexDirection: 'column', gap: '4px'}}>
                                      <InlineInput
                                        value={item.description}
                                        onChange={(e) => handleItemChange(item.id, 'description', e.target.value)}
                                      />
                                      {item.raw_description && item.raw_description !== item.description && (
                                        <span style={{fontSize: '0.75rem', color: '#94a3b8'}}>
                                          OCR: {item.raw_description}
                                        </span>
                                      )}
                                      {item.match_source === 'mapping' && (
                                        <span style={{fontSize: '0.75rem', color: '#16a34a'}}>
                                          Mapped automatically
                                        </span>
                                      )}
                                      {!item.confirmed && item.suggested && (
                                        <div
                                          style={{
                                            display: 'flex',
                                            alignItems: 'center',
                                            justifyContent: 'space-between',
                                            gap: '8px',
                                            background: '#fef9c3',
                                            color: '#854d0e',
                                            border: '1px solid #fde68a',
                                            padding: '6px 8px',
                                            borderRadius: '6px',
                                            fontSize: '0.75rem',
                                          }}
                                        >
                                          <span>
                                            Suggested: {item.suggested.description} ({item.suggested.score}%)
                                          </span>
                                          <button
                                            onClick={() => handleConfirmSuggestion(item.id, item.suggested, item.raw_description)}
                                            style={{
                                              background: '#0f172a',
                                              color: 'white',
                                              border: 'none',
                                              padding: '4px 8px',
                                              borderRadius: '4px',
                                              cursor: 'pointer',
                                              fontSize: '0.7rem',
                                            }}
                                          >
                                            Use
                                          </button>
                                        </div>
                                      )}
                                    </div>
                                  </ItemTd>
                                  <ItemTd>
                                    <InlineInput
                                      type="number"
                                      value={item.quantity}
                                      onChange={(e) => handleItemChange(item.id, 'quantity', e.target.value)}
                                    />
                                  </ItemTd>
                                  <ItemTd>
                                    <InlineInput
                                      type="number"
                                      value={item.unit_price}
                                      onChange={(e) => handleItemChange(item.id, 'unit_price', e.target.value)}
                                    />
                                  </ItemTd>
                                  <ItemTd>
                                    <strong>${((Number(item.quantity) || 0) * (Number(item.unit_price) || 0)).toFixed(2)}</strong>
                                  </ItemTd>
                                  <ItemTd style={{textAlign: 'center'}}>
                                    <Trash2 size={16} color="#ef4444" style={{cursor:'pointer'}} onClick={() => handleRemoveItem(item.id)} />
                                  </ItemTd>
                                </tr>
                              ))}
                            </tbody>
                          </ItemsTable>
                        </div>
                        <Footer>
                          <TotalDisplay>
                            <small>Grand Total</small>
                            <strong>${total.toFixed(2)}</strong>
                          </TotalDisplay>
                          <ActionButton onClick={handleSubmit} disabled={saveLoading}>
                            {saveLoading ? <Loader2 size={18} /> : <Save size={18} />}
                            {saveLoading ? 'Saving...' : 'Confirm Order'}
                          </ActionButton>
                        </Footer>
                      </div>
                    )}
                  </>
                ) : (
                    <>
                        <FormSection>
                            <GridForm>
                                <Field>
                                    <Label><User size={14} /> Supplier</Label>
                                  <Input
                                    placeholder="Search supplier..."
                                    value={supplier}
                                    onChange={(e) => setSupplier(e.target.value)}
                                  />
                                </Field>
                                <Field>
                                    <Label><Hash size={14} /> Reference No.</Label>
                                  <Input
                                    placeholder="PO-2024-XXX"
                                    value={reference}
                                    onChange={(e) => setReference(e.target.value)}
                                  />
                                </Field>
                                <Field>
                                    <Label><Calendar size={14} /> Order Date</Label>
                                  <Input
                                    type="date"
                                    value={orderDate}
                                    onChange={(e) => setOrderDate(e.target.value)}
                                  />
                                </Field>
                            </GridForm>
                        </FormSection>

                        <div style={{minHeight: '300px'}}>
                            <ItemsTable>
                                <thead>
                                    <tr>
                                        <ItemTh style={{width: '40%'}}>Item Description</ItemTh>
                                        <ItemTh style={{width: '15%'}}>Quantity</ItemTh>
                                        <ItemTh style={{width: '15%'}}>Unit Cost</ItemTh>
                                        <ItemTh style={{width: '20%'}}>Line Total</ItemTh>
                                        <ItemTh style={{width: '10%'}}></ItemTh>
                                    </tr>
                                </thead>
                                <tbody>
                                  {items.map((item) => (
                                        <tr key={item.id}>
                                            <ItemTd>
                                        <InlineInput
                                          value={item.description}
                                          onChange={(e) => handleItemChange(item.id, 'description', e.target.value)}
                                        />
                                            </ItemTd>
                                            <ItemTd>
                                        <InlineInput
                                          type="number"
                                          value={item.quantity}
                                          onChange={(e) => handleItemChange(item.id, 'quantity', e.target.value)}
                                        />
                                            </ItemTd>
                                            <ItemTd>
                                        <InlineInput
                                          type="number"
                                          value={item.unit_price}
                                          onChange={(e) => handleItemChange(item.id, 'unit_price', e.target.value)}
                                        />
                                            </ItemTd>
                                            <ItemTd>
                                        <strong>${((Number(item.quantity) || 0) * (Number(item.unit_price) || 0)).toFixed(2)}</strong>
                                            </ItemTd>
                                            <ItemTd style={{textAlign: 'center'}}>
                                        <Trash2 size={16} color="#ef4444" style={{cursor:'pointer'}} onClick={() => handleRemoveItem(item.id)} />
                                            </ItemTd>
                                        </tr>
                                    ))}
                                  {/* New item row */}
                                    <tr>
                                        <ItemTd>
                                      <InlineInput
                                        placeholder="+ Add item..."
                                        value={newItem.description}
                                        onChange={(e) => setNewItem((prev) => ({ ...prev, description: e.target.value }))}
                                      />
                                        </ItemTd>
                                    <ItemTd>
                                      <InlineInput
                                        type="number"
                                        value={newItem.quantity}
                                        onChange={(e) => setNewItem((prev) => ({ ...prev, quantity: e.target.value }))}
                                      />
                                    </ItemTd>
                                    <ItemTd>
                                      <InlineInput
                                        type="number"
                                        value={newItem.unit_price}
                                        onChange={(e) => setNewItem((prev) => ({ ...prev, unit_price: e.target.value }))}
                                      />
                                    </ItemTd>
                                    <ItemTd>-</ItemTd>
                                    <ItemTd style={{textAlign: 'center'}}>
                                      <button
                                        onClick={handleAddItem}
                                        style={{background: 'none', border: 'none', cursor: 'pointer', color: '#0f172a'}}
                                        title="Add item"
                                      >
                                        <Plus size={16} />
                                      </button>
                                    </ItemTd>
                                    </tr>
                                </tbody>
                            </ItemsTable>
                        </div>

                        <Footer>
                            <TotalDisplay>
                                <small>Grand Total</small>
                                <strong>${total.toFixed(2)}</strong>
                            </TotalDisplay>
                          <ActionButton onClick={handleSubmit} disabled={saveLoading}>
                            {saveLoading ? <Loader2 size={18} /> : <Save size={18} />}
                            {saveLoading ? 'Saving...' : 'Confirm Order'}
                            </ActionButton>
                        </Footer>
                    </>
                )}
            </MainCard>

            <HistoryCard>
              <HistoryHeader>Invoice Purchase History</HistoryHeader>
              <div style={{overflowX: 'auto'}}>
                <HistoryTable>
                  <thead>
                    <tr>
                      <HistoryTh>Invoice No.</HistoryTh>
                      <HistoryTh>Supplier</HistoryTh>
                      <HistoryTh>Date</HistoryTh>
                      <HistoryTh style={{textAlign:'right'}}>Total</HistoryTh>
                    </tr>
                  </thead>
                  <tbody>
                    {historyLoading ? (
                      <tr>
                        <HistoryTd colSpan="4" style={{textAlign:'center', color:'#64748b'}}>
                          Loading invoices...
                        </HistoryTd>
                      </tr>
                    ) : invoices.length === 0 ? (
                      <tr>
                        <HistoryTd colSpan="4" style={{textAlign:'center', color:'#64748b'}}>
                          No invoices saved yet.
                        </HistoryTd>
                      </tr>
                    ) : (
                      invoices.map((inv) => (
                        <tr key={inv.id}>
                          <HistoryTd style={{fontFamily:'monospace'}}>{inv.invoice_number || `INV-${inv.id}`}</HistoryTd>
                          <HistoryTd>{inv.supplier_name || '—'}</HistoryTd>
                          <HistoryTd>{inv.invoice_date ? new Date(inv.invoice_date).toLocaleDateString() : '—'}</HistoryTd>
                          <HistoryTd style={{textAlign:'right', fontWeight:600}}>
                            ${(Number(inv.total_amount) || 0).toFixed(2)}
                          </HistoryTd>
                        </tr>
                      ))
                    )}
                  </tbody>
                </HistoryTable>
              </div>
            </HistoryCard>
        </PageContainer>
    );
};

export default Purchase;
