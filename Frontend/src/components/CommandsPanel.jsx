/**
 * src/components/CommandsPanel.jsx
 */

import { useState, useMemo } from 'react'
import { motion } from 'framer-motion'
import './CommandsPanel.css'

const COMMANDS = [
  { name:'Open App',      phrase:'"open chrome"',       icon:'◻', cat:'System'      },
  { name:'Close App',     phrase:'"close firefox"',     icon:'✕', cat:'System'      },
  { name:'Screenshot',    phrase:'"screenshot"',        icon:'◈', cat:'System'      },
  { name:'Lock Screen',   phrase:'"lock the screen"',   icon:'⊗', cat:'Security'    },
  { name:'Volume Up',     phrase:'"volume up"',         icon:'▲', cat:'Media'       },
  { name:'Volume Down',   phrase:'"volume down"',       icon:'▼', cat:'Media'       },
  { name:'Mute',          phrase:'"mute"',              icon:'○', cat:'Media'       },
  { name:'New Note',      phrase:'"new note"',          icon:'⊕', cat:'Files'       },
  { name:'Backup Files',  phrase:'"backup now"',        icon:'⏺', cat:'Files'       },
  { name:'Empty Trash',   phrase:'"empty trash"',       icon:'⊘', cat:'Files'       },
  { name:'Open Terminal', phrase:'"open terminal"',     icon:'▸', cat:'Dev'         },
  { name:'Run Script',    phrase:'"run script"',        icon:'⚙', cat:'Dev'         },
  { name:'Type Text',     phrase:'"type hello"',        icon:'⌨', cat:'Input'       },
  { name:'Zoom In',       phrase:'"zoom in"',           icon:'+', cat:'UI'          },
  { name:'Zoom Out',      phrase:'"zoom out"',          icon:'−', cat:'UI'          },
  { name:'Scroll Down',   phrase:'"scroll down"',       icon:'↓', cat:'UI'          },
  { name:'Show Desktop',  phrase:'"show desktop"',      icon:'⬜', cat:'UI'         },
  { name:'New Tab',       phrase:'"new tab"',           icon:'⊞', cat:'Browser'     },
  { name:'Close Tab',     phrase:'"close tab"',         icon:'⊟', cat:'Browser'     },
  { name:'Next Tab',      phrase:'"next tab"',          icon:'→', cat:'Browser'     },
  { name:'Focus Mode',    phrase:'"focus mode"',        icon:'◎', cat:'Productivity'},
  { name:'What Time',     phrase:'"what time"',         icon:'◷', cat:'Info'        },
]

const CATEGORIES = ['All', ...new Set(COMMANDS.map(c => c.cat))]

export default function CommandsPanel() {
  const [query, setQuery]   = useState('')
  const [catFilter, setCat] = useState('All')

  const filtered = useMemo(() =>
    COMMANDS.filter(c =>
      (catFilter === 'All' || c.cat === catFilter) &&
      (!query || c.name.toLowerCase().includes(query.toLowerCase()) ||
       c.phrase.toLowerCase().includes(query.toLowerCase()))
    ), [query, catFilter]
  )

  return (
    <div className="panel commands-panel">
      <div className="commands-header">
        <h2 className="panel-title">Command Library</h2>
        <span className="tag tag-teal">{filtered.length} commands</span>
      </div>

      {/* Search bar */}
      <div className="cmd-search-bar">
        <span className="search-icon">⌕</span>
        <input
          className="cmd-search-input"
          placeholder="Search commands or phrases..."
          value={query}
          onChange={e => setQuery(e.target.value)}
        />
        {query && (
          <button className="search-clear" onClick={() => setQuery('')}>✕</button>
        )}
      </div>

      {/* Category pills */}
      <div className="cat-row">
        {CATEGORIES.map(cat => (
          <button
            key={cat}
            className={`cat-pill ${catFilter === cat ? 'cat-active' : ''}`}
            onClick={() => setCat(cat)}
          >
            {cat}
          </button>
        ))}
      </div>

      {/* Grid */}
      <div className="cmd-grid">
        {filtered.map((cmd, i) => (
          <motion.div
            key={cmd.name}
            className="cmd-card"
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.02, duration: 0.16 }}
          >
            <div className="cmd-icon">{cmd.icon}</div>
            <div className="cmd-name">{cmd.name}</div>
            <div className="cmd-phrase">{cmd.phrase}</div>
            <div className="cmd-cat">{cmd.cat}</div>
          </motion.div>
        ))}
        {filtered.length === 0 && (
          <div className="cmd-empty">No commands match "{query}"</div>
        )}
      </div>
    </div>
  )
}
