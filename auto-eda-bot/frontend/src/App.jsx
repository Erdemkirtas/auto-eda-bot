import { useState, useRef, useEffect, useCallback } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism'
import { ToastContainer, showToast } from './components/Toast'
import './App.css'

const BACKEND_URL = 'http://localhost:8000'

import { fetchEventSource } from '@microsoft/fetch-event-source'
import AuthPage from './components/AuthPage'

function App() {
  // Auth State
  const [token, setToken] = useState(() => localStorage.getItem('token') || null);
  const [username, setUsername] = useState(() => localStorage.getItem('username') || '');

  // ---------------------------------------------------------------------------
  // State
  // ---------------------------------------------------------------------------
  const [messages, setMessages] = useState(() => {
    const saved = localStorage.getItem('eda_messages')
    return saved ? JSON.parse(saved) : []
  })
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [uploadedFile, setUploadedFile] = useState(() => {
    const saved = localStorage.getItem('eda_uploadedFile')
    return saved ? JSON.parse(saved) : null
  })
  const [isDarkMode, setIsDarkMode] = useState(() => {
    const saved = localStorage.getItem('eda_theme')
    return saved ? JSON.parse(saved) : true
  })
  const [dataPreview, setDataPreview] = useState(() => {
    const saved = localStorage.getItem('eda_dataPreview')
    return saved ? JSON.parse(saved) : null
  })
  const [backendOnline, setBackendOnline] = useState(false)
  const [dragover, setDragover] = useState(false)
  const [urlInput, setUrlInput] = useState('')
  const [isScraping, setIsScraping] = useState(false)
  const [sessionId, setSessionId] = useState(() => {
    const saved = localStorage.getItem('eda_sessionId')
    return saved || crypto.randomUUID()
  })
  const [streamingText, setStreamingText] = useState('')
  const [streamingSteps, setStreamingSteps] = useState([])
  const [fileList, setFileList] = useState([])
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [fullscreenChart, setFullscreenChart] = useState(null)

  useEffect(() => { localStorage.setItem('eda_messages', JSON.stringify(messages)) }, [messages])
  useEffect(() => { localStorage.setItem('eda_uploadedFile', JSON.stringify(uploadedFile)) }, [uploadedFile])
  useEffect(() => { localStorage.setItem('eda_dataPreview', JSON.stringify(dataPreview)) }, [dataPreview])
  useEffect(() => { localStorage.setItem('eda_sessionId', sessionId) }, [sessionId])

  useEffect(() => {
    localStorage.setItem('eda_theme', JSON.stringify(isDarkMode))
    if (!isDarkMode) {
      document.documentElement.classList.add('light-mode')
    } else {
      document.documentElement.classList.remove('light-mode')
    }
  }, [isDarkMode])

  const [isListening, setIsListening] = useState(false)
  const recognitionRef = useRef(null)

  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
    if (SpeechRecognition) {
      const recognition = new SpeechRecognition()
      recognition.lang = 'tr-TR'
      recognition.continuous = false
      recognition.interimResults = false
      recognition.onstart = () => setIsListening(true)
      recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript
        setInput(prev => prev + (prev ? ' ' : '') + transcript)
      }
      recognition.onerror = () => setIsListening(false)
      recognition.onend = () => setIsListening(false)
      recognitionRef.current = recognition
    }
  }, [])

  const chatEndRef = useRef(null)
  const fileInputRef = useRef(null)

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const res = await fetch(`${BACKEND_URL}/`)
        setBackendOnline(res.ok)
      } catch {
        setBackendOnline(false)
      }
    }
    checkHealth()
    const interval = setInterval(checkHealth, 10000)
    return () => clearInterval(interval)
  }, [])

  const fetchFileList = useCallback(async () => {
    if (!token) return
    try {
      const res = await fetch(`${BACKEND_URL}/api/files`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      const data = await res.json()
      setFileList(data.files || [])
    } catch {
    }
  }, [token])

  useEffect(() => {
    fetchFileList()
    const interval = setInterval(fetchFileList, 15000)
    return () => clearInterval(interval)
  }, [fetchFileList])

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isLoading, streamingText])

  const handleFileUpload = async (file) => {
    if (!file) return

    const ext = file.name.split('.').pop().toLowerCase()
    if (!['csv', 'xls', 'xlsx'].includes(ext)) {
      showToast('Sadece CSV ve Excel dosyaları desteklenir!', 'error')
      return
    }

    const formData = new FormData()
    formData.append('file', file)

    try {
      const res = await fetch(`${BACKEND_URL}/api/upload`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
        body: formData,
      })
      const data = await res.json()

      if (data.success) {
        setUploadedFile(data.file_name)
        setDataPreview({
          html: data.preview_html,
          rows: data.row_count,
          cols: data.columns.length
        })
        setMessages(prev => [...prev, {
          role: 'bot',
          content: `✅ **"${data.file_name}"** başarıyla yüklendi!\n\n- 📊 **${data.row_count}** satır, **${data.columns.length}** sütun\n\nŞimdi bana bu veri hakkında sorular sorabilirsin:\n- *"Bu veriyi analiz et"*\n- *"Eksik verileri göster"*\n- *"Sütunlar arasındaki korelasyonu çiz"*`,
          charts: [],
          html_charts: [],
          steps: []
        }])
        showToast(`${data.file_name} yüklendi!`, 'success')
        fetchFileList()
      } else {
        showToast(data.detail || 'Yükleme başarısız!', 'error')
      }
    } catch (err) {
      showToast('Backend\'e bağlanılamadı! Sunucunun çalıştığından emin olun.', 'error')
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleCopyMessage = (content) => {
    navigator.clipboard.writeText(content)
    showToast('Mesaj kopyalandı!', 'info')
  }

  const handleDownloadPDF = async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/report/pdf`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ messages })
      })
      if (res.ok) {
        const blob = await res.blob()
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = 'eda_report.pdf'
        a.click()
        window.URL.revokeObjectURL(url)
        showToast('PDF raporu indiriliyor...', 'success')
      } else {
        showToast('PDF oluşturulamadı!', 'error')
      }
    } catch {
      showToast('PDF indirme hatası!', 'error')
    }
  }

  const handleQuickAction = (prompt) => {
    setInput(prompt)
  }

  const toggleListening = () => {
    if (!recognitionRef.current) return
    if (isListening) {
      recognitionRef.current.stop()
    } else {
      recognitionRef.current.start()
    }
  }

  const handleSend = async () => {
    if (!input.trim() || isLoading) return

    const userMsg = input.trim()
    setInput('')
    setMessages(prev => [...prev, { role: 'user', content: userMsg }])
    setIsLoading(true)
    setStreamingText('')
    setStreamingSteps([])

    try {
      await fetchEventSource(`${BACKEND_URL}/api/chat/stream`, {
        method: 'POST',
        headers: { 
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          message: userMsg,
          session_id: sessionId
        }),
        onmessage(event) {
          const data = JSON.parse(event.data)
          if (data.type === 'token') {
             setStreamingText(prev => prev + data.content)
          } else if (data.type === 'done') {
             setMessages(prev => [...prev, { role: 'bot', content: data.reply }])
             setStreamingText('')
          }
        }
      })
    } catch (err) {
       showToast('Hata oluştu', 'error')
    } finally {
      setIsLoading(false)
    }
  }

  const handleLogout = () => {
    localStorage.removeItem('token')
    localStorage.removeItem('username')
    setToken(null)
    setUsername('')
    setMessages([])
    setSessionId(crypto.randomUUID())
    showToast('Çıkış yapıldı', 'info')
  }

  const handleClearChat = async () => {
    setMessages([])
    setUploadedFile(null)
    setDataPreview(null)
    const newSessionId = crypto.randomUUID()
    setSessionId(newSessionId)
    try {
      await fetch(`${BACKEND_URL}/api/reset`, { 
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      })
    } catch { /* */ }
    showToast('Sohbet temizlendi.', 'info')
  }

  const handleDeleteFile = async (filename) => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/files/${filename}`, { 
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      })
      const data = await res.json()
      if (data.success) {
        showToast(`"${filename}" silindi.`, 'info')
        if (uploadedFile === filename) {
          setUploadedFile(null)
          setDataPreview(null)
        }
        fetchFileList()
      }
    } catch {
      showToast('Dosya silinemedi.', 'error')
    }
  }

  const handleLoadSampleData = async (dataset) => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/sample-data`, {
        method: 'POST',
        headers: { 
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ dataset })
      })
      const data = await res.json()
      if (data.success) {
        setUploadedFile(data.file_name)
        setDataPreview({
          html: data.preview_html,
          rows: data.row_count,
          cols: data.columns.length
        })
        setMessages(prev => [...prev, {
          role: 'bot',
          content: `🧪 **Örnek veri seti** yüklendi!\n\n- 📄 Dosya: \`${data.file_name}\`\n- 📊 **${data.row_count}** satır\n\n${data.message}`,
          charts: [],
          html_charts: [],
          steps: []
        }])
        showToast(data.message, 'success')
        fetchFileList()
      } else {
        showToast(data.detail || 'Veri seti yüklenemedi!', 'error')
      }
    } catch (err) {
      showToast('Hata: ' + err.message, 'error')
    }
  }

  const handleScrapeUrl = async () => {
    if (!urlInput.trim() || isScraping) return
    setIsScraping(true)
    try {
      const res = await fetch(`${BACKEND_URL}/api/scrape`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ url: urlInput.trim() })
      })
      const data = await res.json()
      if (data.success) {
        setUploadedFile(data.file_name)
        setDataPreview({
          html: data.preview_html,
          rows: data.row_count,
          cols: data.columns?.length || 0
        })
        showToast(`URL'den veri çekildi: ${data.file_name}`, 'success')
        setUrlInput('')
        fetchFileList()
      } else {
        showToast(data.detail || 'URL\'den veri çekilemedi!', 'error')
      }
    } catch (err) {
      showToast('URL hatası: ' + err.message, 'error')
    } finally {
      setIsScraping(false)
    }
  }

  if (!token) {
    return (
      <>
        <ToastContainer />
        <AuthPage onLogin={(newToken, newUsername) => {
          setToken(newToken)
          setUsername(newUsername)
          localStorage.setItem('token', newToken)
          localStorage.setItem('username', newUsername)
        }} />
      </>
    )
  }

  return (
    <>
      <div className="bg-blobs">
        <div className="blob blob-1" />
        <div className="blob blob-2" />
      </div>

      <ToastContainer />

      <aside className={`sidebar ${sidebarOpen ? 'sidebar-open' : ''}`}>
        <div className="sidebar-logo">
          <h2>Auto-EDA Bot</h2>
          <span className="user-name">Hoş geldin, {username}</span>
        </div>

        <div className="divider" />

        {/* Backend Durumu */}
        <div className="status-badge">
          <span className={`status-dot ${backendOnline ? 'online' : 'offline'}`} />
          Backend: {backendOnline ? 'Çevrimiçi' : 'Çevrimdışı'}
        </div>

        <div className="divider" />

        {/* Dosya Yükleme */}
        <div className="upload-section">
          <h3>📁 Veri Yükle</h3>
          <div
            className={`upload-zone ${dragover ? 'dragover' : ''}`}
            onDragOver={(e) => { e.preventDefault(); setDragover(true) }}
            onDragLeave={() => setDragover(false)}
            onDrop={(e) => {
              e.preventDefault()
              setDragover(false)
              const file = e.dataTransfer.files[0]
              if (file) handleFileUpload(file)
            }}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".csv,.xls,.xlsx"
              onChange={(e) => handleFileUpload(e.target.files[0])}
            />
            <div className="upload-icon">
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" x2="12" y1="3" y2="15"/></svg>
            </div>
            <p>CSV veya Excel dosyanızı<br />sürükleyin veya tıklayın</p>
            <small>.csv, .xls, .xlsx</small>
          </div>
        </div>

        {/* Örnek Veri Setleri */}
        <div className="upload-section" style={{ marginTop: '12px' }}>
          <h3>🧪 Örnek Veri</h3>
          <div className="sample-data-grid">
            <button className="sample-btn" onClick={() => handleLoadSampleData('iris')}>🌸 Iris</button>
            <button className="sample-btn" onClick={() => handleLoadSampleData('titanic')}>🚢 Titanic</button>
            <button className="sample-btn" onClick={() => handleLoadSampleData('tips')}>💰 Tips</button>
          </div>
        </div>
        {/* URL'den Veri Çekme */}
        <div className="upload-section" style={{ marginTop: '12px' }}>
          <h3>🌐 URL'den Çek</h3>
          <div style={{ display: 'flex', gap: '6px' }}>
            <input
              type="text"
              placeholder="https://..."
              value={urlInput}
              onChange={(e) => setUrlInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleScrapeUrl()}
              className="url-input"
            />
            <button
              onClick={handleScrapeUrl}
              disabled={!urlInput.trim() || isScraping}
              className="url-btn"
            >
              {isScraping ? '...' : 'Çek'}
            </button>
          </div>
        </div>

        {/* Dosya Yöneticisi */}
        {fileList.length > 0 && (
          <>
            <div className="divider" />
            <div className="upload-section">
              <h3>📂 Dosyalar ({fileList.length})</h3>
              <div className="file-list">
                {fileList.map(f => (
                  <div 
                    key={f.name} 
                    className={`file-list-item ${uploadedFile === f.name ? 'active' : ''}`}
                    onClick={() => setUploadedFile(f.name)}
                  >
                    <div className="file-list-info">
                      <span className="file-list-name" title={f.name}>{f.name}</span>
                      <span className="file-list-meta">{f.size_display} • {f.row_count > 0 ? `${f.row_count} satır` : ''}</span>
                    </div>
                    <button 
                      className="file-list-delete"
                      onClick={(e) => { e.stopPropagation(); handleDeleteFile(f.name) }}
                      title="Sil"
                    >
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                    </button>
                  </div>
                ))}
              </div>
            </div>
          </>
        )}

        {/* Yüklü dosya önizleme */}
        {uploadedFile && dataPreview && (
          <>
            <div className="divider" />
            <div className="data-preview-container">
              <h4>📊 Önizleme: {uploadedFile}</h4>
              <div 
                className="table-wrapper"
                dangerouslySetInnerHTML={{ __html: dataPreview.html }} 
              />
            </div>
          </>
        )}

        <div className="divider" />

        {/* Aksiyon Butonları */}
        {messages.length > 0 && (
          <button
            className="sidebar-btn pdf-btn"
            onClick={handleDownloadPDF}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
            PDF Raporu İndir
          </button>
        )}

        <button
          className="sidebar-btn clear-btn"
          onClick={handleClearChat}
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/></svg>
          Sohbeti Temizle
        </button>

        {/* Footer */}
        <div className="sidebar-footer">
          Auto-EDA Bot v2.0<br />
          Tamamen Yerel • İnternetsiz • Otonom
        </div>
      </aside>

      {/* ===== MAIN CONTENT ===== */}
      <main className="main-content">
        <header className="header">
          <h1><span>Auto-EDA</span> Otonom Veri Bilimcisi</h1>
          <button 
            onClick={() => setIsDarkMode(!isDarkMode)} 
            className="theme-toggle-btn"
            title="Temayı Değiştir"
          >
            {isDarkMode ? (
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2"/><path d="M12 20v2"/><path d="m4.93 4.93 1.41 1.41"/><path d="m17.66 17.66 1.41 1.41"/><path d="M2 12h2"/><path d="M20 12h2"/><path d="m6.34 17.66-1.41 1.41"/><path d="m19.07 4.93-1.41 1.41"/></svg>
            ) : (
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/></svg>
            )}
          </button>
        </header>

        {/* Chat Alanı */}
        <div className="chat-area">
          {messages.length === 0 && !streamingText ? (
            /* Hoş geldin ekranı */
            <div className="welcome-screen">
              <div className="welcome-icon">
                <svg width="56" height="56" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round"><path d="M9.5 2A2.5 2.5 0 0 1 12 4.5v15a2.5 2.5 0 0 1-4.96.44 2.5 2.5 0 0 1-2.96-3.08 3 3 0 0 1-.34-5.58 2.5 2.5 0 0 1 1.32-4.24 2.5 2.5 0 0 1 1.98-3A2.5 2.5 0 0 1 9.5 2Z"/><path d="M14.5 2A2.5 2.5 0 0 0 12 4.5v15a2.5 2.5 0 0 0 4.96.44 2.5 2.5 0 0 0 2.96-3.08 3 3 0 0 0 .34-5.58 2.5 2.5 0 0 0-1.32-4.24 2.5 2.5 0 0 0-1.98-3A2.5 2.5 0 0 0 14.5 2Z"/></svg>
              </div>
              <h2>Merhaba, Ben Auto-EDA!</h2>
              <p>
                CSV veya Excel dosyanızı yükleyin, sonra veri hakkında sorular sorun.
                Veriyi analiz edip size grafikler ve içgörüler sunacağım.
              </p>
              <div className="quick-actions">
                <button className="quick-action-btn" onClick={() => handleQuickAction('Bu veriyi analiz et')}>
                  <span className="icon">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 3v18h18"/><rect width="4" height="7" x="7" y="10" rx="1"/><rect width="4" height="12" x="15" y="5" rx="1"/></svg>
                  </span>
                  <span>Bu veriyi analiz et</span>
                </button>
                <button className="quick-action-btn" onClick={() => handleQuickAction('Eksik verileri göster')}>
                  <span className="icon">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>
                  </span>
                  <span>Eksik verileri göster</span>
                </button>
                <button className="quick-action-btn" onClick={() => handleQuickAction('Korelasyon matrisi çiz')}>
                  <span className="icon">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 3v18h18"/><path d="m19 9-5 5-4-4-3 3"/></svg>
                  </span>
                  <span>Korelasyon matrisi çiz</span>
                </button>
                <button className="quick-action-btn" onClick={() => handleQuickAction('Veri dağılımlarını görselleştir')}>
                  <span className="icon">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M2 12h4l2-9 5 18 2-9h7"/></svg>
                  </span>
                  <span>Veri dağılımlarını görselleştir</span>
                </button>
              </div>
            </div>
          ) : (
            /* Mesajlar */
            <>
              {messages.map((msg, i) => (
                <div key={i}>
                  <div className={`message ${msg.role}`}>
                    <div className="message-avatar">
                      {msg.role === 'user' ? (
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
                      ) : (
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 8V4H8"/><rect width="16" height="12" x="4" y="8" rx="2"/><path d="M2 14h2"/><path d="M20 14h2"/><path d="M15 13v2"/><path d="M9 13v2"/></svg>
                      )}
                    </div>
                    <div className="message-content-wrapper">
                      <div className="message-bubble">
                        {msg.role === 'bot' ? (
                          <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
                            {msg.content}
                          </ReactMarkdown>
                        ) : (
                          msg.content
                        )}
                      </div>
                      
                      {/* Mesaj Aksiyonları */}
                      <div className="message-actions">
                        <button 
                          className="action-btn" 
                          onClick={() => handleCopyMessage(msg.content)}
                          title="Kopyala"
                        >
                          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect width="14" height="14" x="8" y="8" rx="2" ry="2"/><path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"/></svg>
                        </button>
                        {msg.role === 'user' && (
                          <button 
                            className="action-btn"
                            onClick={() => { setInput(msg.content) }}
                            title="Düzenle"
                          >
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z"/></svg>
                          </button>
                        )}
                      </div>

                      {/* Ajan Düşünce Adımları */}
                      {msg.steps && msg.steps.length > 0 && (
                        <div className="thinking-steps-container">
                          <details>
                            <summary>🔍 Ajanın Analiz Adımları ({msg.steps.length} adım)</summary>
                            <div className="thinking-steps-list">
                              {msg.steps.map((step, k) => (
                                <div key={k} className={`step-item ${step.type}`}>
                                  <strong>{step.status}</strong>
                                  {step.detail && <pre>{step.detail}</pre>}
                                </div>
                              ))}
                            </div>
                          </details>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* PNG Grafikler */}
                  {msg.charts && msg.charts.length > 0 && (
                    <div className="charts-grid">
                      {msg.charts.map((chart, j) => (
                        <div key={j} className="chart-card" onClick={() => setFullscreenChart({ name: chart, type: 'png' })}>
                          <div className="chart-expand-hint">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="15 3 21 3 21 9"/><polyline points="9 21 3 21 3 15"/><line x1="21" y1="3" x2="14" y2="10"/><line x1="3" y1="21" x2="10" y2="14"/></svg>
                          </div>
                          <img src={`${BACKEND_URL}/output/charts/${chart}`} alt={chart} />
                          <div className="chart-name">{chart}</div>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Plotly HTML İnteraktif Grafikler */}
                  {msg.html_charts && msg.html_charts.length > 0 && (
                    <div className="charts-grid">
                      {msg.html_charts.map((chart, j) => (
                        <div key={`html-${j}`} className="chart-card chart-card-interactive">
                          <div className="chart-interactive-badge">⚡ İnteraktif</div>
                          <div className="chart-expand-hint" onClick={() => setFullscreenChart({ name: chart, type: 'html' })}>
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="15 3 21 3 21 9"/><polyline points="9 21 3 21 3 15"/><line x1="21" y1="3" x2="14" y2="10"/><line x1="3" y1="21" x2="10" y2="14"/></svg>
                          </div>
                          <iframe
                            src={`${BACKEND_URL}/output/charts/${chart}`}
                            title={chart}
                            className="chart-iframe"
                          />
                          <div className="chart-name">{chart}</div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </>
          )}

          {/* Streaming Yanıt (Canlı) */}
          {streamingText && (
            <div className="message bot">
              <div className="message-avatar">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 8V4H8"/><rect width="16" height="12" x="4" y="8" rx="2"/><path d="M2 14h2"/><path d="M20 14h2"/><path d="M15 13v2"/><path d="M9 13v2"/></svg>
              </div>
              <div className="message-content-wrapper">
                <div className="message-bubble streaming-bubble">
                  <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
                    {streamingText}
                  </ReactMarkdown>
                  <span className="streaming-cursor" />
                </div>
                {streamingSteps.length > 0 && (
                  <div className="thinking-steps-container">
                    <details open>
                      <summary>🔍 Canlı Adımlar ({streamingSteps.length})</summary>
                      <div className="thinking-steps-list">
                        {streamingSteps.map((step, k) => (
                          <div key={k} className={`step-item ${step.type}`}>
                            <strong>{step.status}</strong>
                            {step.detail && <pre>{step.detail}</pre>}
                          </div>
                        ))}
                      </div>
                    </details>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Düşünüyor animasyonu */}
          {isLoading && !streamingText && (
            <div className="message bot">
              <div className="message-avatar">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 8V4H8"/><rect width="16" height="12" x="4" y="8" rx="2"/><path d="M2 14h2"/><path d="M20 14h2"/><path d="M15 13v2"/><path d="M9 13v2"/></svg>
              </div>
              <div className="thinking">
                <div className="thinking-dots">
                  <span /><span /><span />
                </div>
                Ajan düşünüyor ve kod yazıyor...
              </div>
            </div>
          )}

          <div ref={chatEndRef} />
        </div>

        {/* Mesaj Girişi */}
        <div className="input-area">
          <div className="input-wrapper">
            <input
              type="text"
              placeholder="Veriye bir soru sorun... (örn: 'Bu veriyi analiz et')"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={isLoading}
            />
            {recognitionRef.current && (
              <button 
                className={`mic-btn ${isListening ? 'listening' : ''}`}
                onClick={toggleListening}
                title="Sesle Yazdır"
              >
                <svg width="20" height="20" viewBox="0 0 24 24" fill={isListening ? "currentColor" : "none"} stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" x2="12" y1="19" y2="22"/></svg>
              </button>
            )}
            <button
              className="send-btn"
              onClick={handleSend}
              disabled={!input.trim() || isLoading}
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
            </button>
          </div>
        </div>
      </main>
    </>
  )
}

export default App
