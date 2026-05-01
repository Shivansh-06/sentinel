import React, { useEffect, useState } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import Ingest from './pages/Ingest';
import Results from './pages/Results';
import Queue from './pages/Queue';
import Pipeline from './pages/Pipeline';
import Flags from './pages/Flags';
import AccessLog from './pages/AccessLog';
import Login from './pages/Login';
import { clearStoredToken, getCurrentUser, getStoredToken } from './utils/api';

export default function App() {
  const [user, setUser] = useState(null);
  const [checkingAuth, setCheckingAuth] = useState(Boolean(getStoredToken()));

  useEffect(() => {
    if (!getStoredToken()) return;

    getCurrentUser()
      .then(data => setUser(data.user))
      .catch(() => {
        clearStoredToken();
        setUser(null);
      })
      .finally(() => setCheckingAuth(false));
  }, []);

  function handleLogout() {
    clearStoredToken();
    setUser(null);
  }

  if (checkingAuth) {
    return null;
  }

  if (!user) {
    return <Login onLogin={setUser} />;
  }

  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout user={user} onLogout={handleLogout} />}>
          <Route index element={<Ingest />} />
          <Route path="results" element={<Results />} />
          <Route path="queue" element={<Queue />} />
          <Route path="pipeline" element={<Pipeline />} />
          <Route path="flags" element={<Flags />} />
          <Route path="access-log" element={<AccessLog />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
