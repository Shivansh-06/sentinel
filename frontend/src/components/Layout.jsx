import React, { useEffect, useState } from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import styles from './Layout.module.css';

const NAV = [
  {
    section: 'Screening',
    items: [
      { to: '/', label: 'Ingest', dot: 'blue', exact: true },
      { to: '/results', label: 'Results', dot: 'green' },
      { to: '/queue', label: 'Job Queue', dot: 'amber' },
    ],
  },
  {
    section: 'Operations',
    items: [
      { to: '/pipeline', label: 'Pipeline', dot: 'gray' },
      { to: '/flags', label: 'Country Flags', dot: 'red' },
      { to: '/access-log', label: 'Access Log', dot: 'purple' },
    ],
  },
];

export default function Layout({ user, onLogout }) {
  const [open, setOpen] = useState(false);
  const [theme, setTheme] = useState(() => {
    const stored = window.localStorage.getItem('sentinel-theme');
    if (stored === 'light' || stored === 'dark') return stored;
    return window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  });

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    window.localStorage.setItem('sentinel-theme', theme);
  }, [theme]);

  const isDark = theme === 'dark';

  return (
    <div className={styles.shell}>
      <header className={styles.topbar}>
        <div className={styles.brand}>
          <ShieldIcon />
          <div>
            <div className={styles.brandName}>Sentinel</div>
            <div className={styles.brandTag}>Risk intelligence</div>
          </div>
        </div>

        <div className={styles.topRight}>
          <span className={styles.statusPill}>
            <span className={styles.statusDot} /> API ready
          </span>
          <button
            className={`${styles.themeToggle} ${isDark ? styles.themeToggleDark : ''}`}
            onClick={() => setTheme(current => current === 'dark' ? 'light' : 'dark')}
            type="button"
            aria-label={`Switch to ${isDark ? 'light' : 'dark'} mode`}
            aria-pressed={isDark}
          >
            <span className={styles.toggleTrack}>
              <span className={styles.toggleThumb} />
            </span>
            <span className={styles.toggleText}>{isDark ? 'Dark' : 'Light'}</span>
          </button>
          <a
            href="http://localhost:8000/docs"
            target="_blank"
            rel="noopener noreferrer"
            className={styles.docsButton}
          >
            API Docs
          </a>
          <span className={styles.userPill}>{user?.username || 'User'}</span>
          <button className={styles.logoutButton} onClick={onLogout} type="button">
            Logout
          </button>
          <button
            className={styles.hamburger}
            onClick={() => setOpen(o => !o)}
            aria-label="Toggle navigation"
            type="button"
          >
            {open ? 'Close' : 'Menu'}
          </button>
        </div>
      </header>

      <div className={styles.body}>
        <nav className={`${styles.sidebar} ${open ? styles.sidebarOpen : ''}`}>
          {NAV.map(({ section, items }) => (
            <div key={section}>
              <div className={styles.sectionLabel}>{section}</div>
              {items.map(({ to, label, dot, exact }) => (
                <NavLink
                  key={to}
                  to={to}
                  end={exact}
                  className={({ isActive }) =>
                    `${styles.navItem} ${isActive ? styles.active : ''}`
                  }
                  onClick={() => setOpen(false)}
                >
                  <span className={`${styles.dot} ${styles[`dot_${dot}`]}`} />
                  <span>{label}</span>
                </NavLink>
              ))}
            </div>
          ))}

          <div className={styles.sidebarFooter}>
            <div className={styles.footerLabel}>Local backend</div>
            <div className={styles.footerValue}>localhost:8000</div>
          </div>
        </nav>

        {open && (
          <button
            className={styles.backdrop}
            onClick={() => setOpen(false)}
            aria-label="Close navigation"
            type="button"
          />
        )}

        <main className={styles.main}>
          <Outlet />
        </main>
      </div>
    </div>
  );
}

function ShieldIcon() {
  return (
    <div className={styles.shieldWrap} aria-hidden="true">
      <svg width="17" height="17" viewBox="0 0 17 17" fill="none">
        <path
          d="M8.5 1.7L14 4.3V8.2C14 11.5 11.6 13.9 8.5 15.1C5.4 13.9 3 11.5 3 8.2V4.3L8.5 1.7Z"
          stroke="currentColor"
          strokeWidth="1.25"
        />
        <path
          d="M6.2 8.4L7.7 9.9L10.9 6.5"
          stroke="currentColor"
          strokeWidth="1.35"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    </div>
  );
}
