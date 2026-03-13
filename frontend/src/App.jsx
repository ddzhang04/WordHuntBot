import { useState, useEffect, useRef } from 'react'
import './App.css'

function getApi() {
  return window.pywebview?.api
}

function App() {
  const [mode, setMode] = useState('wordhunt')
  const [status, setStatus] = useState('loading...')
  const [grid, setGrid] = useState([
    ['','','',''],['','','',''],['','','',''],['','','','']
  ])
  const [anagramLetters, setAnagramLetters] = useState(['','','','','',''])
  const [results, setResults] = useState([])
  const [playing, setPlaying] = useState(false)
  const [capturing, setCapturing] = useState(false)
  const [editing, setEditing] = useState(null) // {r, c} or index

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

  const go = async () => {
    const api = getApi()
    if (!api) { setStatus('pywebview not ready'); return }

    setCapturing(true)
    let captureData
    try {
      const raw = mode === 'anagram'
        ? await api.capture_anagram()
        : await api.capture_wordhunt()
      captureData = JSON.parse(raw)
      if (captureData.error) {
        setStatus(captureData.error)
        setCapturing(false)
        return
      }
      if (mode === 'anagram') {
        setAnagramLetters(captureData.letters)
      } else {
        setGrid(captureData.grid)
      }
      setResults(captureData.results)
      setStatus(`found ${captureData.results.length} words (${captureData.total_points} pts)`)
    } catch (e) {
      setStatus('capture failed')
      setCapturing(false)
      return
    }
    setCapturing(false)

    if (!captureData.results.length) return
    const count = captureData.results.length

    setPlaying(true)
    try {
      const raw = mode === 'anagram'
        ? await api.play_anagram(0.2, count)
        : await api.play_wordhunt(0, count)
      const data = JSON.parse(raw)
      if (data.error) { setStatus(data.error); setPlaying(false) }
    } catch { setPlaying(false) }
  }

  const solve = async () => {
    const api = getApi()
    if (!api) return

    try {
      let raw
      if (mode === 'anagram') {
        raw = await api.solve_anagram(JSON.stringify(anagramLetters))
      } else {
        raw = await api.solve_wordhunt(JSON.stringify(grid))
      }
      const data = JSON.parse(raw)
      setResults(data.results)
      setStatus(`found ${data.results.length} words (${data.total_points} pts)`)

      // Auto-play
      if (!data.results.length) return
      setPlaying(true)
      try {
        const playRaw = mode === 'anagram'
          ? await api.play_anagram(0, data.results.length)
          : await api.play_wordhunt(0, data.results.length)
        const playData = JSON.parse(playRaw)
        if (playData.error) { setStatus(playData.error); setPlaying(false) }
      } catch { setPlaying(false) }
    } catch {
      setStatus('solve failed')
    }
  }

  const stop = async () => {
    const api = getApi()
    if (!api) return
    await api.stop()
    setPlaying(false)
    setStatus('stopped')
  }

  const handleCellEdit = (r, c, value) => {
    const ch = value.slice(-1).toLowerCase()
    if (ch && !/^[a-z]$/.test(ch)) return
    const newGrid = grid.map(row => [...row])
    newGrid[r][c] = ch
    setGrid(newGrid)
  }

  const handleAnagramEdit = (i, value) => {
    const ch = value.slice(-1).toLowerCase()
    if (ch && !/^[a-z]$/.test(ch)) return
    const newLetters = [...anagramLetters]
    newLetters[i] = ch
    setAnagramLetters(newLetters)
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
            <span className="card-hint">click to edit</span>
          </div>
          {isAnagram ? (
            <div className="anagram-tiles">
              {anagramLetters.map((l, i) => (
                <div key={i} className="anagram-cell editable" onClick={() => setEditing({i})}>
                  {editing?.i === i ? (
                    <input
                      className="cell-input"
                      autoFocus
                      maxLength={1}
                      value={l}
                      onChange={e => handleAnagramEdit(i, e.target.value)}
                      onBlur={() => setEditing(null)}
                      onKeyDown={e => {
                        if (e.key === 'Enter' || e.key === 'Tab') {
                          e.preventDefault()
                          setEditing(i < 5 ? {i: i + 1} : null)
                        }
                      }}
                    />
                  ) : (
                    l ? l.toUpperCase() : '\u00B7'
                  )}
                </div>
              ))}
            </div>
          ) : (
            <div className="board">
              {[0,1,2,3].map(r => (
                <div key={r} className="board-row">
                  {[0,1,2,3].map(c => (
                    <div key={c} className="cell editable" onClick={() => setEditing({r, c})}>
                      {editing?.r === r && editing?.c === c ? (
                        <input
                          className="cell-input"
                          autoFocus
                          maxLength={1}
                          value={grid[r][c]}
                          onChange={e => handleCellEdit(r, c, e.target.value)}
                          onBlur={() => setEditing(null)}
                          onKeyDown={e => {
                            if (e.key === 'Enter' || e.key === 'Tab') {
                              e.preventDefault()
                              const next = r * 4 + c + 1
                              if (next < 16) setEditing({r: Math.floor(next / 4), c: next % 4})
                              else setEditing(null)
                            }
                          }}
                        />
                      ) : (
                        grid[r][c] ? grid[r][c].toUpperCase() : '\u00B7'
                      )}
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
              onClick={go} disabled={capturing || playing}>
              {capturing ? 'Capturing...' : playing ? 'Playing...' : 'Go'}
            </button>
            <button className={`btn ${isAnagram ? 'secondary-purple' : 'secondary'}`}
              onClick={solve} disabled={capturing || playing}>
              Solve
            </button>
            <button className="btn danger" onClick={stop} disabled={!playing}>
              Stop (Esc)
            </button>
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
