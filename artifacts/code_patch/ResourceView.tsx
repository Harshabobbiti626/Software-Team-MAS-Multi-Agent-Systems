/**
 * Provenance Header:
 * Task-ID: TASK-001
 * ADR-Ref: ADR-001
 * Author: FrontendEngineerAgent
 * Contract: api-spec.yaml
 */

import React, { useState } from 'react';

interface ResourcePayload {
  name: string;
  category: string;
}

export const ResourceView: React.FC = () => {
  const [name, setName] = useState('');
  const [category, setCategory] = useState('');
  const [status, setStatus] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name || !category) return;
    setStatus('SUBMITTING');
    try {
      const res = await fetch('/api/v1/resource', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, category })
      });
      if (res.ok) {
        setStatus('SUCCESS');
      } else {
        setStatus('ERROR');
      }
    } catch {
      setStatus('ERROR');
    }
  };

  return (
    <div className="p-4 border rounded shadow-sm">
      <h2 className="text-xl font-bold">Real-Time Payment Gateway</h2>
      <form onSubmit={handleSubmit} className="space-y-4">
        <input 
          aria-label="resource-name" 
          value={name} 
          onChange={(e) => setName(e.target.value)} 
          placeholder="Resource Name" 
          className="border p-2 w-full"
        />
        <input 
          aria-label="resource-category" 
          value={category} 
          onChange={(e) => setCategory(e.target.value)} 
          placeholder="Category" 
          className="border p-2 w-full"
        />
        <button type="submit" className="bg-blue-600 text-white px-4 py-2 rounded">
          Create Resource
        </button>
      </form>
      {status && <div data-testid="status-indicator">{status}</div>}
    </div>
  );
};
