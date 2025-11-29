import React from 'react';
import { Routes, Route, NavLink } from 'react-router-dom';
import Config from './pages/Config';
import Search from './pages/Search';

function App() {
  return (
    <div className="app">
      <nav className="navbar">
        <div className="nav-brand">🔐 Wyplaty Excel Google</div>
        <div className="nav-links">
          <NavLink to="/" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
            Config
          </NavLink>
          <NavLink to="/search" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
            Search
          </NavLink>
        </div>
      </nav>
      <main className="main-content">
        <Routes>
          <Route path="/" element={<Config />} />
          <Route path="/search" element={<Search />} />
        </Routes>
      </main>
    </div>
  );
}

export default App;
