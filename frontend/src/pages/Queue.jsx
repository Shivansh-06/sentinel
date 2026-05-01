import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import PageHeader from '../components/PageHeader';
import { Badge, Button, MonoId, Spinner, EmptyState } from '../components/UI';
import { getJobs } from '../utils/api';
import styles from './Queue.module.css';

const STATUS_VARIANT = {
  processing: 'info',
  queued: 'warn',
  completed: 'success',
  failed: 'danger',
};

function elapsed(isoString) {
  if (!isoString) return '-';
  const secs = Math.max(0, Math.floor((Date.now() - new Date(isoString)) / 1000));
  if (secs < 60) return `${secs}s`;
  if (secs < 3600) return `${Math.floor(secs / 60)}m ${secs % 60}s`;
  return `${Math.floor(secs / 3600)}h ${Math.floor((secs % 3600) / 60)}m`;
}

export default function Queue() {
  const navigate = useNavigate();
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastRefresh, setLastRefresh] = useState(null);

  const fetchJobs = useCallback(async (silent = false) => {
    if (!silent) setLoading(true);
    setError(null);
    try {
      const data = await getJobs();
      setJobs(Array.isArray(data) ? data : (data.jobs ?? []));
      setLastRefresh(new Date());
    } catch (err) {
      setError(err.message);
    } finally {
      if (!silent) setLoading(false);
    }
  }, []);

  useEffect(() => { fetchJobs(); }, [fetchJobs]);

  useEffect(() => {
    const hasActive = jobs.some(j => j.status === 'processing' || j.status === 'queued');
    if (!hasActive) return;
    const timer = setTimeout(() => fetchJobs(true), 5000);
    return () => clearTimeout(timer);
  }, [jobs, fetchJobs]);

  const active = jobs.filter(j => j.status === 'processing' || j.status === 'queued').length;
  const completed = jobs.filter(j => j.status === 'completed').length;
  const failed = jobs.filter(j => j.status === 'failed').length;

  return (
    <div>
      <PageHeader
        title="Job Queue"
        sub="Recent ingestion and screening jobs"
        action={
          <div className={styles.headerActions}>
            {lastRefresh && (
              <span className={styles.lastRefresh}>
                Updated {elapsed(lastRefresh.toISOString())} ago
              </span>
            )}
            <Button size="sm" loading={loading} onClick={() => fetchJobs()}>
              Refresh
            </Button>
          </div>
        }
      />

      {!loading && !error && (
        <div className={styles.strip}>
          <div className={styles.stripItem}>
            <span className={styles.stripLabel}>Total jobs</span>
            <span className={styles.stripVal}>{jobs.length}</span>
          </div>
          <div className={styles.stripItem}>
            <span className={styles.stripLabel}>Active</span>
            <span className={styles.stripVal} style={{ color: active ? 'var(--info)' : undefined }}>
              {active}
            </span>
          </div>
          <div className={styles.stripItem}>
            <span className={styles.stripLabel}>Completed</span>
            <span className={styles.stripVal} style={{ color: completed ? 'var(--success)' : undefined }}>
              {completed}
            </span>
          </div>
          <div className={styles.stripItem}>
            <span className={styles.stripLabel}>Failed</span>
            <span className={styles.stripVal} style={{ color: failed ? 'var(--danger)' : undefined }}>
              {failed}
            </span>
          </div>
        </div>
      )}

      {error && <div className={styles.errorBanner}>{error}</div>}

      <div className={styles.panel}>
        {loading ? (
          <div className={styles.center}><Spinner size={28} /></div>
        ) : jobs.length === 0 ? (
          <EmptyState
            title="No jobs yet"
            sub="Jobs appear here after you submit entities for screening."
          />
        ) : (
          <div className={styles.tableWrap}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>Job ID</th>
                  <th>Records</th>
                  <th>Processed</th>
                  <th>Status</th>
                  <th>Error</th>
                  <th>Submitted</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {jobs.map(j => (
                  <tr key={j.job_id}>
                    <td><MonoId>{j.job_id}</MonoId></td>
                    <td><span className={styles.count}>{j.total_records ?? 0}</span></td>
                    <td><span className={styles.count}>{j.processed_records ?? 0}</span></td>
                    <td>
                      <Badge variant={STATUS_VARIANT[j.status] ?? 'neutral'}>
                        {j.status === 'processing' && <span className={styles.processingDot} />}
                        {j.status || 'unknown'}
                      </Badge>
                    </td>
                    <td>
                      <span className={styles.entityName}>{j.error_message || '-'}</span>
                    </td>
                    <td><MonoId>{j.created_at ? `${elapsed(j.created_at)} ago` : '-'}</MonoId></td>
                    <td>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => navigate(`/results?job_id=${j.job_id}`)}
                      >
                        Results
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
