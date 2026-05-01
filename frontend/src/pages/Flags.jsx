import React, { useState, useEffect, useCallback } from 'react';
import PageHeader from '../components/PageHeader';
import { Badge, Button, MonoId, Spinner, EmptyState } from '../components/UI';
import { getFlags } from '../utils/api';
import styles from './Flags.module.css';

function countryLabel(country) {
  return country || 'Unknown country';
}

export default function Flags() {
  const [countries, setCountries] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchFlags = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getFlags();
      const byCountry = Array.isArray(data)
        ? data
        : (data.by_country ?? data.flags ?? []);

      setCountries(byCountry);
      setTotal(data.total ?? byCountry.reduce((sum, row) => sum + (row.count || 0), 0));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchFlags(); }, [fetchFlags]);

  return (
    <div>
      <PageHeader
        title="Country Flags"
        sub="Entity distribution by country from the backend flags endpoint"
        action={
          !loading && !error
            ? <Badge variant={total > 0 ? 'info' : 'success'}>{total} entities</Badge>
            : null
        }
      />

      {error && (
        <div className={styles.errorBanner}>
          {error}
          <Button size="sm" variant="ghost" onClick={fetchFlags} style={{ marginLeft: 12 }}>
            Retry
          </Button>
        </div>
      )}

      {loading ? (
        <div className={styles.center}><Spinner size={28} /></div>
      ) : countries.length === 0 && !error ? (
        <EmptyState
          title="No country data"
          sub="Country totals appear after you upload a CSV or submit an entity."
        />
      ) : (
        <div className={styles.flagList}>
          {countries.map((row, i) => (
            <div key={`${row.country ?? 'unknown'}-${i}`} className={styles.flagCard}>
              <div className={styles.flagLeft}>
                <div className={styles.flagEntity}>{countryLabel(row.country)}</div>
                <div className={styles.flagMeta}>
                  <MonoId>GET /flags</MonoId>
                </div>
              </div>

              <div className={styles.flagReason}>
                <Badge variant="info">{row.count ?? 0} entities</Badge>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
