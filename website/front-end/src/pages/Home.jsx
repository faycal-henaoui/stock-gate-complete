import React, { useEffect, useMemo, useState } from 'react';
import styled from 'styled-components';
import { DollarSign, Package, AlertCircle, ArrowUp, ArrowDown, Users, Clock } from 'lucide-react';
import axios from 'axios';

// --- Styled Components ---

const PageContainer = styled.div`
  max-width: 1600px;
  margin: 0 auto;
  padding: 32px;
  background-color: #f8fafc;
  min-height: 100vh;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
`;

const Header = styled.div`
  margin-bottom: 32px;
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
`;

const TitleBlock = styled.div``;

const Title = styled.h1`
  font-size: 1.875rem;
  font-weight: 700;
  color: #0f172a;
  letter-spacing: -0.025em;
  margin-bottom: 8px;
`;

const Subtitle = styled.p`
  color: #64748b;
  font-size: 0.95rem;
`;

const DateBadge = styled.div`
  background: white;
  padding: 8px 16px;
  border-radius: 6px;
  border: 1px solid #e2e8f0;
  color: #475569;
  font-size: 0.875rem;
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 8px;
`;

// Stats Grid
const StatGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 24px;
  margin-bottom: 32px;

  @media (max-width: 1280px) {
    grid-template-columns: repeat(2, 1fr);
  }
  @media (max-width: 640px) {
    grid-template-columns: 1fr;
  }
`;

const StatCard = styled.div`
  background: white;
  border-radius: 12px;
  padding: 24px;
  border: 1px solid #e2e8f0;
  box-shadow: 0 1px 3px rgba(0,0,0,0.05);
  transition: transform 0.2s;

  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
  }
`;

const StatHeader = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
`;

const StatIcon = styled.div `
  width: 40px;
  height: 40px;
  border-radius: 8px;
  background-color: ${props => props.bg || '#f1f5f9'};
  color: ${props => props.color || '#64748b'};
  display: flex;
  align-items: center;
  justify-content: center;
`;

const StatLabel = styled.div`
  color: #64748b;
  font-size: 0.875rem;
  font-weight: 600;
`;

const StatValue = styled.div`
  font-size: 2rem;
  font-weight: 700;
  color: #0f172a;
  letter-spacing: -0.025em;
  margin-bottom: 8px;
`;

const StatTrend = styled.div`
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 0.875rem;
  font-weight: 500;
  color: ${props => props.positive ? '#16a34a' : '#ef4444'};
`;

// Dashboard Main Content
const ContentGrid = styled.div`
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 24px;

  @media (max-width: 1024px) {
    grid-template-columns: 1fr;
  }
`;

const ContentCard = styled.div`
  background: white;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  box-shadow: 0 1px 3px rgba(0,0,0,0.05);
  overflow: hidden;
  display: flex;
  flex-direction: column;
`;

const CardHeader = styled.div`
  padding: 20px 24px;
  border-bottom: 1px solid #f1f5f9;
  display: flex;
  justify-content: space-between;
  align-items: center;
`;

const CardTitle = styled.h3`
  font-size: 1.1rem;
  font-weight: 600;
  color: #0f172a;
`;

const CardBody = styled.div`
  padding: 24px;
  flex-grow: 1;
`;

// Mock Chart Bars
const ChartContainer = styled.div`
  height: 250px;
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 12px;
  padding-top: 20px;
`;

const BarColumn = styled.div`
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  gap: 4px;
  height: 100%;
  position: relative;
  cursor: pointer;

  &:hover > div {
    opacity: 0.9;
  }
`;

const BarBlue = styled.div`
  background-color: #3b82f6;
  border-radius: 4px;
  width: 100%;
  height: ${props => props.height}%;
  transition: height 0.5s ease;
`;

const BarSlate = styled.div`
  background-color: #cbd5e1;
  border-radius: 4px;
  width: 100%;
  height: ${props => props.height}%;
  transition: height 0.5s ease;
`;

const BarLabel = styled.div`
  text-align: center;
  font-size: 0.75rem;
  color: #94a3b8;
  margin-top: 8px;
`;

// Recent Orders Table
const Table = styled.table`
  width: 100%;
  border-collapse: collapse;
`;

const Th = styled.th`
  text-align: left;
  padding: 12px 16px;
  color: #64748b;
  font-size: 0.8rem;
  font-weight: 600;
  text-transform: uppercase;
  background-color: #f8fafc;
`;

const Td = styled.td`
  padding: 16px;
  border-bottom: 1px solid #f1f5f9;
  font-size: 0.9rem;
  color: #334155;
`;

const StatusPill = styled.span`
  display: inline-flex;
  padding: 4px 10px;
  border-radius: 9999px;
  font-size: 0.75rem;
  font-weight: 600;
  background-color: ${props => props.color === 'success' ? '#dcfce7' : props.color === 'warning' ? '#fef9c3' : '#f1f5f9'};
  color: ${props => props.color === 'success' ? '#166534' : props.color === 'warning' ? '#854d0e' : '#475569'};
`;

const Home = () => {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const loadProducts = async () => {
      try {
        setLoading(true);
        const response = await axios.get('/api/products');
        setProducts(response.data || []);
        setError('');
      } catch (err) {
        setError('Failed to load dashboard data.');
      } finally {
        setLoading(false);
      }
    };
    loadProducts();
  }, []);

  const formatCurrency = (value) => {
    const numberValue = Number(value) || 0;
    return numberValue.toLocaleString('en-US', { style: 'currency', currency: 'USD' });
  };

  const metrics = useMemo(() => {
    const totalStockValue = products.reduce((sum, p) => {
      const qty = Number(p.quantity) || 0;
      const unitPrice = Number(p.unit_price) || 0;
      const full = Number(p.full_stock_value);
      return sum + (Number.isFinite(full) ? full : qty * unitPrice);
    }, 0);
    const totalUnits = products.reduce((sum, p) => sum + (Number(p.quantity) || 0), 0);
    const lowStockCount = products.filter(p => (Number(p.quantity) || 0) <= 10).length;
    return {
      totalStockValue,
      totalUnits,
      lowStockCount,
      productCount: products.length,
    };
  }, [products]);

  const stats = [
    { label: 'Inventory Value', value: formatCurrency(metrics.totalStockValue), trend: loading ? 'Loading...' : 'Updated', positive: true, icon: DollarSign, color: '#2563eb', bg: '#eff6ff' },
    { label: 'Total Units', value: metrics.totalUnits.toLocaleString('en-US'), trend: loading ? 'Loading...' : 'In Stock', positive: true, icon: Package, color: '#f59e0b', bg: '#fefce8' },
    { label: 'Low Stock Items', value: metrics.lowStockCount.toString(), trend: metrics.lowStockCount > 0 ? 'Action Required' : 'Healthy', positive: metrics.lowStockCount === 0, icon: AlertCircle, color: '#ef4444', bg: '#fef2f2' },
    { label: 'Products', value: metrics.productCount.toString(), trend: loading ? 'Loading...' : 'Catalog Size', positive: true, icon: Users, color: '#8b5cf6', bg: '#f5f3ff' },
  ];

  const chartData = useMemo(() => {
    if (!products.length) {
      return [40, 55, 35, 70, 50, 60, 45];
    }
    const sorted = [...products].sort((a, b) => (Number(b.quantity) || 0) - (Number(a.quantity) || 0));
    const slice = sorted.slice(0, 7);
    return slice.map((p, index) => {
      const qty = Number(p.quantity) || 0;
      const max = Math.max(1, slice[0]?.quantity || 1);
      return Math.max(20, Math.round((qty / max) * 90)) || (index + 1) * 10;
    });
  }, [products]);

  return (
    <PageContainer>
        <Header>
            <TitleBlock>
                <Title>Executive Dashboard</Title>
                <Subtitle>
                  Real-time overview of inventory and financial performance.
                  {error && ` ${error}`}
                </Subtitle>
            </TitleBlock>
            <DateBadge>
                <Clock size={16} />
                {new Date().toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
            </DateBadge>
        </Header>

        <StatGrid>
            {stats.map((stat, index) => (
                <StatCard key={index}>
                    <StatHeader>
                        <StatIcon bg={stat.bg} color={stat.color}>
                            <stat.icon size={20} />
                        </StatIcon>
                        <StatTrend positive={stat.positive}>
                            {stat.positive ? <ArrowUp size={16} /> : <ArrowDown size={16} />}
                            {stat.trend}
                        </StatTrend>
                    </StatHeader>
                    <StatLabel>{stat.label}</StatLabel>
                    <StatValue>{stat.value}</StatValue>
                </StatCard>
            ))}
        </StatGrid>

        <ContentGrid>
            {/* Main Chart */}
            <ContentCard>
                <CardHeader>
                    <CardTitle>Revenue Analytics (2024)</CardTitle>
                </CardHeader>
                <CardBody>
                    <ChartContainer>
                        {['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].map((day, i) => (
                            <BarColumn key={day}>
                                <BarSlate height={100 - chartData[i]} style={{opacity: 0.3}} />
                                <BarBlue height={chartData[i]} />
                                <BarLabel>{day}</BarLabel>
                            </BarColumn>
                        ))}
                    </ChartContainer>
                </CardBody>
            </ContentCard>

            {/* Simple Recent Activity Table */}
            <ContentCard>
                <CardHeader>
                    <CardTitle>Recent Orders</CardTitle>
                </CardHeader>
                 <div style={{overflowX: 'auto'}}>
                    <Table>
                        <thead>
                            <tr>
                                <Th>Order ID</Th>
                                <Th>Status</Th>
                                <Th style={{textAlign:'right'}}>Amount</Th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <Td><span style={{fontFamily:'monospace'}}>#ORD-001</span></Td>
                                <Td><StatusPill color="success">Completed</StatusPill></Td>
                                <Td style={{textAlign:'right', fontWeight:600}}>$1,200.00</Td>
                            </tr>
                            <tr>
                                <Td><span style={{fontFamily:'monospace'}}>#ORD-002</span></Td>
                                <Td><StatusPill color="warning">Pending</StatusPill></Td>
                                <Td style={{textAlign:'right', fontWeight:600}}>$850.50</Td>
                            </tr>
                            <tr>
                                <Td><span style={{fontFamily:'monospace'}}>#ORD-003</span></Td>
                                <Td><StatusPill color="success">Completed</StatusPill></Td>
                                <Td style={{textAlign:'right', fontWeight:600}}>$2,100.00</Td>
                            </tr>
                             <tr>
                                <Td><span style={{fontFamily:'monospace'}}>#ORD-004</span></Td>
                                <Td><StatusPill color="default">Processing</StatusPill></Td>
                                <Td style={{textAlign:'right', fontWeight:600}}>$450.00</Td>
                            </tr>
                             <tr>
                                <Td><span style={{fontFamily:'monospace'}}>#ORD-005</span></Td>
                                <Td><StatusPill color="success">Completed</StatusPill></Td>
                                <Td style={{textAlign:'right', fontWeight:600}}>$980.00</Td>
                            </tr>
                        </tbody>
                    </Table>
                </div>
            </ContentCard>
        </ContentGrid>
    </PageContainer>
  );
};

export default Home;
