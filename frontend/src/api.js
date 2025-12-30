const API_BASE = '/api';

export async function scan() {
  const response = await fetch(`${API_BASE}/scan`, {
    method: 'POST',
  });
  if (!response.ok) throw new Error('Scan failed');
  return response.json();
}

export async function getPlan(planId) {
  const response = await fetch(`${API_BASE}/plan/${planId}`);
  if (!response.ok) throw new Error('Failed to fetch plan');
  return response.json();
}

export async function updateItems(planId, items, selectAll = null) {
  const response = await fetch(`${API_BASE}/plan/${planId}/items`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ items, select_all: selectAll }),
  });
  if (!response.ok) throw new Error('Failed to update items');
  return response.json();
}

export async function applyPlan(planId, confirmPhrase = null) {
  const response = await fetch(`${API_BASE}/plan/${planId}/apply`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ confirm_phrase: confirmPhrase }),
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Apply failed');
  }
  return response.json();
}

export async function getRun(runId) {
  const response = await fetch(`${API_BASE}/runs/${runId}`);
  if (!response.ok) throw new Error('Failed to fetch run');
  return response.json();
}

export async function getRunLogs(runId) {
  const response = await fetch(`${API_BASE}/runs/${runId}/logs`);
  if (!response.ok) throw new Error('Failed to fetch logs');
  return response.json();
}

export async function protectItem(data) {
  const response = await fetch(`${API_BASE}/protect`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!response.ok) throw new Error('Protect failed');
  return response.json();
}

export async function getDiagnostics() {
  const response = await fetch(`${API_BASE}/diagnostics`);
  if (!response.ok) throw new Error('Failed to fetch diagnostics');
  return response.json();
}

export async function getConfig() {
  const response = await fetch(`${API_BASE}/config`);
  if (!response.ok) throw new Error('Failed to fetch config');
  return response.json();
}

export async function updateConfig(configData) {
  const response = await fetch(`${API_BASE}/config`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(configData),
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to update config');
  }
  return response.json();
}

