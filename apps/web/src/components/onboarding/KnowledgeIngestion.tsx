"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import {
  uploadKnowledgeFile,
  addKnowledgeUrl,
  addKnowledgeText,
  listKnowledgeDocuments,
  deleteKnowledgeDocument,
  type KnowledgeBase,
} from "@/actions/knowledge";

interface KnowledgeIngestionProps {
  onComplete?: () => void;
}

type TabType = "file" | "url" | "text";

export function KnowledgeIngestion({ onComplete }: KnowledgeIngestionProps) {
  const [activeTab, setActiveTab] = React.useState<TabType>("file");
  const [documents, setDocuments] = React.useState<KnowledgeBase[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [uploading, setUploading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [successMessage, setSuccessMessage] = React.useState<string | null>(null);

  // Form states
  const [url, setUrl] = React.useState("");
  const [urlTitle, setUrlTitle] = React.useState("");
  const [text, setText] = React.useState("");
  const [textTitle, setTextTitle] = React.useState("");
  const [file, setFile] = React.useState<File | null>(null);

  // Polling for status updates
  const pollingIntervalRef = React.useRef<NodeJS.Timeout | null>(null);

  React.useEffect(() => {
    loadDocuments();
    startPolling();

    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
      }
    };
  }, []);

  function startPolling() {
    // Poll every 3 seconds for document status updates
    pollingIntervalRef.current = setInterval(() => {
      loadDocuments(true);
    }, 3000);
  }

  async function loadDocuments(silent = false) {
    if (!silent) setLoading(true);
    setError(null);

    const result = await listKnowledgeDocuments();

    if (result.error && !silent) {
      setError(result.error);
    } else if (result.data) {
      setDocuments(result.data.items);
    }

    if (!silent) setLoading(false);
  }

  async function handleFileUpload(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!file) return;

    setUploading(true);
    setError(null);
    setSuccessMessage(null);

    const formData = new FormData();
    formData.append("file", file);

    const result = await uploadKnowledgeFile(formData);

    if (result.error) {
      setError(result.error);
    } else if (result.data) {
      setSuccessMessage("File uploaded successfully");
      setFile(null);
      loadDocuments(true);
    }

    setUploading(false);
  }

  async function handleUrlSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();

    if (!url.trim()) {
      setError("URL is required");
      return;
    }

    setUploading(true);
    setError(null);
    setSuccessMessage(null);

    const result = await addKnowledgeUrl(url, urlTitle || undefined);

    if (result.error) {
      setError(result.error);
    } else if (result.data) {
      setSuccessMessage("URL added successfully");
      setUrl("");
      setUrlTitle("");
      loadDocuments(true);
    }

    setUploading(false);
  }

  async function handleTextSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();

    if (!text.trim()) {
      setError("Text is required");
      return;
    }

    setUploading(true);
    setError(null);
    setSuccessMessage(null);

    const result = await addKnowledgeText(text, textTitle || undefined);

    if (result.error) {
      setError(result.error);
    } else if (result.data) {
      setSuccessMessage("Text added successfully");
      setText("");
      setTextTitle("");
      loadDocuments(true);
    }

    setUploading(false);
  }

  async function handleDelete(id: number) {
    if (!confirm("Are you sure you want to delete this document?")) {
      return;
    }

    setError(null);

    const result = await deleteKnowledgeDocument(id);

    if (result.error) {
      setError(result.error);
    } else {
      setSuccessMessage("Document deleted successfully");
      loadDocuments(true);
    }
  }

  function getStatusBadge(status: KnowledgeBase["status"]) {
    const variants = {
      processing: "bg-yellow-100 text-yellow-800",
      ready: "bg-green-100 text-green-800",
      failed: "bg-red-100 text-red-800",
    };

    const labels = {
      processing: "Processing",
      ready: "Ready",
      failed: "Failed",
    };

    return (
      <span
        className={cn(
          "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium",
          variants[status]
        )}
      >
        {labels[status]}
      </span>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold text-gray-900">Knowledge Base</h2>
        <p className="text-sm text-gray-500 mt-1">
          Upload PDFs, URLs, or text to train your AI agent
        </p>
      </div>

      {/* Alerts */}
      {error && (
        <div className="rounded-md bg-red-50 p-4">
          <p className="text-sm text-red-800">{error}</p>
        </div>
      )}

      {successMessage && (
        <div className="rounded-md bg-green-50 p-4">
          <p className="text-sm text-green-800">{successMessage}</p>
        </div>
      )}

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-8">
          {[
            { key: "file" as TabType, label: "Upload File" },
            { key: "url" as TabType, label: "Add URL" },
            { key: "text" as TabType, label: "Paste Text" },
          ].map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={cn(
                "whitespace-nowrap border-b-2 py-4 px-1 text-sm font-medium",
                activeTab === tab.key
                  ? "border-orange-500 text-orange-600"
                  : "border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700"
              )}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      <div className="bg-white shadow rounded-lg p-6">
        {activeTab === "file" && (
          <form onSubmit={handleFileUpload} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">
                Upload PDF (max 50MB)
              </label>
              <div className="mt-2 flex justify-center px-6 pt-5 pb-6 border-2 border-gray-300 border-dashed rounded-md">
                <div className="space-y-1 text-center">
                  <svg
                    className="mx-auto h-12 w-12 text-gray-400"
                    stroke="currentColor"
                    fill="none"
                    viewBox="0 0 48 48"
                  >
                    <path
                      d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02"
                      strokeWidth={2}
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                  <div className="flex text-sm text-gray-600">
                    <label
                      htmlFor="file-upload"
                      className="relative cursor-pointer bg-white rounded-md font-medium text-orange-600 hover:text-orange-500 focus-within:outline-none"
                    >
                      <span>Upload a file</span>
                      <input
                        id="file-upload"
                        type="file"
                        accept=".pdf,.txt,.md"
                        className="sr-only"
                        onChange={(e) => setFile(e.target.files?.[0] || null)}
                      />
                    </label>
                    <p className="pl-1">or drag and drop</p>
                  </div>
                  <p className="text-xs text-gray-500">PDF, TXT, MD up to 50MB</p>
                  {file && (
                    <p className="text-sm text-gray-900 mt-2">Selected: {file.name}</p>
                  )}
                </div>
              </div>
            </div>
            <button
              type="submit"
              disabled={!file || uploading}
              className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-orange-600 hover:bg-orange-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-orange-500 disabled:opacity-50"
            >
              {uploading ? "Uploading..." : "Upload"}
            </button>
          </form>
        )}

        {activeTab === "url" && (
          <form onSubmit={handleUrlSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">
                URL
              </label>
              <input
                type="url"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="https://example.com/page"
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-orange-500 focus:ring-orange-500 sm:text-sm border p-2"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">
                Title (optional)
              </label>
              <input
                type="text"
                value={urlTitle}
                onChange={(e) => setUrlTitle(e.target.value)}
                placeholder="Document title"
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-orange-500 focus:ring-orange-500 sm:text-sm border p-2"
              />
            </div>
            <button
              type="submit"
              disabled={uploading}
              className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-orange-600 hover:bg-orange-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-orange-500 disabled:opacity-50"
            >
              {uploading ? "Adding..." : "Add URL"}
            </button>
          </form>
        )}

        {activeTab === "text" && (
          <form onSubmit={handleTextSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">
                Title (optional)
              </label>
              <input
                type="text"
                value={textTitle}
                onChange={(e) => setTextTitle(e.target.value)}
                placeholder="Document title"
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-orange-500 focus:ring-orange-500 sm:text-sm border p-2"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">
                Text Content
              </label>
              <textarea
                value={text}
                onChange={(e) => setText(e.target.value)}
                rows={10}
                placeholder="Paste your text content here..."
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-orange-500 focus:ring-orange-500 sm:text-sm border p-2"
              />
            </div>
            <button
              type="submit"
              disabled={uploading}
              className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-orange-600 hover:bg-orange-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-orange-500 disabled:opacity-50"
            >
              {uploading ? "Adding..." : "Add Text"}
            </button>
          </form>
        )}
      </div>

      {/* Documents List */}
      <div className="bg-white shadow rounded-lg">
        <div className="px-4 py-5 sm:px-6 border-b border-gray-200">
          <h3 className="text-lg leading-6 font-medium text-gray-900">
            Documents ({documents.length})
          </h3>
        </div>
        <ul className="divide-y divide-gray-200">
          {loading ? (
            <li className="px-4 py-4 text-center text-sm text-gray-500">
              Loading...
            </li>
          ) : documents.length === 0 ? (
            <li className="px-4 py-4 text-center text-sm text-gray-500">
              No documents yet. Upload your first document above.
            </li>
          ) : (
            documents.map((doc) => (
              <li key={doc.id} className="px-4 py-4 sm:px-6">
                <div className="flex items-center justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center space-x-3">
                      <p className="text-sm font-medium text-orange-600 truncate">
                        {doc.title}
                      </p>
                      {getStatusBadge(doc.status)}
                    </div>
                    <div className="mt-1 flex items-center space-x-4 text-sm text-gray-500">
                      <span>Source: {doc.sourceType}</span>
                      {doc.chunkCount > 0 && (
                        <span>{doc.chunkCount} chunks</span>
                      )}
                      {doc.errorMessage && (
                        <span className="text-red-600">{doc.errorMessage}</span>
                      )}
                    </div>
                  </div>
                  <button
                    onClick={() => handleDelete(doc.id)}
                    disabled={doc.status === "processing"}
                    className={cn(
                      "ml-4 text-sm font-medium",
                      doc.status === "processing"
                        ? "text-gray-400 cursor-not-allowed"
                        : "text-red-600 hover:text-red-900"
                    )}
                  >
                    Delete
                  </button>
                </div>
              </li>
            ))
          )}
        </ul>
      </div>
    </div>
  );
}
