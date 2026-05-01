const BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1';
const TOKEN_KEY = 'sentinel-token';

export function getStoredToken() {
  return window.localStorage.getItem(TOKEN_KEY);
}

export function setStoredToken(token) {
  window.localStorage.setItem(TOKEN_KEY, token);
}

export function clearStoredToken() {
  window.localStorage.removeItem(TOKEN_KEY);
}

async function request(method, path, body, isFormData = false) {
  const opts = { method, headers: {} };
  const token = getStoredToken();

  if (token) {
    opts.headers.Authorization = `Bearer ${token}`;
  }

  if (body && !isFormData) {
    opts.headers['Content-Type'] = 'application/json';
    opts.body = JSON.stringify(body);
  } else if (isFormData) {
    opts.body = body;
  }

  const res = await fetch(`${BASE}${path}`, opts);

  if (!res.ok) {
    let msg = `HTTP ${res.status}`;
    try {
      const j = await res.json();
      msg = j.detail || j.message || msg;
    } catch (_) {}
    if (res.status === 401) {
      clearStoredToken();
    }
    throw new Error(msg);
  }

  return res.json();
}

export async function login(username, password) {
  const data = await request('POST', '/auth/login', { username, password });
  setStoredToken(data.access_token);
  return data;
}

export async function getCurrentUser() {
  return request('GET', '/auth/me');
}

export async function getLoginEvents() {
  return request('GET', '/auth/login-events');
}

export async function ingestEntities(entity) {
  return request('POST', '/ingest/manual', entity);
}

export async function ingestCSV(file) {
  const form = new FormData();
  form.append('file', file);
  return request('POST', '/ingest', form, true);
}

export async function getJobStatus(jobId) {
  return request('GET', `/jobs/${jobId}`);
}

export async function getJobSummary(jobId) {
  return request('GET', `/jobs/${jobId}/summary`);
}

export async function getJobEntities(jobId) {
  return request('GET', `/jobs/${jobId}/entities`);
}

export async function getResults(jobId) {
  const [entitiesResult, statusResult, summaryResult] = await Promise.allSettled([
    getJobEntities(jobId),
    getJobStatus(jobId),
    getJobSummary(jobId),
  ]);

  if (entitiesResult.status === 'rejected') {
    throw entitiesResult.reason;
  }

  const entities = entitiesResult.value;
  const status = statusResult.status === 'fulfilled' ? statusResult.value : {};
  const summary = summaryResult.status === 'fulfilled' ? summaryResult.value : null;

  return {
    ...entities,
    ...status,
    status: status.status || summary?.job_status || entities.status,
    summary,
  };
}

export async function getFlags() {
  return request('GET', '/flags');
}

export async function getJobs() {
  return request('GET', '/queue');
}

export async function ingestManual(data) {
  return request('POST', '/ingest/manual', data);
}
