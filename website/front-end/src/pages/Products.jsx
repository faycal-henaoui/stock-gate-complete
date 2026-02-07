import React, { useEffect, useMemo, useState } from 'react';
import styled from 'styled-components';
import { Search, Filter, Plus, Download, MoreHorizontal, AlertCircle, CheckCircle } from 'lucide-react';
import axios from 'axios';

const PageContainer = styled.div`
  max-width: 1600px;
  margin: 0 auto;
  padding: 32px;
  background-color: #f8fafc;
  min-height: 100vh;
  font-family: 'Inter', sans-serif;
`;

const Header = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
`;

const Title = styled.h1`
  font-size: 1.5rem;
  font-weight: 700;
  color: #0f172a;
`;

const HeaderActions = styled.div`
  display: flex;
  gap: 12px;
`;

const Button = styled.button`
  background-color: ${props => props.$primary ? '#0f172a' : 'white'};
  color: ${props => props.$primary ? 'white' : '#64748b'};
  border: 1px solid ${props => props.$primary ? '#0f172a' : '#cbd5e1'};
  padding: 8px 16px;
  border-radius: 6px;
  font-weight: 500;
  font-size: 0.875rem;
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  
  &:hover {
    background-color: ${props => props.$primary ? '#1e293b' : '#f1f5f9'};
  }
`;

const FilterBar = styled.div`
  background: white;
  padding: 16px 20px;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
  display: flex;
  gap: 16px;
  align-items: center;
  margin-bottom: 24px;
  box-shadow: 0 1px 2px rgba(0,0,0,0.05);
`;

const SearchWrapper = styled.div`
  position: relative;
  flex-grow: 1;
  max-width: 400px;

  svg {
    position: absolute;
    left: 12px;
    top: 50%;
    transform: translateY(-50%);
    color: #94a3b8;
  }
`;

const SearchInput = styled.input`
  width: 100%;
  padding: 10px 12px 10px 40px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  font-size: 0.9rem;
  color: #334155;
  transition: all 0.2s;

  &:focus {
    outline: none;
    border-color: #3b82f6;
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
  }
`;

const TableContainer = styled.div`
  background: white;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
  overflow: hidden;
`;

const Table = styled.table`
  width: 100%;
  border-collapse: collapse;
`;

const Th = styled.th`
  background-color: #f8fafc;
  color: #475569;
  font-size: 0.75rem;
  text-transform: uppercase;
  font-weight: 600;
  letter-spacing: 0.05em;
  padding: 12px 24px;
  text-align: left;
  border-bottom: 1px solid #e2e8f0;
`;

const Tr = styled.tr`
  border-bottom: 1px solid #f1f5f9;
  
  &:hover {
    background-color: #f8fafc;
  }
  
  &:last-child {
    border-bottom: none;
  }
`;

const Td = styled.td`
  padding: 16px 24px;
  font-size: 0.875rem;
  color: #334155;
`;

const Badge = styled.span`
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 12px;
  border-radius: 9999px;
  font-size: 0.75rem;
  font-weight: 600;
  background-color: ${props => props.alert ? '#fef2f2' : '#f0fdf4'};
  color: ${props => props.alert ? '#b91c1c' : '#15803d'};
  border: 1px solid ${props => props.alert ? '#fecaca' : '#bbf7d0'};
`;

const SkuText = styled.span`
  font-family: 'JetBrains Mono', 'Menlo', 'Courier New', monospace;
  color: #64748b;
  font-size: 0.8rem;
  background: #f1f5f9;
  padding: 2px 6px;
  border-radius: 4px;
`;

const Products = () => {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [query, setQuery] = useState('');

  useEffect(() => {
    const loadProducts = async () => {
      try {
        setLoading(true);
        const response = await axios.get('/api/products');
        setProducts(response.data || []);
        setError('');
      } catch (err) {
        setError('Unable to load products.');
      } finally {
        setLoading(false);
      }
    };
    loadProducts();
  }, []);

  const filteredProducts = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return products;
    return products.filter((p) => {
      const reference = (p.reference || '').toLowerCase();
      const description = (p.description || '').toLowerCase();
      const category = (p.category || '').toLowerCase();
      return reference.includes(q) || description.includes(q) || category.includes(q);
    });
  }, [products, query]);

  return (
    <PageContainer>
        <Header>
            <Title>Inventory Management</Title>
            <HeaderActions>
                <Button>
                    <Download size={16} /> Export
                </Button>
                <Button $primary>
                    <Plus size={16} /> Add Product
                </Button>
            </HeaderActions>
        </Header>

        <FilterBar>
            <SearchWrapper>
                <Search size={18} />
            <SearchInput
              placeholder="Search by SKU, Name or Category..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
            </SearchWrapper>
            <Button>
                <Filter size={16} /> All Categories
            </Button>
            <div style={{flexGrow: 1}} />
          <span style={{fontSize:'0.875rem', color:'#64748b'}}>Showing <strong>{filteredProducts.length}</strong> items</span>
        </FilterBar>

        <TableContainer>
            <Table>
                <thead>
                    <tr>
                        <Th style={{width: '50px'}}><input type="checkbox" /></Th>
                        <Th>SKU</Th>
                        <Th>Product Name</Th>
                        <Th>Category</Th>
                        <Th>Stock Level</Th>
                        <Th>Unit Price</Th>
                        <Th>Status</Th>
                        <Th style={{width: '50px'}}></Th>
                    </tr>
                </thead>
                <tbody>
                  {loading ? (
                    <Tr>
                      <Td colSpan="8" style={{textAlign: 'center', padding: '32px', color: '#64748b'}}>
                        Loading inventory...
                      </Td>
                    </Tr>
                  ) : error ? (
                    <Tr>
                      <Td colSpan="8" style={{textAlign: 'center', padding: '32px', color: '#ef4444'}}>
                        {error}
                      </Td>
                    </Tr>
                  ) : filteredProducts.length === 0 ? (
                    <Tr>
                      <Td colSpan="8" style={{textAlign: 'center', padding: '32px', color: '#64748b'}}>
                        No products found.
                      </Td>
                    </Tr>
                  ) : (
                    filteredProducts.map(p => (
                      <Tr key={p.id}>
                        <Td><input type="checkbox" /></Td>
                        <Td><SkuText>{p.reference || `ID-${p.id}`}</SkuText></Td>
                        <Td>
                          <div style={{fontWeight: 500, color:'#0f172a'}}>{p.description}</div>
                        </Td>
                        <Td>{p.category || 'General'}</Td>
                        <Td style={{fontVariantNumeric:'tabular-nums'}}>
                          <strong>{p.quantity || 0}</strong> <span style={{color:'#94a3b8'}}>{p.unit || ''}</span>
                        </Td>
                        <Td style={{fontVariantNumeric:'tabular-nums'}}>${Number(p.unit_price || 0).toFixed(2)}</Td>
                        <Td>
                          <Badge alert={(Number(p.quantity) || 0) <= 10}>
                            {(Number(p.quantity) || 0) <= 10 ? <AlertCircle size={12} /> : <CheckCircle size={12} />}
                            {(Number(p.quantity) || 0) === 0 ? 'Out of Stock' : ((Number(p.quantity) || 0) <= 10 ? 'Low Stock' : 'In Stock')}
                          </Badge>
                        </Td>
                        <Td>
                          <button style={{background:'none', border:'none', cursor:'pointer', color:'#94a3b8'}}>
                            <MoreHorizontal size={16} />
                          </button>
                        </Td>
                      </Tr>
                    ))
                  )}
                </tbody>
            </Table>
        </TableContainer>
    </PageContainer>
  );
};

export default Products;
