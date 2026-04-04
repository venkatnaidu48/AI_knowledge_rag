import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import './ChatApp.css';

const ChatApp = () => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('token'));
  const messagesEndRef = useRef(null);

  const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

  // Initialize session on mount
  useEffect(() => {
    const initSession = async () => {
      if (token) {
        try {
          const response = await axios.post(
            `${API_URL}/conversations/create`,
            { title: `Chat ${new Date().toLocaleString()}` },
            { headers: { Authorization: `Bearer ${token}` } }
          );
          setSessionId(response.data.session_id);
        } catch (error) {
          console.error('Session creation failed:', error);
        }
      }
    };
    initSession();
  }, [token]);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!input.trim() || !token || !sessionId) return;

    const userMessage = input;
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
    setLoading(true);

    try {
      const response = await axios.post(
        `${API_URL}/ask`,
        {
          query: userMessage,
          session_id: sessionId,
          top_k: 5
        },
        {
          headers: { Authorization: `Bearer ${token}` }
        }
      );

      const assistantMessage = {
        role: 'assistant',
        content: response.data.answer,
        quality_score: response.data.quality_score,
        hallucination_risk: response.data.hallucination_risk,
        sources: response.data.sources,
        provider: response.data.provider
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      const errorMessage = {
        role: 'assistant',
        content: `Error: ${error.response?.data?.detail || error.message}`
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  const handleLogin = async (username, password) => {
    try {
      const response = await axios.post(`${API_URL}/auth/login`, {
        username,
        password
      });
      setToken(response.data.access_token);
      localStorage.setItem('token', response.data.access_token);
    } catch (error) {
      alert('Login failed: ' + (error.response?.data?.detail || error.message));
    }
  };

  if (!token) {
    return <LoginPage onLogin={handleLogin} />;
  }

  return (
    <div className="chat-app">
      <div className="chat-header">
        <h1>🤖 RAG Chat Assistant</h1>
        <div className="header-actions">
          <button className="btn btn-small" onClick={() => { localStorage.clear(); window.location.reload(); }}>
            Logout
          </button>
        </div>
      </div>

      <div className="chat-container">
        <div className="messages">
          {messages.map((msg, idx) => (
            <div key={idx} className={`message message-${msg.role}`}>
              <div className="message-content">
                <p>{msg.content}</p>
                {msg.role === 'assistant' && (
                  <div className="message-metadata">
                    <span className={`quality-score quality-${Math.round(msg.quality_score / 20)}`}>
                      Quality: {msg.quality_score?.toFixed(1) || 'N/A'}%
                    </span>
                    <span className={`hallucination-risk risk-${msg.hallucination_risk?.toLowerCase() || 'unknown'}`}>
                      Risk: {msg.hallucination_risk || 'N/A'}
                    </span>
                    {msg.sources && msg.sources.length > 0 && (
                      <div className="sources">
                        <strong>Sources:</strong>
                        <ul>
                          {msg.sources.slice(0, 3).map((src, i) => (
                            <li key={i}>{src}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>
      </div>

      <form className="input-form" onSubmit={handleSendMessage}>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask a question about our documents..."
          disabled={loading}
        />
        <button type="submit" disabled={loading} className="btn btn-send">
          {loading ? '⏳ Sending...' : '📤 Send'}
        </button>
      </form>
    </div>
  );
};

const LoginPage = ({ onLogin }) => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    onLogin(username, password);
  };

  return (
    <div className="login-page">
      <div className="login-box">
        <h1>🤖 RAG Chat Assistant</h1>
        <form onSubmit={handleSubmit}>
          <input
            type="text"
            placeholder="Username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
          />
          <input
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          <button type="submit" className="btn">Login</button>
        </form>
      </div>
    </div>
  );
};

export default ChatApp;
