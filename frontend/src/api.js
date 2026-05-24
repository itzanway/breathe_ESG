const BASE = import.meta.env.VITE_API_URL || '';

export async function fetchSummary() {
  const r = await fetch(`${BASE}/api/summary/`);
  return r.json();
}

export async function fetchRecords(filters = {}) {
  const params = new URLSearchParams(filters).toString();
  const r = await fetch(`${BASE}/api/records/?${params}`);
  return r.json();
}

export async function fetchBatches() {
  const r = await fetch(`${BASE}/api/batches/`);
  return r.json();
}

export async function approveRecord(id, reviewer = 'analyst', note = '') {
  const r = await fetch(`${BASE}/api/records/${id}/approve/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ reviewer, note }),
  });
  return r.json();
}

export async function rejectRecord(id, reviewer = 'analyst', note = '') {
  const r = await fetch(`${BASE}/api/records/${id}/reject/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ reviewer, note }),
  });
  return r.json();
}

export async function uploadFile(source, file) {
  const fd = new FormData();
  fd.append('file', file);
  const r = await fetch(`${BASE}/api/ingest/${source}/`, {
    method: 'POST',
    body: fd,
  });
  return r.json();
}
