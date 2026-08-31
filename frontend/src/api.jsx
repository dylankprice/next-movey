// Base URL of your FastAPI backend. Override with a .env file
// (VITE_API_BASE=http://localhost:8000) if it ever runs elsewhere.
const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

async function handle(res) {
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`${res.status} ${res.statusText}: ${text}`)
  }
  return res.json()
}

export async function recommend({ query, limit = 10, tasteVector = null }) {
  const res = await fetch(`${API_BASE}/recommend`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      query,
      limit,
      taste_vector: tasteVector,
    }),
  })
  return handle(res)
}

export async function findSimilar(movieId, limit = 10) {
  const res = await fetch(`${API_BASE}/similar/${movieId}?limit=${limit}`, {
    method: 'POST',
  })
  return handle(res)
}

export async function uploadLetterboxdCsv(file) {
  const formData = new FormData()
  formData.append('file', file)
  const res = await fetch(`${API_BASE}/upload_file/`, {
    method: 'POST',
    body: formData,
  })
  const data = await handle(res)
  return data.taste_vector
}