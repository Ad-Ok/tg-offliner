function isPdfSsr() {
  if (typeof window !== 'undefined') return false;
  // Nuxt 3/4: доступен useRequestEvent
  try {
    const { useRequestEvent } = require('#app');
    const event = useRequestEvent && useRequestEvent();
    if (event && event.node && event.node.req && event.node.req.url) {
      return event.node.req.url.includes('pdf=1');
    }
  } catch (e) {}
  return false;
}

export const apiBase =
  typeof window === 'undefined'
    ? 'http://app:5000'
    : 'http://localhost:5000';

// Универсальный base для media
export const mediaBase =
  typeof window !== 'undefined'
    ? 'http://localhost:5000'
    : isPdfSsr()
      ? 'http://app:5000'
      : 'http://localhost:5000';

function handleResponse(res) {
  if (!res.ok) {
    return res.text().then(text => {
      throw { response: { status: res.status, data: text } };
    });
  }
  const contentType = res.headers.get('content-type');
  if (contentType && contentType.includes('application/json')) {
    return res.json();
  }
  return res.text();
}

export const api = {
  get(path) {
    return fetch(`${apiBase}${path}`).then(handleResponse).then(data => ({ data }));
  },
  post(path, body, config = {}) {
    return fetch(`${apiBase}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...(config.headers || {}) },
      body: JSON.stringify(body),
      ...config,
    }).then(handleResponse).then(data => ({ data }));
  },
  delete(path, config = {}) {
    return fetch(`${apiBase}${path}`, {
      method: 'DELETE',
      ...(config || {}),
    }).then(handleResponse).then(data => ({ data }));
  },
  // Добавь другие методы по необходимости (put, patch и т.д.)
};