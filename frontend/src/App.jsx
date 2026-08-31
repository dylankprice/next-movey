import { useState, useRef } from 'react'
import { recommend, findSimilar, uploadLetterboxdCsv } from './api'

export default function App() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [tasteVector, setTasteVector] = useState(null)
  const [tasteFileName, setTasteFileName] = useState(null)
  const [watchedIds, setWatchedIds] = useState([]) // only movies from Letterboxd
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const fileInputRef = useRef(null)

  async function runSearch(e) {
    e.preventDefault()
    if (!query.trim()) return
    setLoading(true)
    setError(null)
    try {
      const res = await recommend({ query, limit: 15, tasteVector, excludeIds: watchedIds })
      setResults(res)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  async function handleMoreLikeThis(movieId) {
    setLoading(true)
    setError(null)
    try {
      const res = await findSimilar(movieId, 15, watchedIds)
      setResults(res)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  async function handleTasteUpload(e) {
    const file = e.target.files?.[0]
    if (!file) return
    setLoading(true)
    setError(null)
    try {
      const { tasteVector: vec, watchedIds: ids } = await uploadLetterboxdCsv(file)
      setTasteVector(vec)
      setTasteFileName(file.name)
      setWatchedIds(ids)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="page">
      <h1 className="title">next-movey</h1>

      <form className="search-row" onSubmit={runSearch}>
        <input
          type="text"
          placeholder="describe what you want to watch"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <button type="submit" disabled={loading}>
          {loading ? '...' : 'search'}
        </button>
      </form>

      {error && <p className="error">error: {error}</p>}

      {results.length > 0 && (
        <ul className="results">
          {results.map((r) => (
            <li key={r.tmdb_id}>
              <span className="result-title">{r.title}</span>
              <span className="result-meta">
                {' '}
                — match {(1 - r.distance).toFixed(2)}{' '}
                <button
                  className="link-btn"
                  onClick={() => handleMoreLikeThis(r.tmdb_id)}
                >
                  [similar]
                </button>
              </span>
            </li>
          ))}
        </ul>
      )}

      <hr />

      <div className="upload-area">
        <p>
          {tasteFileName
            ? `taste profile loaded: ${tasteFileName}`
            : 'upload letterboxd ratings (.csv) to personalize results'}
        </p>
        <button onClick={() => fileInputRef.current?.click()}>
          choose file
        </button>
        <input
          ref={fileInputRef}
          type="file"
          accept=".csv"
          hidden
          onChange={handleTasteUpload}
        />
      </div>
    </div>
  )
}