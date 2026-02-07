import React from 'react';
import styled from 'styled-components';
import { Link, useLocation } from 'react-router-dom';
import { LayoutDashboard, Package, ShoppingCart, Activity } from 'lucide-react';

const Nav = styled.nav`
  background: white;
  border-bottom: 1px solid #e1e4e8;
  position: sticky;
  top: 0;
  z-index: 100;
  height: 70px;
  display: flex;
  align-items: center;
  box-shadow: 0 2px 4px rgba(0,0,0,0.02);
`;

const Container = styled.div`
  max-width: 1400px;
  margin: 0 auto;
  width: 100%;
  padding: 0 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
`;

const Brand = styled(Link)`
  display: flex;
  align-items: center;
  gap: 12px;
  text-decoration: none;
`;

const LogoIcon = styled.div`
  background-color: #0f172a;
  color: white;
  padding: 8px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
`;

const BrandText = styled.div`
  display: flex;
  flex-direction: column;
`;

const BrandName = styled.span`
  font-size: 1.1rem;
  font-weight: 700;
  color: #0f172a;
  letter-spacing: -0.5px;
  line-height: 1.2;
`;

const BrandSub = styled.span`
  font-size: 0.7rem;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 1px;
`;

const Menu = styled.div`
  display: flex;
  gap: 8px;
  align-items: center;
`;

const MenuItem = styled(Link)`
  text-decoration: none;
  color: ${props => props.$active ? '#0ea5e9' : '#64748b'};
  background-color: ${props => props.$active ? '#f0f9ff' : 'transparent'};
  font-weight: 600;
  font-size: 0.9rem;
  padding: 8px 16px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  gap: 8px;
  transition: all 0.2s;

  &:hover {
    color: #0ea5e9;
    background-color: #f0f9ff;
  }
`;

const Navbar = () => {
  const location = useLocation();
  // Simple check for active path (exact match mainly)
  const isActive = (path) => location.pathname === path;

  return (
    <Nav>
      <Container>
        <Brand to="/">
            <LogoIcon>
                <Activity size={20} />
            </LogoIcon>
            <BrandText>
                <BrandName>AQUAPLAST</BrandName>
                <BrandSub>Management</BrandSub>
            </BrandText>
        </Brand>

        <Menu>
            <MenuItem to="/" $active={isActive('/')}>
                <LayoutDashboard size={18} />
                Dashboard
            </MenuItem>
            <MenuItem to="/products" $active={isActive('/products')}>
                <Package size={18} />
                Stock Inventory
            </MenuItem>
            <MenuItem to="/purchase" $active={isActive('/purchase')}>
                <ShoppingCart size={18} />
                Purchase / Inbound
            </MenuItem>
        </Menu>

        <div style={{width: '40px'}}></div> 
      </Container>
    </Nav>
  );
};

export default Navbar;
