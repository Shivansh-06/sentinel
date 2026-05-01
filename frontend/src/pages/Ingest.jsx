import React, { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import PageHeader from '../components/PageHeader';
import { Button, Badge, MonoId } from '../components/UI';
import { ingestManual, ingestCSV } from '../utils/api';
import styles from './Ingest.module.css';

const COUNTRIES = [
  { code: 'IR', name: 'Iran', risk: 'high' },
  { code: 'RU', name: 'Russia', risk: 'high' },
  { code: 'KP', name: 'North Korea', risk: 'high' },
  { code: 'SY', name: 'Syria', risk: 'high' },
  { code: 'CN', name: 'China', risk: 'medium' },
  { code: 'PK', name: 'Pakistan', risk: 'medium' },
  { code: 'IN', name: 'India', risk: 'low' },
  { code: 'US', name: 'United States', risk: 'low' },
  { code: 'GB', name: 'United Kingdom', risk: 'low' },
  { code: 'DE', name: 'Germany', risk: 'low' },
  { code: 'FR', name: 'France', risk: 'low' },
  { code: 'JP', name: 'Japan', risk: 'low' },
];

const ENTITY_TYPES = ['Individual', 'Organisation', 'Vessel'];
const BLANK = { name: '', country: '', identifier: '', aliases: '', type: 'Individual' };

export default function Ingest() {
  const navigate = useNavigate();
  const fileRef = useRef();

  const [form, setForm] = useState(BLANK);
  const [errors, setErrors] = useState({});
  const [loading, setLoading] = useState(false);
  const [csvLoading, setCsvLoading] = useState(false);
  const [job, setJob] = useState(null);
  const [dragOver, setDragOver] = useState(false);

  function set(field) {
    return e => {
      setForm(f => ({ ...f, [field]: e.target.value }));
      setErrors(er => ({ ...er, [field]: null }));
    };
  }

  function validate() {
    const e = {};
    if (!form.name.trim()) e.name = 'Name is required';
    if (!form.country) e.country = 'Country is required';
    return e;
  }

  async function handleSubmit(ev) {
    ev.preventDefault();
    const e = validate();
    if (Object.keys(e).length) {
      setErrors(e);
      return;
    }

    setLoading(true);
    try {
      const data = await ingestManual({
        name: form.name.trim(),
        country: form.country,
        entity_type: form.type,
      });
      setJob(data);
      navigate(`/results?job_id=${data.job_id}`);
    } catch (err) {
      setErrors({ submit: err.message });
    } finally {
      setLoading(false);
    }
  }

  async function handleFile(file) {
    if (!file || !file.name.endsWith('.csv')) {
      setErrors({ csv: 'Please upload a valid .csv file' });
      return;
    }

    setCsvLoading(true);
    try {
      const data = await ingestCSV(file);
      setJob(data);
      navigate(`/results?job_id=${data.job_id}`);
    } catch (err) {
      setErrors({ csv: err.message });
    } finally {
      setCsvLoading(false);
    }
  }

  function clearForm() {
    setForm(BLANK);
    setErrors({});
    setJob(null);
  }

  const selectedCountry = COUNTRIES.find(c => c.code === form.country);

  return (
    <div>
      <PageHeader
        title="Ingest Entity"
        sub="Submit one entity or upload a CSV batch for sanctions screening."
        action={
          <Button variant="default" size="sm" onClick={clearForm}>
            Clear form
          </Button>
        }
      />

      <div className={styles.grid}>
        <div className={styles.panel}>
          <div className={styles.panelHead}>
            <span className={styles.panelTitle}>Entity details</span>
            <MonoId>POST /ingest/manual</MonoId>
          </div>
          <form onSubmit={handleSubmit} noValidate className={styles.form}>
            <Field label="Full name" error={errors.name}>
              <input
                type="text"
                placeholder="John Doe"
                value={form.name}
                onChange={set('name')}
                className={errors.name ? styles.inputError : ''}
              />
            </Field>

            <div className={styles.fieldRow}>
              <Field label="Country" error={errors.country}>
                <select
                  value={form.country}
                  onChange={set('country')}
                  className={errors.country ? styles.inputError : ''}
                >
                  <option value="">Select country</option>
                  {COUNTRIES.map(c => (
                    <option key={c.code} value={c.code}>
                      {c.name} ({c.code})
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="Entity type">
                <select value={form.type} onChange={set('type')}>
                  {ENTITY_TYPES.map(t => <option key={t}>{t}</option>)}
                </select>
              </Field>
            </div>

            {selectedCountry && (
              <div className={styles.countryHint}>
                <span>Country risk</span>
                <Badge
                  variant={
                    selectedCountry.risk === 'high'
                      ? 'danger'
                      : selectedCountry.risk === 'medium'
                        ? 'warn'
                        : 'success'
                  }
                >
                  {selectedCountry.risk}
                </Badge>
              </div>
            )}

            <Field label="Identifier">
              <input
                type="text"
                placeholder="PASS-12345"
                value={form.identifier}
                onChange={set('identifier')}
              />
            </Field>

            <Field label="Aliases">
              <input
                type="text"
                placeholder="Comma-separated alternate names"
                value={form.aliases}
                onChange={set('aliases')}
              />
            </Field>

            {errors.submit && <div className={styles.errorBanner}>{errors.submit}</div>}

            <div className={styles.formFooter}>
              <Button type="submit" variant="primary" loading={loading}>
                Submit for screening
              </Button>
            </div>
          </form>
        </div>

        <div className={styles.panel}>
          <div className={styles.panelHead}>
            <span className={styles.panelTitle}>Batch CSV upload</span>
            <MonoId>POST /ingest</MonoId>
          </div>
          <div className={styles.csvSection}>
            <div
              className={`${styles.dropzone} ${dragOver ? styles.dragOver : ''}`}
              onDragOver={e => { e.preventDefault(); setDragOver(true); }}
              onDragLeave={() => setDragOver(false)}
              onDrop={e => {
                e.preventDefault();
                setDragOver(false);
                handleFile(e.dataTransfer.files[0]);
              }}
              onClick={() => fileRef.current?.click()}
            >
              <input
                ref={fileRef}
                type="file"
                accept=".csv"
                style={{ display: 'none' }}
                onChange={e => handleFile(e.target.files[0])}
              />
              <span className={styles.dropIcon}>CSV</span>
              <span className={styles.dropTitle}>
                {csvLoading ? 'Uploading...' : 'Drop CSV or click to browse'}
              </span>
              <span className={styles.dropSub}>
                Required column: name. Optional columns: country, entity_type.
              </span>
            </div>

            {errors.csv && <div className={styles.errorBanner}>{errors.csv}</div>}

            <div className={styles.schemaBlock}>
              <div className={styles.schemaLabel}>Expected format</div>
              <pre className={styles.schemaPre}>
{`name,country,entity_type
John Doe,IR,Individual
Acme Corp,SY,Organisation`}
              </pre>
            </div>

            <Button
              variant="primary"
              size="sm"
              loading={csvLoading}
              onClick={() => fileRef.current?.click()}
              style={{ alignSelf: 'flex-end' }}
            >
              Upload CSV
            </Button>
          </div>
        </div>
      </div>

      {job && (
        <div className={`${styles.panel} ${styles.jobPanel}`}>
          <div className={styles.panelHead}>
            <span className={styles.panelTitle}>Job submitted</span>
            <Badge variant="info">{job.status || 'queued'}</Badge>
          </div>
          <div className={styles.jobRow}>
            <div>
              <div className={styles.jobFieldLabel}>Job ID</div>
              <MonoId>{job.job_id}</MonoId>
            </div>
            <div>
              <div className={styles.jobFieldLabel}>Entities</div>
              <span className={styles.jobFieldVal}>{job.total_records ?? job.entity_count ?? 1}</span>
            </div>
            <div>
              <div className={styles.jobFieldLabel}>Status</div>
              <Badge variant="info">{job.status}</Badge>
            </div>
            <div style={{ marginLeft: 'auto' }}>
              <Button
                variant="primary"
                size="sm"
                onClick={() => navigate(`/results?job_id=${job.job_id}`)}
              >
                View results
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function Field({ label, error, children }) {
  return (
    <div className={styles.field}>
      <label className={styles.fieldLabel}>{label}</label>
      {children}
      {error && <span className={styles.fieldError}>{error}</span>}
    </div>
  );
}
