import React, { useCallback, useEffect, useState } from 'react';
import PageHeader from '../components/PageHeader';
import { Badge, Button, EmptyState, MonoId, Spinner } from '../components/UI';
import { getLoginEvents } from '../utils/api';
import styles from './AccessLog.module.css';

function formatDate(value) {
  if (!value) return '-';
  return new Date(value).toLocaleString();
}

export default function AccessLog() {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchEvents = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getLoginEvents();
      setEvents(data.events || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchEvents(); }, [fetchEvents]);

  return (
    <div>
      <PageHeader
        title="Access Log"
        sub="Recent authentication attempts, including failed logins, IP addresses, and user agents."
        action={<Button size="sm" onClick={fetchEvents} loading={loading}>Refresh</Button>}
      />

      {error && <div className={styles.errorBanner}>{error}</div>}

      <div className={styles.panel}>
        {loading ? (
          <div className={styles.center}><Spinner size={28} /></div>
        ) : events.length === 0 ? (
          <EmptyState title="No login events" sub="Authentication attempts will appear here." />
        ) : (
          <div className={styles.tableWrap}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>Time</th>
                  <th>User</th>
                  <th>Status</th>
                  <th>IP</th>
                  <th>User agent</th>
                </tr>
              </thead>
              <tbody>
                {events.map(event => (
                  <tr key={event.id}>
                    <td><MonoId>{formatDate(event.created_at)}</MonoId></td>
                    <td>{event.username}</td>
                    <td>
                      <Badge variant={event.success ? 'success' : 'danger'}>
                        {event.success ? 'success' : event.failure_reason || 'failed'}
                      </Badge>
                    </td>
                    <td><MonoId>{event.ip_address || '-'}</MonoId></td>
                    <td className={styles.userAgent}>{event.user_agent || '-'}</td>
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
