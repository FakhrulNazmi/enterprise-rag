"use client";
import React, { useState, useEffect } from 'react';
import axios from 'axios';

interface ManagedDocument {
  filename: string;
  total_chunks: number;
}

export default function AdminPage() {
  const [file, setFile] = useState<File | null>(null);
  const [documents, setDocuments] = useState<ManagedDocument[]>([]);
  const [status, setStatus] = useState<{ type: 'idle' | 'loading' | 'success' | 'error'; message: string }>({ type: 'idle', message: '' });
  const [loadingDocs, setLoadingDocs] = useState<boolean>(false);

  // Fetch documents from LanceDB backend storage layout
  const fetchUploadedDocuments = async () => {
    setLoadingDocs(true);
    try {
      const response = await axios.get('http://127.0.0.1:8000/admin/documents');
      setDocuments(response.data.documents || []);
    } catch (error) {
      console.error("Could not fetch document index configuration list:", error);
    } finally {
      setLoadingDocs(false);
    }
  };

  // Automatically fetch files when admin loads the module viewport
  useEffect(() => {
    fetchUploadedDocuments();
  }, []);

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
      // Refresh folder management list array view dynamically
      fetchUploadedDocuments();
    } catch (error: any) {
      const errorMsg = error.response?.data?.detail || 'Failed to connect to the AI engine server.';
      setStatus({ type: 'error', message: errorMsg });
    }
  };

  return (
    <div className="max-w-4xl mx-auto mt-12 p-6 font-sans grid grid-cols-1 md:grid-cols-5 gap-6">
      
      {/* LEFT COLUMN: Ingestion Module Input Panel Form */}
      <div className="md:col-span-2 bg-white border rounded-xl p-5 shadow-sm h-fit">
        <h1 className="text-lg font-bold text-gray-800 mb-1">Data Ingestion</h1>
        <p className="text-xs text-gray-500 mb-4">Upload files for AI vector optimization layouts.</p>
        
        <form onSubmit={handleUpload} className="space-y-4">
          <div className="border-2 border-dashed border-gray-300 rounded-lg p-4 text-center hover:border-blue-500 transition-colors cursor-pointer relative">
            <input 
              type="file" 
              accept=".pdf" 
              onChange={handleFileChange} 
              className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
            />
            <div className="text-gray-600 text-xs font-medium">
              {file ? `📄 ${file.name}` : "Click or drag PDF file"}
            </div>
            <span className="text-[10px] text-gray-400 block mt-1">PDF up to 25MB</span>
          </div>

          <button
            type="submit"
            disabled={!file || status.type === 'loading'}
            className={`w-full py-2 rounded-lg text-xs font-semibold text-white transition-colors ${!file || status.type === 'loading' ? 'bg-gray-400 cursor-not-allowed' : 'bg-blue-600 hover:bg-blue-700'}`}
          >
            {status.type === 'loading' ? 'Ingesting...' : 'Parse & Embed File'}
          </button>
        </form>

        {status.message && (
          <div className={`mt-4 p-3 rounded-lg text-[11px] font-medium ${status.type === 'success' ? 'bg-green-50 text-green-700 border border-green-200' : status.type === 'error' ? 'bg-red-50 text-red-700 border border-red-200' : 'bg-blue-50 text-blue-700'}`}>
            {status.message}
          </div>
        )}
      </div>

      {/* RIGHT COLUMN: Interactive Document Folder Structure Directory View */}
      <div className="md:col-span-3 bg-white border rounded-xl p-5 shadow-sm">
        <div className="flex justify-between items-center mb-3">
          <div>
            <h2 className="text-lg font-bold text-gray-800">Knowledge Repository</h2>
            <p className="text-xs text-gray-500">Currently indexed runtime memory files in LanceDB tables.</p>
          </div>
          <button 
            onClick={fetchUploadedDocuments}
            className="text-xs bg-gray-100 hover:bg-gray-200 border px-2.5 py-1 rounded text-gray-600 transition-colors"
          >
            {loadingDocs ? 'Refreshing...' : '🔄 Refresh'}
          </button>
        </div>

        <div className="border border-gray-100 rounded-lg overflow-hidden bg-gray-50 max-h-[320px] overflow-y-auto">
          {documents.length === 0 ? (
            <div className="p-8 text-center text-xs text-gray-400">
              📂 No items have been parsed into the database environment yet.
            </div>
          ) : (
            <div className="divide-y divide-gray-200">
              {documents.map((doc, idx) => (
                <div key={idx} className="p-3 flex items-center justify-between bg-white hover:bg-gray-50 transition-colors">
                  <div className="flex items-center space-x-3 overflow-hidden pr-2">
                    <span className="text-xl shrink-0">📄</span>
                    <div className="truncate">
                      <p className="text-xs font-semibold text-gray-700 truncate">{doc.filename}</p>
                      <p className="text-[10px] text-gray-400">Context File Structure Row Element</p>
                    </div>
                  </div>
                  <div className="shrink-0 text-right">
                    <span className="inline-block bg-blue-50 text-blue-700 text-[10px] font-bold px-2 py-0.5 rounded-full border border-blue-100">
                      {doc.total_chunks} vectors
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

    </div>
  );
}
