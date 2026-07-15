import { useState, useRef, useEffect } from 'react'
import './App.css'

const BACKEND_URL = 'http://localhost:8000'

function App() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [uploadedFile, setUploadedFile] = useState(null)
  const [dataPreview, setDataPreview] = useState(null)
  const [backendOnline, setBackendOnline] = useState(false)
  const [dragover, setDragover] = useState(false)

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
      {/* ===== SIDEBAR ===== */}
      <aside className="sidebar">
        <div className="sidebar-logo">
          <span className="logo-icon">🤖</span>
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
            <div className="upload-icon">📤</div>
            <p>CSV veya Excel dosyanızı<br />sürükleyin veya tıklayın</p>
            <small>.csv, .xls, .xlsx</small>
          </div>
        </div>

        {/* Yüklü dosya */}
        {uploadedFile && (
          <>
            <div className="divider" />
            <div className="file-badge">
              📊 {uploadedFile}
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
        <button
          className="sidebar-btn"
          onClick={() => { setMessages([]); setUploadedFile(null); setDataPreview(null) }}
        >
          🗑️ Sohbeti Temizle
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
              <div className="welcome-icon">🧠</div>
              <h2>Merhaba, Ben Auto-EDA!</h2>
              <p>
                CSV veya Excel dosyanızı yükleyin, sonra veri hakkında sorular sorun.
                Veriyi analiz edip size grafikler ve içgörüler sunacağım.
              </p>
              <div className="quick-actions">
                <button className="quick-action-btn" onClick={() => handleQuickAction('Bu veriyi analiz et')}>
                  📊 Bu veriyi analiz et
                </button>
                <button className="quick-action-btn" onClick={() => handleQuickAction('Eksik verileri göster')}>
                  🔍 Eksik verileri göster
                </button>
                <button className="quick-action-btn" onClick={() => handleQuickAction('Korelasyon matrisi çiz')}>
                  📈 Korelasyon matrisi çiz
                </button>
                <button className="quick-action-btn" onClick={() => handleQuickAction('Veri dağılımlarını görselleştir')}>
                  🎯 Veri dağılımlarını görselleştir
                </button>
              </div>
            </div>
          ) : (
            /* Mesajlar */
            messages.map((msg, i) => (
              <div key={i}>
                <div className={`message ${msg.role}`}>
                  <div className="message-avatar">
                    {msg.role === 'user' ? '👤' : '🤖'}
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
              <div className="message-avatar">🤖</div>
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
