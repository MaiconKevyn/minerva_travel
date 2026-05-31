export function apiBaseUrl() {
  return import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';
}

export async function fetchCatalog() {
  const response = await fetch(`${apiBaseUrl()}/api/catalog`);

  if (!response.ok) {
    throw new Error('Nao foi possivel carregar o roteiro.');
  }

  return response.json();
}

export async function generateGuide(formData) {
  const response = await fetch(`${apiBaseUrl()}/api/generate`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || 'Nao foi possivel gerar o PDF.');
  }

  return response.json();
}

export async function parseLandmarks(message) {
  const response = await fetch(`${apiBaseUrl()}/api/landmarks/parse`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ message }),
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || 'Nao foi possivel interpretar os pontos turisticos.');
  }

  return response.json();
}

export function absoluteDownloadUrl(path) {
  if (path.startsWith('http')) {
    return path;
  }

  return `${apiBaseUrl()}${path}`;
}
