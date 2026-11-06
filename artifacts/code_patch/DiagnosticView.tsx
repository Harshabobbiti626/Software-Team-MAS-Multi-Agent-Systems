/**
 * Provenance Header:
 * Task-ID: TASK-1793963085476
 * ADR-Ref: ADR-001
 * Author: FrontendEngineerAgent
 * Contract: api-spec.yaml
 */

import React, { useState, useEffect } from 'react';

export interface DiagnosticEntity {
  id: string;
  name: string;
  status: string;
  category?: string;
  createdAt?: string;
}

export interface DiagnosticCreatePayload {
  name: string;
  category: string;
}

export const DiagnosticView: React.FC = () => {
  const [items, setItems] = useState<DiagnosticEntity[]>([]);
  const [name, setName] = useState('');
  const [category, setCategory] = useState('');
  const [uiState, setUiState] = useState<'IDLE' | 'LOADING' | 'SUCCESS' | 'ERROR'>('IDLE');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const fetchItems = async () => {
    setUiState('LOADING');
    try {
      const res = await fetch('/api/v1/diagnostic');
      if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
      const data = await res.json();
      setItems(Array.isArray(data) ? data : []);
      setUiState('SUCCESS');
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : 'Unknown network failure');
      setUiState('ERROR');
    }
  };

  useEffect(() => {
    fetchItems();
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !category.trim()) return;
    setUiState('LOADING');
    try {
      const res = await fetch('/api/v1/diagnostic', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, category })
      });
      if (!res.ok) throw new Error(`Failed to create ${res.statusText}`);
      setName('');
      setCategory('');
      await fetchItems();
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : 'Creation failed');
      setUiState('ERROR');
    }
  };

  return (
    <div className="max-w-2xl mx-auto p-6 bg-white rounded-lg shadow-md" role="region" aria-label="Diagnostic AutoFix Mission">
      <h2 className="text-2xl font-bold mb-4 text-gray-800">Diagnostic AutoFix Mission</h2>

      {/* Creation Form */}
      <form onSubmit={handleSubmit} className="space-y-4 mb-6" aria-label="Create Diagnostic">
        <div>
          <label htmlFor="diagnostic-name" className="block text-sm font-medium text-gray-700">
            Diagnostic Name
          </label>
          <input
            id="diagnostic-name"
            aria-label="diagnostic-name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Enter name"
            className="mt-1 block w-full rounded border-gray-300 p-2 shadow-sm focus:border-blue-500"
            required
          />
        </div>
        <div>
          <label htmlFor="diagnostic-category" className="block text-sm font-medium text-gray-700">
            Category
          </label>
          <input
            id="diagnostic-category"
            aria-label="diagnostic-category"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            placeholder="Enter category"
            className="mt-1 block w-full rounded border-gray-300 p-2 shadow-sm focus:border-blue-500"
            required
          />
        </div>
        <button
          type="submit"
          disabled={uiState === 'LOADING'}
          className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded transition"
        >
          {uiState === 'LOADING' ? 'Processing...' : `Create ${domain_noun}`}
        </button>
      </form>

      {/* 4-State UI Matrix: Loading / Error / Empty / Populated */}
      {uiState === 'LOADING' && (
        <div className="text-center py-6 text-gray-500" data-testid="loading-skeleton" role="status">
          Loading diagnostic records...
        </div>
      )}

      {uiState === 'ERROR' && (
        <div className="p-4 bg-red-50 border border-red-200 rounded text-red-700" role="alert" data-testid="error-state">
          <p className="font-semibold">Operation encountered an error:</p>
          <p className="text-sm">{errorMessage}</p>
          <button
            onClick={fetchItems}
            className="mt-2 text-sm text-red-600 underline hover:text-red-800"
          >
            Retry
          </button>
        </div>
      )}

      {uiState === 'SUCCESS' && items.length === 0 && (
        <div className="text-center py-8 text-gray-400" data-testid="empty-state">
          No diagnostic records found. Create one using the form above.
        </div>
      )}

      {items.length > 0 && (
        <ul className="divide-y divide-gray-200" data-testid="populated-state">
          {items.map((item) => (
            <li key={item.id} className="py-3 flex justify-between items-center">
              <div>
                <p className="font-medium text-gray-900">{item.name}</p>
                <p className="text-sm text-gray-500">{item.category || 'General'}</p>
              </div>
              <span className="px-2 py-1 text-xs font-semibold rounded bg-green-100 text-green-800">
                {item.status}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};
