import React from 'react';
import styles from './UI.module.css';

export function Badge({ variant = 'neutral', children }) {
  return (
    <span className={`${styles.badge} ${styles[`badge_${variant}`]}`}>
      {children}
    </span>
  );
}

export function Button({ variant = 'default', size = 'md', loading, disabled, children, ...props }) {
  return (
    <button
      className={`${styles.btn} ${styles[`btn_${variant}`]} ${styles[`btn_${size}`]}`}
      disabled={disabled || loading}
      {...props}
    >
      {loading ? <span className={styles.spinnerInline} /> : children}
    </button>
  );
}

export function RiskBar({ score }) {
  const numeric = Number(score) || 0;
  const pct = Math.min(100, Math.max(0, numeric));
  const color = pct >= 70 ? 'var(--danger)' : pct >= 40 ? 'var(--warn)' : 'var(--success)';

  return (
    <div className={styles.riskWrap}>
      <div className={styles.riskTrack}>
        <div className={styles.riskFill} style={{ width: `${pct}%`, background: color }} />
      </div>
      <span className={styles.riskNum} style={{ color }}>{pct.toFixed(1)}</span>
    </div>
  );
}

export function Spinner({ size = 20 }) {
  return (
    <span
      className={styles.spinner}
      style={{ width: size, height: size }}
      role="status"
      aria-label="Loading"
    />
  );
}

export function MetricCard({ label, value, sub, subVariant }) {
  return (
    <div className={styles.metricCard}>
      <span className={styles.metricLabel}>{label}</span>
      <span className={styles.metricValue}>{value}</span>
      {sub && (
        <span className={`${styles.metricSub} ${subVariant ? styles[`sub_${subVariant}`] : ''}`}>
          {sub}
        </span>
      )}
    </div>
  );
}

export function MonoId({ children }) {
  return <span className={styles.monoId}>{children}</span>;
}

export function EmptyState({ icon, title, sub }) {
  return (
    <div className={styles.empty}>
      {icon && <span className={styles.emptyIcon}>{icon}</span>}
      <span className={styles.emptyTitle}>{title}</span>
      {sub && <span className={styles.emptySub}>{sub}</span>}
    </div>
  );
}
