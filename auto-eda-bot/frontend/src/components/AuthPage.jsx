import { useState } from 'react';
import { Bot, Mail, Lock, User as UserIcon, ArrowRight, Loader2 } from 'lucide-react';
import { showToast } from './Toast';

export default function AuthPage({ onLogin }) {
  const [isLogin, setIsLogin] = useState(true);
  const [isLoading, setIsLoading] = useState(false);
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: ''
  });

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      if (isLogin) {
        // Login Request (OAuth2 form data expected by FastAPI)
        const formBody = new URLSearchParams();
        formBody.append('username', formData.username);
        formBody.append('password', formData.password);

        const res = await fetch('http://localhost:8000/api/auth/login', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
          },
          body: formBody
        });

        const data = await res.json();
        
        if (!res.ok) {
          throw new Error(data.detail || 'Giriş başarısız.');
        }

        localStorage.setItem('token', data.access_token);
        localStorage.setItem('username', data.username);
        showToast(`Hoş geldin, ${data.username}!`, 'success');
        onLogin(data.access_token, data.username);

      } else {
        // Register Request (JSON expected)
        const res = await fetch('http://localhost:8000/api/auth/register', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            username: formData.username,
            email: formData.email,
            password: formData.password
          })
        });

        const data = await res.json();

        if (!res.ok) {
          throw new Error(data.detail || 'Kayıt başarısız.');
        }

        showToast('Kayıt başarılı! Şimdi giriş yapabilirsin.', 'success');
        setIsLogin(true); // Switch to login view
      }
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="auth-container">
      {/* Arka plan dekorasyonları */}
      <div className="glow glow-1"></div>
      <div className="glow glow-2"></div>
      
      <div className="auth-card glass-panel">
        <div className="auth-header">
          <div className="auth-logo">
            <Bot size={36} color="var(--accent-primary)" />
          </div>
          <h1>Auto-EDA Bot</h1>
          <p>Otonom Veri Bilimcisi Ajanı</p>
        </div>

        <div className="auth-tabs">
          <button 
            className={`auth-tab ${isLogin ? 'active' : ''}`}
            onClick={() => setIsLogin(true)}
          >
            Giriş Yap
          </button>
          <button 
            className={`auth-tab ${!isLogin ? 'active' : ''}`}
            onClick={() => setIsLogin(false)}
          >
            Kayıt Ol
          </button>
        </div>

        <form onSubmit={handleSubmit} className="auth-form">
          <div className="input-group">
            <UserIcon size={18} className="input-icon" />
            <input 
              type="text" 
              placeholder="Kullanıcı Adı" 
              required
              value={formData.username}
              onChange={(e) => setFormData({...formData, username: e.target.value})}
            />
          </div>

          {!isLogin && (
            <div className="input-group">
              <Mail size={18} className="input-icon" />
              <input 
                type="email" 
                placeholder="E-posta Adresi" 
                value={formData.email}
                onChange={(e) => setFormData({...formData, email: e.target.value})}
              />
            </div>
          )}

          <div className="input-group">
            <Lock size={18} className="input-icon" />
            <input 
              type="password" 
              placeholder="Parola" 
              required
              value={formData.password}
              onChange={(e) => setFormData({...formData, password: e.target.value})}
            />
          </div>

          <button type="submit" className="primary-button auth-submit" disabled={isLoading}>
            {isLoading ? (
              <Loader2 size={20} className="spinner" />
            ) : (
              <>
                {isLogin ? 'Giriş Yap' : 'Kayıt Ol'}
                <ArrowRight size={18} />
              </>
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
