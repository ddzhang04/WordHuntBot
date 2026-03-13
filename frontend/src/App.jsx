import { useState, useEffect, useRef } from 'react'
import './App.css'

function getApi() {
  return window.pywebview?.api
}

function App() {
  const [mode, setMode] = useState('wordhunt')
  const [status, setStatus] = useState('loading...')
  const [grid, setGrid] = useState(null)
  const [anagramLetters, setAnagramLetters] = useState(null)
  const [results, setResults] = useState([])
  const [playing, setPlaying] = useState(false)
  const [delay, setDelay] = useState(0.3)
  const [maxWords, setMaxWords] = useState(100)
  const [capturing, setCapturing] = useState(false)
  const pollRef = useRef(null)

  useEffect(() => {
    const poll = setInterval(async () => {
      const api = getApi()
      if (!api) return
      try {
        const s = await api.get_status()
        setStatus(s)
        if (s === 'done!' || (!s.startsWith('playing') && playing)) {
          setPlaying(false)
        }
      } catch {}
    }, 500)
    return () => clearInterval(poll)
  }, [playing])

  const capture = async () => {
    const api = getApi()
    if (!api) { setStatus('pywebview not ready'); return }
    setCapturing(true)
    try {
      const raw = mode === 'anagram'
        ? await api.capture_anagram()
        : await api.capture_wordhunt()
      const data = JSON.parse(raw)
      if (data.error) {
        setStatus(data.error)
      } else if (mode === 'anagram') {
        setAnagramLetters(data.letters)
        setResults(data.results)
        setStatus(`found ${data.results.length} words (${data.total_points} pts)`)
      } else {
        setGrid(data.grid)
        setResults(data.results)
        setStatus(`found ${data.results.length} words (${data.total_points} pts)`)
      }
    } catch (e) {
      setStatus('capture failed')
    }
    setCapturing(false)
  }

  const play = async () => {
    const api = getApi()
    if (!api) return
    setPlaying(true)
    try {
      const raw = mode === 'anagram'
        ? await api.play_anagram(delay, maxWords)
        : await api.play_wordhunt(delay, maxWords)
      const data = JSON.parse(raw)
      if (data.error) { setStatus(data.error); setPlaying(false) }
    } catch { setPlaying(false) }
  }

  const stop = async () => {
    const api = getApi()
    if (!api) return
    await api.stop()
    setPlaying(false)
    setStatus('stopped')
  }

  const totalPoints = results.reduce((sum, r) => sum + r.points, 0)
  const isAnagram = mode === 'anagram'

  return (
    <div className={`app ${isAnagram ? 'anagram-mode' : ''}`}>
      <div className="topbar">
        <div className="topbar-left">
          <div className="logo">
            <span className={isAnagram ? 'purple' : 'green'}>
              {isAnagram ? 'Anagram' : 'WordHunt'}
            </span> Bot
          </div>
          <div className="mode-toggle">
            <button className={`mode-btn ${!isAnagram ? 'active' : ''}`}
              onClick={() => { setMode('wordhunt'); setResults([]) }}>
              Word Hunt
            </button>
            <button className={`mode-btn anagram ${isAnagram ? 'active' : ''}`}
              onClick={() => { setMode('anagram'); setResults([]) }}>
              Anagrams
            </button>
          </div>
        </div>
        <div className={`status-pill ${status === 'ready' ? 'ready' : ''}`}>{status}</div>
      </div>

      <div className="dashboard">
        <div className="card card-board">
          <div className="card-title">
            {isAnagram ? 'Letters' : 'Board'}
          </div>
          {isAnagram ? (
            <div className="anagram-tiles">
              {(anagramLetters || Array(6).fill(null)).map((l, i) => (
                <div key={i} className="anagram-cell">{l ? l.toUpperCase() : '\u00B7'}</div>
              ))}
            </div>
          ) : (
            <div className="board">
              {[0,1,2,3].map(r => (
                <div key={r} className="board-row">
                  {[0,1,2,3].map(c => (
                    <div key={c} className="cell">
                      {grid ? grid[r][c].toUpperCase() : '\u00B7'}
                    </div>
                  ))}
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="card card-controls">
          <div className="card-title">Controls</div>
          <div className="controls">
            <button className={`btn ${isAnagram ? 'primary-purple' : 'primary'}`}
              onClick={capture} disabled={capturing || playing}>
              {capturing ? 'Capturing...' : 'Capture'}
            </button>
            <button className={`btn ${isAnagram ? 'secondary-purple' : 'secondary'}`}
              onClick={play} disabled={!results.length || playing}>
              Play Words
            </button>
            <button className="btn danger" onClick={stop} disabled={!playing}>
              Stop
            </button>
            <div className="settings">
              <label>
                <span>Delay (s)</span>
                <input type="number" step="0.1" min="0" value={delay}
                  onChange={e => setDelay(Number(e.target.value))} />
              </label>
              <label>
                <span>Max words</span>
                <input type="number" min="1" value={maxWords}
                  onChange={e => setMaxWords(Number(e.target.value))} />
              </label>
            </div>
          </div>
        </div>

        <div className="card card-results">
          <div className="results-header">
            <div className="card-title" style={{marginBottom: 0}}>Results</div>
            {results.length > 0 && (
              <div className="results-stats">
                {results.length} words &middot; {totalPoints} pts
              </div>
            )}
          </div>
          {results.length > 0 ? (
            <div className="word-list">
              {results.map((r, i) => (
                <div key={i} className="word-row">
                  <span className="word">{r.word}</span>
                  <span className={`pts ${isAnagram ? 'purple' : ''}`}>{r.points}</span>
                  <span className="len">{r.word.length}L</span>
                </div>
              ))}
            </div>
          ) : (
            <div className="empty-state">
              Capture a board to see results
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default App
