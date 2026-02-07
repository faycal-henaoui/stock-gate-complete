import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Navbar from './components/Navbar';
import Home from './pages/Home';
import Purchase from './pages/Purchase';
import Products from './pages/Products';

import './App.css'; 

function App() {
  return (
    <Router>
      <div className="flex flex-col min-h-screen bg-white">
        <Navbar />
        <main className="flex-grow">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/products" element={<Products />} />
            <Route path="/purchase" element={<Purchase />} />
            <Route path="/contact" element={<Home />} />
          </Routes>
        </main>
        
        <footer className="bg-slate-900 text-white py-8 border-t border-slate-800">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col md:flex-row justify-between items-center gap-4">
                <div className="text-sm text-slate-400">
                    © 2024 Aquaplast Solutions. All rights reserved.
                </div>
                <div className="flex gap-6 text-sm font-medium">
                    <a href="#" className="hover:text-primary-400 transition-colors">Privacy</a>
                    <a href="#" className="hover:text-primary-400 transition-colors">Terms</a>
                    <a href="#" className="hover:text-primary-400 transition-colors">Support</a>
                </div>
            </div>
        </footer>
      </div>
    </Router>
  );
}

export default App;
