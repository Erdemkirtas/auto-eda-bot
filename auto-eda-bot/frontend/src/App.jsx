import { useState, useRef, useEffect } from 'react'
import './App.css'

const BACKEND_URL = 'http://localhost:8000'

function App() {
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
  const [dataPreview, setDataPreview] = useState(() => {
    const saved = localStorage.getItem('eda_dataPreview')
    return saved ? JSON.parse(saved) : null
  })
  const [backendOnline, setBackendOnline] = useState(false)
  const [dragover, setDragover] = useState(false)

  // LocalStorage senkronizasyonu
  useEffect(() => {
    localStorage.setItem('eda_messages', JSON.stringify(messages))
  }, [messages])

  useEffect(() => {
    localStorage.setItem('eda_uploadedFile', JSON.stringify(uploadedFile))
  }, [uploadedFile])

  useEffect(() => {
    localStorage.setItem('eda_dataPreview', JSON.stringify(dataPreview))
  }, [dataPreview])

  const chatEndRef = useRef(null)
  const fileInputRef = useRef(null)

  // Backend sağlık kontrolü
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

  // Sohbet alanını otomatik kaydır
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isLoading])

  // Dosya yükleme
  const handleFileUpload = async (file) => {
    if (!file) return

    const ext = file.name.split('.').pop().toLowerCase()
    if (!['csv', 'xls', 'xlsx'].includes(ext)) {
      alert('Sadece CSV ve Excel dosyaları desteklenir!')
      return
    }

    const formData = new FormData()
    formData.append('file', file)

    try {
      const res = await fetch(`${BACKEND_URL}/api/upload`, {
        method: 'POST',
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
          content: `✅ "${data.file_name}" başarıyla yüklendi! (${data.row_count} satır, ${data.columns.length} sütun)\n\nŞimdi bana bu veri hakkında sorular sorabilirsin. Örneğin:\n• "Bu veriyi analiz et"\n• "Eksik verileri göster"\n• "Sütunlar arasındaki korelasyonu çiz"`,
          charts: [],
          steps: []
        }])
      } else {
        alert(data.detail || 'Yükleme başarısız!')
      }
    } catch (err) {
      alert('Backend\'e bağlanılamadı! Sunucunun çalıştığından emin olun.')
    }
  }

  // Mesaj gönder
  const handleSend = async () => {
    if (!input.trim() || isLoading) return

    const userMsg = input.trim()
    setInput('')
    setMessages(prev => [...prev, { role: 'user', content: userMsg }])
    setIsLoading(true)

    try {
      const res = await fetch(`${BACKEND_URL}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: userMsg,
          file_name: uploadedFile
        })
      })
      const data = await res.json()

      setMessages(prev => [...prev, {
        role: 'bot',
        content: data.reply || 'Bir hata oluştu.',
        charts: data.charts || [],
        steps: data.steps || []
      }])
    } catch (err) {
      setMessages(prev => [...prev, {
        role: 'bot',
        content: '❌ Backend\'e bağlanılamadı. Lütfen sunucunun çalıştığından emin olun.',
        charts: [],
        steps: []
      }])
    } finally {
      setIsLoading(false)
    }
  }

  // Enter ile gönder
  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  // Hızlı eylem butonları
  const handleQuickAction = (text) => {
    setInput(text)
  }

  // PDF İndirme
  const handleDownloadPDF = () => {
    if (messages.length === 0) {
      alert("Henüz bir analiz yapılmadı!");
      return;
    }
    const text = encodeURIComponent("Otonom Veri Bilimcisi tarafından oluşturulan EDA Raporu.");
    window.open(`${BACKEND_URL}/api/report?text=${text}`, '_blank');
  }

  // Drag & Drop
  const handleDragOver = (e) => { e.preventDefault(); setDragover(true) }
  const handleDragLeave = () => setDragover(false)
  const handleDrop = (e) => {
    e.preventDefault()
    setDragover(false)
    const file = e.dataTransfer.files[0]
    if (file) handleFileUpload(file)
  }

  return (
    <>
      <div className="bg-blobs">
        <div className="blob blob-1" />
        <div className="blob blob-2" />
      </div>
      {/* ===== SIDEBAR ===== */}
      <aside className="sidebar">
        <div className="sidebar-logo">
          <span className="logo-icon">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 8V4H8"/><rect width="16" height="12" x="4" y="8" rx="2"/><path d="M2 14h2"/><path d="M20 14h2"/><path d="M15 13v2"/><path d="M9 13v2"/></svg>
          </span>
          <h2>Auto-EDA Bot</h2>
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
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
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

        {/* Yüklü dosya */}
        {uploadedFile && (
          <>
            <div className="divider" />
            <div className="file-badge">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{flexShrink: 0}}><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>
              {uploadedFile}
            </div>
            
            {/* Veri Önizleme */}
            {dataPreview && (
              <div className="data-preview-container">
                <h4>İlk 5 Satır Önizleme</h4>
                <div 
                  className="table-wrapper"
                  dangerouslySetInnerHTML={{ __html: dataPreview.html }} 
                />
              </div>
            )}
          </>
        )}

        <div className="divider" />

        {/* Sohbeti Temizle */}
        {messages.length > 0 && (
          <button
            className="sidebar-btn"
            style={{ marginBottom: '10px', borderColor: 'var(--accent-secondary)', color: 'var(--accent-secondary)' }}
            onClick={handleDownloadPDF}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
            PDF Raporu İndir
          </button>
        )}

        <button
          className="sidebar-btn"
          onClick={() => { setMessages([]); setUploadedFile(null); setDataPreview(null) }}
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/></svg>
          Sohbeti Temizle
        </button>

        {/* Footer */}
        <div className="sidebar-footer">
          Auto-EDA Bot v1.0<br />
          Tamamen Yerel • İnternetsiz • Otonom
        </div>
      </aside>

      {/* ===== MAIN CONTENT ===== */}
      <main className="main-content">
        {/* Header */}
        <header className="header">
          <h1>Otonom Veri Bilimciniz — <span>AI Destekli EDA</span></h1>
        </header>

        {/* Chat Alanı */}
        <div className="chat-area">
          {messages.length === 0 ? (
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
            messages.map((msg, i) => (
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
                    <div className="message-bubble">{msg.content}</div>
                    
                    {/* Ajan Düşünce Adımları (Sadece Bot Mesajlarında) */}
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

                {/* Grafikler */}
                {msg.charts && msg.charts.length > 0 && (
                  <div className="charts-grid">
                    {msg.charts.map((chart, j) => (
                      <div key={j} className="chart-card">
                        <img
                          src={`${BACKEND_URL}/output/charts/${chart}`}
                          alt={chart}
                        />
                        <div className="chart-name">{chart}</div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))
          )}

          {/* Düşünüyor animasyonu */}
          {isLoading && (
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
            <button
              className="send-btn"
              onClick={handleSend}
              disabled={!input.trim() || isLoading}
            >
              ➤
            </button>
          </div>
        </div>
      </main>
    </>
  )
}

export default App
