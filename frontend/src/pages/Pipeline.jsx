import React, { useState } from 'react';
import PageHeader from '../components/PageHeader';
import { Badge, Button } from '../components/UI';
import styles from './Pipeline.module.css';

const STAGES = [
  { id: '01', name: 'normalizer', desc: 'Name and identifier normalization', status: 'healthy', avgMs: 12 },
  { id: '02', name: 'sanctions_fetcher', desc: 'OFAC and UN list ingestion', status: 'healthy', avgMs: 84 },
  { id: '03', name: 'country_risk', desc: 'Jurisdiction risk classification', status: 'healthy', avgMs: 6 },
  { id: '04', name: 'screener', desc: 'Entity matching engine', status: 'slow', avgMs: 340 },
  { id: '05', name: 'risk_scorer', desc: 'Composite risk score generation', status: 'healthy', avgMs: 22 },
  { id: '06', name: 'resolver', desc: 'Case creation and final status', status: 'healthy', avgMs: 18 },
];

const STATUS_VARIANT = { healthy: 'success', slow: 'warn', error: 'danger', idle: 'neutral' };

export default function Pipeline() {
  const [refreshed, setRefreshed] = useState(false);

  function handleRefresh() {
    setRefreshed(true);
    setTimeout(() => setRefreshed(false), 1200);
  }

  return (
    <div>
      <PageHeader
        title="Pipeline Status"
        sub="Operational view of the async worker stages used during screening."
        action={
          <Button size="sm" onClick={handleRefresh}>
            {refreshed ? 'Refreshed' : 'Refresh'}
          </Button>
        }
      />

      <div className={styles.grid}>
        <div className={styles.panel}>
          <div className={styles.panelHead}>
            <span className={styles.panelTitle}>Worker stages</span>
            <span className={styles.mono}>Redis / RQ</span>
          </div>
          <div className={styles.stageList}>
            {STAGES.map(s => (
              <div key={s.id} className={styles.stageRow}>
                <div className={styles.stageNum}>{s.id}</div>
                <div className={styles.stageInfo}>
                  <div className={styles.stageName}>{s.name}</div>
                  <div className={styles.stageDesc}>{s.desc}</div>
                </div>
                <div className={styles.stageRight}>
                  <Badge variant={STATUS_VARIANT[s.status]}>{s.status}</Badge>
                  <span className={`${styles.stageMs} ${s.avgMs > 200 ? styles.slow : ''}`}>
                    avg {s.avgMs}ms
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className={styles.panel}>
          <div className={styles.panelHead}>
            <span className={styles.panelTitle}>Pipeline flow</span>
          </div>
          <div className={styles.flow}>
            <FlowBox label="POST /ingest" sub="FastAPI" color="blue" />
            <Arrow />
            <FlowBox label="PostgreSQL" sub="Entities persisted" color="gray" />
            <Arrow />
            <FlowBox label="Redis Queue" sub="Job enqueued" color="amber" />
            <Arrow />
            <div className={styles.workerBox}>
              <div className={styles.workerLabel}>Worker Pipeline</div>
              {['normalizer', 'sanctions_fetcher', 'screener', 'risk_scorer', 'resolver'].map((s, i, a) => (
                <React.Fragment key={s}>
                  <div className={styles.workerStage}>{s}</div>
                  {i < a.length - 1 && <div className={styles.miniArrow}>then</div>}
                </React.Fragment>
              ))}
            </div>
            <Arrow />
            <FlowBox label="PostgreSQL" sub="Results saved" color="gray" />
            <Arrow />
            <FlowBox label="GET /jobs/{id}" sub="FastAPI" color="blue" />
          </div>
        </div>
      </div>

      <div className={`${styles.panel} ${styles.infraPanel}`}>
        <div className={styles.panelHead}>
          <span className={styles.panelTitle}>Infrastructure</span>
        </div>
        <div className={styles.infraGrid}>
          {[
            { layer: 'Framework', tech: 'FastAPI', status: 'healthy' },
            { layer: 'Database', tech: 'PostgreSQL + asyncpg', status: 'healthy' },
            { layer: 'Job Queue', tech: 'Redis + RQ', status: 'healthy' },
            { layer: 'Worker', tech: 'RQ ingestion worker', status: 'healthy' },
          ].map(r => (
            <div key={r.layer} className={styles.infraRow}>
              <span className={styles.infraLayer}>{r.layer}</span>
              <span className={styles.infraTech}>{r.tech}</span>
              <Badge variant={STATUS_VARIANT[r.status]}>{r.status}</Badge>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function FlowBox({ label, sub, color }) {
  const colors = {
    blue: { bg: 'var(--info-bg)', text: 'var(--info)', border: 'var(--info-border)' },
    gray: { bg: 'var(--surface2)', text: 'var(--text2)', border: 'var(--border)' },
    amber: { bg: 'var(--warn-bg)', text: 'var(--warn)', border: 'var(--warn-border)' },
  };
  const c = colors[color] || colors.gray;

  return (
    <div
      className={styles.flowBox}
      style={{ background: c.bg, border: `1px solid ${c.border}`, color: c.text }}
    >
      <span className={styles.flowLabel} style={{ color: c.text }}>{label}</span>
      <span className={styles.flowSub}>{sub}</span>
    </div>
  );
}

function Arrow() {
  return <div className={styles.arrow}>then</div>;
}
