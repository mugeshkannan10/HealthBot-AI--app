import React, { useState, useEffect, useRef } from 'react';
import './App.css';
import { MessageCircle, Send, Stethoscope, Heart, Shield, Lightbulb, Clock, User } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const App = () => {
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [userId] = useState(() => `user_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`);
  const [stats, setStats] = useState({});
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    fetchStats();
    // Add welcome message
    setMessages([{
      type: 'bot',
      content: `👋 Hello! I'm your AI-powered Public Health Assistant. I'm here to help you with:

🩺 Disease information and prevention
💊 General health questions
🥗 Wellness and lifestyle advice
🚨 When to seek medical care

How can I help you today?`,
      timestamp: new Date()
    }]);
  }, []);

  const fetchStats = async () => {
    try {
      const response = await fetch(`${API}/health/stats`);
      const data = await response.json();
      setStats(data);
    } catch (error) {
      console.error('Error fetching stats:', error);
    }
  };

  const sendMessage = async () => {
    if (!inputMessage.trim() || isLoading) return;

    const userMessage = {
      type: 'user',
      content: inputMessage,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setIsLoading(true);

    try {
      const response = await fetch(`${API}/health/query`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          question: inputMessage,
          user_id: userId
        }),
      });

      if (response.ok) {
        const data = await response.json();
        const botMessage = {
          type: 'bot',
          content: data.answer,
          timestamp: new Date()
        };
        setMessages(prev => [...prev, botMessage]);
        fetchStats(); // Update stats after successful query
      } else {
        throw new Error('Failed to get response');
      }
    } catch (error) {
      console.error('Error sending message:', error);
      const errorMessage = {
        type: 'bot',
        content: 'Sorry, I encountered an error processing your question. Please try again.',
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const quickQuestions = [
    "What are the symptoms of flu?",
    "How can I boost my immune system?",
    "When should I see a doctor for a headache?",
    "What foods are good for heart health?",
    "How much water should I drink daily?",
    "What are signs of high blood pressure?"
  ];

  const handleQuickQuestion = (question) => {
    setInputMessage(question);
  };

  return (
    <div className="app">
      {/* Header */}
      <header className="header">
        <div className="header-content">
          <div className="logo">
            <Stethoscope className="logo-icon" />
            <h1>HealthBot AI</h1>
          </div>
          <div className="stats">
            <div className="stat-item">
              <MessageCircle size={16} />
              <span>{stats.total_queries || 0} queries</span>
            </div>
            <div className="stat-item">
              <User size={16} />
              <span>{stats.unique_users || 0} users</span>
            </div>
            <div className="stat-item">
              <Clock size={16} />
              <span>{stats.recent_queries_24h || 0} today</span>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="main-content">
        <div className="chat-container">
          {/* Feature Cards */}
          {messages.length <= 1 && (
            <div className="features-grid">
              <div className="feature-card">
                <Heart className="feature-icon" />
                <h3>Disease Awareness</h3>
                <p>Get information about symptoms, causes, and prevention of common diseases</p>
              </div>
              <div className="feature-card">
                <Shield className="feature-icon" />
                <h3>Prevention Tips</h3>
                <p>Learn evidence-based prevention strategies and healthy lifestyle choices</p>
              </div>
              <div className="feature-card">
                <Lightbulb className="feature-icon" />
                <h3>Health Education</h3>
                <p>Understand health concepts explained in simple, accessible language</p>
              </div>
            </div>
          )}

          {/* Messages */}
          <div className="messages-container">
            {messages.map((message, index) => (
              <div key={index} className={`message ${message.type}`}>
                <div className="message-content">
                  <div className="message-text">
                    {message.content.split('\n').map((line, i) => (
                      <p key={i}>{line}</p>
                    ))}
                  </div>
                  <div className="message-time">
                    {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </div>
                </div>
              </div>
            ))}
            {isLoading && (
              <div className="message bot">
                <div className="message-content">
                  <div className="typing-indicator">
                    <div className="typing-dot"></div>
                    <div className="typing-dot"></div>
                    <div className="typing-dot"></div>
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Quick Questions */}
          {messages.length <= 1 && (
            <div className="quick-questions">
              <h3>Quick Questions to Get Started:</h3>
              <div className="quick-questions-grid">
                {quickQuestions.map((question, index) => (
                  <button
                    key={index}
                    className="quick-question-btn"
                    onClick={() => handleQuickQuestion(question)}
                  >
                    {question}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Input Area */}
          <div className="input-area">
            <div className="input-container">
              <textarea
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Ask me anything about health, diseases, symptoms, or prevention..."
                rows="3"
                disabled={isLoading}
              />
              <button 
                onClick={sendMessage} 
                disabled={!inputMessage.trim() || isLoading}
                className="send-button"
              >
                <Send size={20} />
              </button>
            </div>
            <div className="disclaimer">
              <p>⚠️ This AI assistant provides general health information. Always consult healthcare professionals for medical diagnosis and treatment.</p>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};

export default App;