import React, { useState, useEffect, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import PageHeader from '../components/PageHeader';
import { Badge, Button, RiskBar, MonoId, Spinner, EmptyState } from '../components/UI';
import { getResults } from '../utils/api';
import styles from './Results.module.css';

const RISK_VARIANT = {
  critical: 'danger',
  high: 'danger',
  medium: 'warn',
  low: 'success',
};

const STATUS_VARIANT = {
  completed: 'success',
  failed: 'danger',
  processing: 'info',
  queued: 'warn',
};

function displayName(entity) {
  return entity.normalized_name || entity.raw_name || 'Unknown entity';
}

export default function Results() {
  const [params, setParams] = useSearchParams();
  const initialJobId = params.get('job_id') || '';
  const [jobId, setJobId] = useState(initialJobId);
  const [input, setInput] = useState(initialJobId);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [polling, setPolling] = useState(false);

  const fetchResults = useCallback(async (id, silent = false) => {
    if (!id) return;
    if (!silent) setLoading(true);
    setError(null);
    try {
      const res = await getResults(id);
      setData(res);
      setPolling(res.status === 'processing' || res.status === 'queued');
    } catch (err) {
      setError(err.message);
      setPolling(false);
    } finally {
      if (!silent) setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (initialJobId) fetchResults(initialJobId);
  }, [initialJobId, fetchResults]);

  useEffect(() => {
    if (!polling || !jobId) return;
    const timer = setTimeout(() => fetchResults(jobId, true), 3000);
    return () => clearTimeout(timer);
  }, [polling, jobId, data, fetchResults]);

  function handleLookup(e) {
    e.preventDefault();
    const id = input.trim();
    if (!id) return;
    setJobId(id);
    setParams({ job_id: id });
    fetchResults(id);
  }

  const entities = data?.entities || [];
  const summary = data?.summary;
  const totalEntities = summary?.total_entities ?? data?.total_records ?? data?.total ?? entities.length;
  const processed = summary?.processed_records ?? data?.processed_records ?? 0;
  const sanctionsMatches = summary?.sanctions_matches ?? entities.filter(e => e.sanctions_match).length;
  const openCases = summary?.open_cases ?? 0;

  return (
    <div>
      <PageHeader
        title="Screening Results"
        sub="Retrieve results for a submitted screening job"
        action={
          data && (
            <Button
              size="sm"
              onClick={() => {
                const csv = [
                  'name,normalized_name,entity_type,country,risk_score,risk_label,sanctions_match,status',
                  ...entities.map(e => [
                    e.raw_name,
                    e.normalized_name,
                    e.entity_type,
                    e.country,
                    e.risk_score,
                    e.risk_label,
                    e.sanctions_match,
                    e.status,
                  ].map(v => `"${String(v ?? '').replaceAll('"', '""')}"`).join(',')),
                ].join('\n');
                const a = document.createElement('a');
                a.href = URL.createObjectURL(new Blob([csv], { type: 'text/csv' }));
                a.download = `sentinel_${data.job_id}.csv`;
                a.click();
              }}
            >
              Export CSV
            </Button>
          )
        }
      />

      <form onSubmit={handleLookup} className={styles.lookupBar}>
        <input
          type="text"
          placeholder="Enter job ID"
          value={input}
          onChange={e => setInput(e.target.value)}
          className={styles.lookupInput}
        />
        <Button type="submit" variant="primary" loading={loading}>
          Fetch
        </Button>
      </form>

      {error && <div className={styles.errorBanner}>{error}</div>}

      {loading && !data && (
        <div className={styles.centerSpinner}><Spinner size={28} /></div>
      )}

      {data && (
        <>
          <div className={styles.jobStrip}>
            <div className={styles.stripItem}>
              <span className={styles.stripLabel}>Job ID</span>
              <MonoId>{data.job_id}</MonoId>
            </div>
            <div className={styles.stripItem}>
              <span className={styles.stripLabel}>Status</span>
              <Badge variant={STATUS_VARIANT[data.status] || 'neutral'}>
                {polling && <Spinner size={10} />}
                {data.status || 'unknown'}
              </Badge>
            </div>
            <div className={styles.stripItem}>
              <span className={styles.stripLabel}>Processed</span>
              <span className={styles.stripVal}>{processed} / {totalEntities}</span>
            </div>
            <div className={styles.stripItem}>
              <span className={styles.stripLabel}>Sanctions matches</span>
              <span className={styles.stripVal} style={{ color: sanctionsMatches ? 'var(--danger)' : undefined }}>
                {sanctionsMatches}
              </span>
            </div>
            <div className={styles.stripItem}>
              <span className={styles.stripLabel}>Open cases</span>
              <span className={styles.stripVal} style={{ color: openCases ? 'var(--warn)' : undefined }}>
                {openCases}
              </span>
            </div>
          </div>

          <div className={styles.panel}>
            {entities.length === 0 ? (
              <EmptyState
                title="No entities yet"
                sub="The job may still be processing. Results will appear once entities are available."
              />
            ) : (
              <div className={styles.tableWrap}>
                <table className={styles.table}>
                  <thead>
                    <tr>
                      <th>Entity</th>
                      <th>Type</th>
                      <th>Country</th>
                      <th>Sanctions</th>
                      <th>Risk score</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {entities.map(entity => (
                      <tr key={entity.id}>
                        <td>
                          <div className={styles.entityName}>{displayName(entity)}</div>
                          {entity.normalized_name && entity.raw_name !== entity.normalized_name && (
                            <MonoId>{entity.raw_name}</MonoId>
                          )}
                        </td>
                        <td>{entity.entity_type || '-'}</td>
                        <td>{entity.country || '-'}</td>
                        <td>
                          <Badge variant={entity.sanctions_match ? 'danger' : 'success'}>
                            {entity.sanctions_match ? 'match' : 'clear'}
                          </Badge>
                        </td>
                        <td>
                          <RiskBar score={entity.risk_score ?? 0} />
                        </td>
                        <td>
                          <Badge variant={RISK_VARIANT[entity.risk_label] || 'neutral'}>
                            {entity.risk_label || entity.status || 'pending'}
                          </Badge>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      )}

      {!data && !loading && !error && (
        <EmptyState
          title="Enter a job ID above"
          sub="After submitting an entity on the Ingest page, paste the returned job ID here to see screening results."
        />
      )}
    </div>
  );
}
