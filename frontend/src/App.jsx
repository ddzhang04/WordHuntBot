import { useState, useEffect, useRef } from 'react'
import './App.css'

const API = 'http://localhost:5050/api'

function App() {
  const [status, setStatus] = useState('connecting...')
  const [grid, setGrid] = useState(null)
  const [results, setResults] = useState([])
  const [playing, setPlaying] = useState(false)
  const [delay, setDelay] = useState(0.3)
  const [maxWords, setMaxWords] = useState(100)
  const [capturing, setCapturing] = useState(false)
  const pollRef = useRef(null)

  // Poll status while playing
  useEffect(() => {
    if (playing) {
      pollRef.current = setInterval(async () => {
        try {
          const res = await fetch(`${API}/status`)
          const data = await res.json()
          setStatus(data.status)
          setPlaying(data.playing)
        } catch {}
      }, 500)
    } else if (pollRef.current) {
      clearInterval(pollRef.current)
    }
    return () => clearInterval(pollRef.current)
  }, [playing])

  // Initial status check
  useEffect(() => {
    const check = async () => {
      try {
        const res = await fetch(`${API}/status`)
        const data = await res.json()
        setStatus(data.status)
        if (data.grid) setGrid(data.grid)
        if (data.results?.length) setResults(data.results)
      } catch {
        setStatus('server not running')
      }
    }
    check()
    const interval = setInterval(check, 2000)
    return () => clearInterval(interval)
  }, [])

  const capture = async () => {
    setCapturing(true)
    setStatus('capturing...')
    try {
      const res = await fetch(`${API}/capture`, { method: 'POST' })
      const data = await res.json()
      if (data.error) {
        setStatus(data.error)
      } else {
        setGrid(data.grid)
        setResults(data.results)
        setStatus(`found ${data.results.length} words (${data.total_points} pts)`)
      }
    } catch {
      setStatus('capture failed')
    }
    setCapturing(false)
  }

  const play = async () => {
    setPlaying(true)
    try {
      await fetch(`${API}/play`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ delay, max_words: maxWords }),
      })
    } catch {
      setPlaying(false)
    }
  }

  const stop = async () => {
    await fetch(`${API}/stop`, { method: 'POST' })
    setPlaying(false)
    setStatus('stopped')
  }

  const totalPoints = results.reduce((sum, r) => sum + r.points, 0)

  return (
    <div className="app">
      <header>
        <h1>Word Hunt Bot</h1>
        <div className={`status ${status === 'ready' ? 'ready' : ''}`}>{status}</div>
      </header>

      <div className="main">
        <div className="left-panel">
          <div className="board">
            {[0, 1, 2, 3].map(r => (
              <div key={r} className="board-row">
                {[0, 1, 2, 3].map(c => (
                  <div key={c} className="cell">
                    {grid ? grid[r][c].toUpperCase() : '\u00B7'}
                  </div>
                ))}
              </div>
            ))}
          </div>

          <div className="controls">
            <button className="btn primary" onClick={capture} disabled={capturing || playing}>
              {capturing ? 'Capturing...' : 'Capture Board'}
            </button>
            <button className="btn success" onClick={play} disabled={!results.length || playing}>
              Play Words
            </button>
            <button className="btn danger" onClick={stop} disabled={!playing}>
              Stop
            </button>
          </div>

          <div className="settings">
            <label>
              <span>Delay (s)</span>
              <input type="number" step="0.1" min="0" value={delay} onChange={e => setDelay(Number(e.target.value))} />
            </label>
            <label>
              <span>Max words</span>
              <input type="number" min="1" value={maxWords} onChange={e => setMaxWords(Number(e.target.value))} />
            </label>
          </div>
        </div>

        <div className="right-panel">
          <div className="results-header">
            {results.length > 0 && (
              <span>{results.length} words &middot; {totalPoints} pts</span>
            )}
          </div>
          <div className="word-list">
            {results.map((r, i) => (
              <div key={i} className="word-row">
                <span className="word">{r.word}</span>
                <span className="pts">{r.points}</span>
                <span className="len">{r.word.length}L</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

export default App
