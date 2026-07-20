"use client";
import React, { useState } from 'react';
import axios from 'axios';

export default function AdminPage() {
  const [file, setFile] = useState<File | null>(null);
  const [status, setStatus] = useState<{ type: 'idle' | 'loading' | 'success' | 'error'; message: string }>({ type: 'idle', message: '' });

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setStatus({ type: 'idle', message: '' });
    }
  };

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;

    setStatus({ type: 'loading', message: 'Processing PDF data extraction and creating vector embeddings...' });

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await axios.post('http://127.0.0.1:8000/admin/upload-pdf', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setStatus({ type: 'success', message: response.data.message });
      setFile(null);
    } catch (error: any) {
      const errorMsg = error.response?.data?.detail || 'Failed to connect to the AI engine server.';
      setStatus({ type: 'error', message: errorMsg });
    }
  };

  return (
    <div className="max-w-xl mx-auto mt-12 p-6 bg-white border rounded-xl shadow-sm font-sans">
      <h1 className="text-xl font-bold text-gray-800 mb-2">Knowledge Base Ingestion System</h1>
      <p className="text-sm text-gray-500 mb-6">Upload operational manuals or order processing flowcharts for user AI search integration.</p>
      
      <form onSubmit={handleUpload} className="space-y-4">
        <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center hover:border-blue-500 transition-colors cursor-pointer relative">
          <input 
            type="file" 
            accept=".pdf" 
            onChange={handleFileChange} 
            className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
          />
          <div className="text-gray-600 text-sm">
            {file ? `Selected file: ${file.name}` : "Click or drag your training PDF file here"}
          </div>
          <span className="text-xs text-gray-400 block mt-1">Accepts PDF files up to 25MB</span>
        </div>

        <button
          type="submit"
          disabled={!file || status.type === 'loading'}
          className={`w-full py-2 rounded-lg text-sm font-semibold text-white transition-colors ${!file || status.type === 'loading' ? 'bg-gray-400 cursor-not-allowed' : 'bg-blue-600 hover:bg-blue-700'}`}
        >
          {status.type === 'loading' ? 'Ingesting Data...' : 'Parse and Store PDF Knowledge'}
        </button>
      </form>

      {status.message && (
        <div className={`mt-4 p-3 rounded-lg text-xs font-medium ${status.type === 'success' ? 'bg-green-50 text-green-700 border border-green-200' : status.type === 'error' ? 'bg-red-50 text-red-700 border border-red-200' : 'bg-blue-50 text-blue-700'}`}>
          {status.message}
        </div>
      )}
    </div>
  );
}
