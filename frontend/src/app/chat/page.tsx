"use client";
import React, { useState } from 'react';
import axios from 'axios';

interface Citation {
  source_file: string;
  page: number;
}

interface Message {
  role: 'user' | 'assistant';
  text: string;
  citations?: Citation[];
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage: Message = { role: 'user', text: input };
    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      // Connects directly to the FastAPI Backend endpoint we built earlier
      const response = await axios.post('http://127.0.0.1:8000/user/chat', {
        question: input,
      });

      const assistantMessage: Message = {
        role: 'assistant',
        text: response.data.answer,
        citations: response.data.citations,
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', text: 'Error connecting to the AI backend service.' },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-screen max-w-4xl mx-auto p-4 font-sans">
      <header className="border-b pb-4 mb-4">
        <h1 className="text-2xl font-bold text-gray-800">Enterprise AI Order Assistant</h1>
        <p className="text-sm text-gray-500">Ask how to process orders based on Admin-uploaded documentation.</p>
      </header>

      {/* Chat History Container */}
      <div className="flex-1 overflow-y-auto space-y-4 mb-4 p-2 bg-gray-50 rounded-lg border">
        {messages.map((msg, index) => (
          <div key={index} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[75%] rounded-lg p-3 ${msg.role === 'user' ? 'bg-blue-600 text-white' : 'bg-white text-gray-800 border'}`}>
              <p className="text-sm leading-relaxed">{msg.text}</p>
              
              {/* Citations Block */}
              {msg.citations && msg.citations.length > 0 && (
                <div className="mt-3 pt-2 border-t border-gray-200 text-xs text-gray-500">
                  <span className="font-semibold block mb-1">Sources Verified:</span>
                  <div className="flex flex-wrap gap-1">
                    {msg.citations.map((cite, cIdx) => (
                      <span key={cIdx} className="bg-gray-100 border text-gray-700 px-2 py-0.5 rounded">
                        📄 {cite.source_file} (Pg. {cite.page})
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}
        {isLoading && <div className="text-sm text-gray-400 animate-pulse pl-2">AI is analyzing documentation...</div>}
      </div>

      {/* Input Message Form */}
      <form onSubmit={handleSendMessage} className="flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="e.g., How do I create a new international order?"
          className="flex-1 border rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          disabled={isLoading}
        />
        <button
          type="submit"
          className="bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold px-5 py-2 rounded-lg transition-colors"
          disabled={isLoading}
        />
      </form>
    </div>
  );
}
