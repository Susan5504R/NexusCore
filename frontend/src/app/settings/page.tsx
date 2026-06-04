"use client";

import { useState, useEffect } from "react";
import { API_BASE_URL, API_KEY } from "../../lib/config";
import { Loader2, Copy, Check } from "lucide-react";

interface ApiKey {
  id: string;
  namespace: string;
  label: string;
  created_at: string;
  revoked: boolean;
  last_used_at: string | null;
}

export default function SettingsPage() {
  const [keys, setKeys] = useState<ApiKey[]>([]);
  const [loading, setLoading] = useState(true);
  const [namespace, setNamespace] = useState("");
  const [label, setLabel] = useState("");
  const [generating, setGenerating] = useState(false);
  const [newKey, setNewKey] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", "palette1");
    fetchKeys();
  }, []);

  const fetchKeys = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/v1/keys`, {
        headers: { Authorization: `Bearer ${API_KEY}` }
      });
      if (!res.ok) throw new Error("Failed to fetch");
      const data = await res.json();
      setKeys(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    setGenerating(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/v1/keys`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${API_KEY}`
        },
        body: JSON.stringify({ namespace, label })
      });
      if (!res.ok) throw new Error("Failed to generate");
      const data = await res.json();
      setNewKey(data.raw_key);
      setNamespace("");
      setLabel("");
      fetchKeys();
    } catch (err) {
      console.error(err);
    } finally {
      setGenerating(false);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <main className="min-h-screen p-8 transition-colors duration-500">
      <div className="max-w-4xl mx-auto space-y-8">
        
        <div className="flex justify-between items-center bg-surface p-6 rounded-2xl shadow-xl border border-primary/30">
          <div>
            <h1 className="text-3xl font-extrabold tracking-tight text-transparent bg-clip-text bg-gradient-to-r from-primary to-error drop-shadow-md">
              SaaS Administration
            </h1>
            <p className="text-text-main/90 font-medium mt-1">Tenant API Keys & Onboarding</p>
          </div>
          <a href="/dashboard" className="text-sm font-semibold text-primary hover:underline">
            &larr; Back to Dashboard
          </a>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          {/* Generate Key */}
          <div className="bg-surface p-6 rounded-2xl shadow-lg border border-primary/20">
            <h2 className="text-xl font-bold mb-4 text-text-main">Generate API Key</h2>
            <form onSubmit={handleGenerate} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-text-muted mb-1">Tenant Namespace</label>
                <input 
                  type="text" 
                  value={namespace}
                  onChange={e => setNamespace(e.target.value)}
                  placeholder="e.g. acme-corp"
                  required
                  className="w-full bg-base border border-surface rounded-lg px-3 py-2 text-sm text-text-main focus:outline-none focus:border-primary transition-colors"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-text-muted mb-1">Label (Optional)</label>
                <input 
                  type="text" 
                  value={label}
                  onChange={e => setLabel(e.target.value)}
                  placeholder="e.g. Prod Environment"
                  className="w-full bg-base border border-surface rounded-lg px-3 py-2 text-sm text-text-main focus:outline-none focus:border-primary transition-colors"
                />
              </div>
              <button 
                type="submit"
                disabled={generating || !namespace}
                className="w-full bg-primary/10 border border-primary/30 text-primary py-2 rounded-lg text-sm font-semibold hover:bg-primary/20 transition-all disabled:opacity-50"
              >
                {generating ? <Loader2 className="w-5 h-5 animate-spin mx-auto" /> : "Generate Key"}
              </button>
            </form>

            {newKey && (
              <div className="mt-6 p-4 bg-success/10 border border-success/30 rounded-xl space-y-2">
                <p className="text-sm font-semibold text-success">Key Generated Successfully!</p>
                <p className="text-xs text-text-muted">Copy this now. You won't be able to see it again.</p>
                <div className="flex items-center gap-2 mt-2">
                  <code className="flex-1 bg-base p-2 rounded text-xs text-text-main truncate select-all">
                    {newKey}
                  </code>
                  <button 
                    onClick={() => copyToClipboard(newKey)}
                    className="p-2 bg-success text-surface rounded hover:bg-success/80 transition-colors"
                  >
                    {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Onboarding snippet */}
          <div className="bg-surface p-6 rounded-2xl shadow-lg border border-primary/20 flex flex-col justify-between">
            <div>
              <h2 className="text-xl font-bold mb-2 text-text-main">Daemon Onboarding</h2>
              <p className="text-sm text-text-muted mb-4">
                Provide this exact command to the tenant so they can run the local execution daemon in their own environment.
              </p>
              <div className="bg-base p-4 rounded-xl border border-surface text-xs font-mono text-text-muted break-all relative group">
                <div className="text-primary mb-2"># 1. Install lightweight dependencies</div>
                pip install psutil requests<br/><br/>
                <div className="text-primary mb-2"># 2. Download and run the daemon</div>
                curl -sO https://raw.githubusercontent.com/Susan5504R/NexusCore/main/frontend/public/nexus_daemon.py<br/>
                python nexus_daemon.py \<br/>
                &nbsp;&nbsp;--api-key {<span className="text-warning">{newKey ? newKey : "YOUR_API_KEY"}</span>} \<br/>
                &nbsp;&nbsp;--server-url https://nexuscore-rdc1.onrender.com
              </div>
            </div>
          </div>
        </div>

        {/* Existing Keys Table */}
        <div className="bg-surface p-6 rounded-2xl shadow-lg border border-primary/20">
          <h2 className="text-xl font-bold mb-4 text-text-main">Active Keys</h2>
          {loading ? (
            <div className="flex justify-center p-8"><Loader2 className="w-6 h-6 animate-spin text-primary" /></div>
          ) : keys.length === 0 ? (
            <p className="text-sm text-text-muted text-center p-4">No API keys generated yet.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm text-left">
                <thead className="text-xs text-text-muted uppercase border-b border-surface">
                  <tr>
                    <th className="px-4 py-3">Namespace</th>
                    <th className="px-4 py-3">Label</th>
                    <th className="px-4 py-3">Created At</th>
                    <th className="px-4 py-3">Last Used</th>
                    <th className="px-4 py-3 text-right">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {keys.map((key) => (
                    <tr key={key.id} className="border-b border-surface/50 hover:bg-base/50">
                      <td className="px-4 py-3 font-medium text-text-main">{key.namespace}</td>
                      <td className="px-4 py-3 text-text-muted">{key.label || "-"}</td>
                      <td className="px-4 py-3 text-text-muted">{new Date(key.created_at).toLocaleDateString()}</td>
                      <td className="px-4 py-3 text-text-muted">{key.last_used_at ? new Date(key.last_used_at).toLocaleDateString() : "Never"}</td>
                      <td className="px-4 py-3 text-right">
                        {key.revoked ? (
                          <span className="bg-error/10 text-error px-2 py-1 rounded text-xs font-semibold">Revoked</span>
                        ) : (
                          <span className="bg-success/10 text-success px-2 py-1 rounded text-xs font-semibold">Active</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

      </div>
    </main>
  );
}
