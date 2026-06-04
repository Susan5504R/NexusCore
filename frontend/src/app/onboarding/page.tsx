"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { generateKey, verifyKey } from "../../lib/keysClient";
import { getStoredSaasKey, setStoredSaasKey } from "../../lib/authKey";

export default function OnboardingPage() {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<"common" | "local" | "cloud">("common");

  // --- SaaS API-key flow (generate + verify gates the dashboard) ---
  const [namespace, setNamespace] = useState("");
  const [generating, setGenerating] = useState(false);
  const [generatedKey, setGeneratedKey] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [keyInput, setKeyInput] = useState("");
  const [verifying, setVerifying] = useState(false);
  const [verifyError, setVerifyError] = useState<string | null>(null);
  const [verifiedNamespace, setVerifiedNamespace] = useState<string | null>(null);

  useEffect(() => {
    // Deep-link from the gated dashboard lands here on the Cloud tab.
    if (typeof window !== "undefined" && window.location.search.includes("needkey")) {
      setActiveTab("cloud");
    }
    // If a key was already verified earlier, pre-fill it so the user can re-enter.
    const stored = getStoredSaasKey();
    if (stored) setKeyInput(stored);
  }, []);

  const handleGenerate = async () => {
    setGenerating(true);
    setVerifyError(null);
    try {
      const raw = await generateKey(namespace.trim());
      setGeneratedKey(raw);
      setKeyInput(raw); // pre-fill the verify box with the freshly minted key
    } catch (err) {
      setVerifyError(err instanceof Error ? err.message : "Key generation failed.");
    } finally {
      setGenerating(false);
    }
  };

  const handleVerify = async () => {
    setVerifying(true);
    setVerifyError(null);
    setVerifiedNamespace(null);
    try {
      const result = await verifyKey(keyInput.trim());
      setStoredSaasKey(keyInput.trim());
      setVerifiedNamespace(result.namespace);
    } catch (err) {
      setVerifyError(err instanceof Error ? err.message : "Verification failed.");
    } finally {
      setVerifying(false);
    }
  };

  const copyKey = () => {
    if (!generatedKey) return;
    navigator.clipboard.writeText(generatedKey);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <main className="min-h-screen p-8 transition-colors duration-500 bg-background text-text-main">
      <div className="max-w-4xl mx-auto space-y-8">
        
        {/* Header */}
        <div className="flex justify-between items-center bg-surface p-6 rounded-2xl shadow-xl border border-primary/30">
          <div>
            <h1 className="text-3xl font-extrabold tracking-tight text-transparent bg-clip-text bg-gradient-to-r from-primary to-error drop-shadow-md">
              NexusCore SRE Onboarding
            </h1>
            <p className="text-text-main/90 font-medium mt-1">End-to-End Testing & Deployment Guide</p>
          </div>
          <Link href="/dashboard">
            <button className="px-4 py-2 bg-surface hover:bg-primary/10 border border-primary text-primary rounded-md font-semibold transition-colors shadow-sm">
              Go to SaaS Dashboard &rarr;
            </button>
          </Link>
        </div>

        {/* Navigation Tabs */}
        <div className="flex gap-4 border-b border-primary/20 pb-2">
          <button
            onClick={() => setActiveTab("common")}
            className={`px-4 py-2 font-bold rounded-t-lg transition-colors ${activeTab === "common" ? "bg-primary/20 text-primary border-b-2 border-primary" : "text-text-main/70 hover:text-primary hover:bg-primary/10"}`}
          >
            0. Common Setup
          </button>
          <button
            onClick={() => setActiveTab("local")}
            className={`px-4 py-2 font-bold rounded-t-lg transition-colors ${activeTab === "local" ? "bg-primary/20 text-primary border-b-2 border-primary" : "text-text-main/70 hover:text-primary hover:bg-primary/10"}`}
          >
            1. Self-Hosted (Local)
          </button>
          <button
            onClick={() => setActiveTab("cloud")}
            className={`px-4 py-2 font-bold rounded-t-lg transition-colors ${activeTab === "cloud" ? "bg-primary/20 text-primary border-b-2 border-primary" : "text-text-main/70 hover:text-primary hover:bg-primary/10"}`}
          >
            2. Cloud-Managed (SaaS)
          </button>
        </div>

        {/* Content Area */}
        <div className="bg-surface p-8 rounded-2xl shadow-lg border border-primary/20 space-y-6">
          
          {activeTab === "common" && (
            <div className="space-y-6 animate-in fade-in duration-300">
              <h2 className="text-2xl font-bold text-primary">🛠️ Step 0: Common Setup (Do This First!)</h2>
              <p className="text-text-main/80">No matter which mode you want to test, you first need to get the basic dependencies installed.</p>
              
              <div className="bg-background/50 p-4 rounded-lg border border-primary/10">
                <h3 className="text-lg font-semibold mb-2">Prerequisites</h3>
                <ul className="list-disc list-inside space-y-1 text-text-main/90">
                  <li><strong>Python 3.10+</strong></li>
                  <li><strong>Node.js 18+</strong></li>
                  <li><strong>Docker Desktop</strong> (MUST be open and running in the background!)</li>
                </ul>
              </div>

              <div className="space-y-4">
                <h3 className="text-xl font-bold">1. Install Backend Dependencies</h3>
                <p className="text-text-main/80 text-sm">Open a PowerShell terminal, navigate to the project folder, and run:</p>
                <pre className="bg-gray-900 text-green-400 p-4 rounded-md overflow-x-auto shadow-inner border border-gray-700">
                  <code>make install</code>
                </pre>
                <p className="text-xs text-text-main/60 italic">(This will create a Python virtual environment and install everything the backend needs).</p>
              </div>

              <div className="space-y-4">
                <h3 className="text-xl font-bold">2. Install Frontend Dependencies</h3>
                <pre className="bg-gray-900 text-green-400 p-4 rounded-md overflow-x-auto shadow-inner border border-gray-700">
                  <code>cd frontend{"\n"}npm ci{"\n"}cd ..</code>
                </pre>
              </div>
            </div>
          )}

          {activeTab === "local" && (
            <div className="space-y-6 animate-in fade-in duration-300">
              <h2 className="text-2xl font-bold text-primary">🚀 Testing Method 1: Self-Hosted / Local Mode</h2>
              <p className="text-text-main/80">In this mode, everything runs on your machine. The vector database (Chroma) runs in Docker, and the system executes self-healing patches using your local Docker daemon.</p>

              <div className="space-y-4">
                <h3 className="text-xl font-bold">1. Configure the Environment</h3>
                <pre className="bg-gray-900 text-green-400 p-4 rounded-md overflow-x-auto shadow-inner border border-gray-700">
                  <code>cp backend/.env.example backend/.env</code>
                </pre>
                <p className="text-text-main/80 text-sm">Open <code>backend/.env</code> in any text editor and make sure it looks like this:</p>
                <pre className="bg-gray-900 text-blue-300 p-4 rounded-md overflow-x-auto shadow-inner border border-gray-700">
                  <code>DEPLOYMENT_MODE=local{"\n"}SANDBOX_MODE=docker{"\n"}CHROMA_HOST=localhost{"\n"}GEMINI_API_KEY=your_actual_gemini_api_key_here</code>
                </pre>
              </div>

              <div className="space-y-4">
                <h3 className="text-xl font-bold">2. Start the Local Infrastructure (Docker)</h3>
                <pre className="bg-gray-900 text-green-400 p-4 rounded-md overflow-x-auto shadow-inner border border-gray-700">
                  <code>make docker-up</code>
                </pre>
              </div>

              <div className="space-y-4">
                <h3 className="text-xl font-bold">3. Start the Backend Server</h3>
                <p className="text-text-main/80 text-sm">Open a <strong>new</strong> PowerShell window, navigate to the project, and run:</p>
                <pre className="bg-gray-900 text-green-400 p-4 rounded-md overflow-x-auto shadow-inner border border-gray-700">
                  <code>cd backend{"\n"}.\.venv\Scripts\activate{"\n"}uvicorn app.main:app --reload</code>
                </pre>
              </div>

              <div className="space-y-4">
                <h3 className="text-xl font-bold">4. Verify it Works!</h3>
                <ul className="list-decimal list-inside space-y-2 text-text-main/90 bg-background/50 p-4 rounded-lg border border-primary/10">
                  <li>Open your browser and go to: <strong>http://localhost:3000</strong></li>
                  <li>You should see a status indicator saying <strong>"Running in Self‑Hosted mode"</strong>.</li>
                  <li><strong>Trigger the AI:</strong> Click on the <strong>"Simulate Spike"</strong> button on the dashboard to artificially trigger a server anomaly.</li>
                  <li><strong>Watch the Magic:</strong> Look at your backend terminal. You should see it detect the anomaly, search the Chroma vector database, generate a code patch using Gemini, and safely test that patch inside a Docker container!</li>
                </ul>
              </div>
              
              <div className="space-y-4">
                <h3 className="text-xl font-bold text-error">5. Clean Up</h3>
                <p className="text-text-main/80 text-sm">When you are done testing local mode, press <code>Ctrl+C</code> in your backend and frontend terminals to stop them, then run:</p>
                <pre className="bg-gray-900 text-red-400 p-4 rounded-md overflow-x-auto shadow-inner border border-gray-700">
                  <code>make docker-down</code>
                </pre>
              </div>
            </div>
          )}

          {activeTab === "cloud" && (
            <div className="space-y-6 animate-in fade-in duration-300">
              <div>
                <h2 className="text-2xl font-bold text-primary">☁️ Cloud-Managed SaaS Mode</h2>
                <p className="text-text-main/80 mt-2">A hosted SaaS architecture backed by <strong>Pinecone</strong>. There is no login — access is gated by a namespace-scoped <code>nx_core_</code> API key. Generate one, verify it, then enter the online SRE dashboard.</p>
              </div>

              {/* === Get Access: generate + verify the API key === */}
              <div className="bg-gradient-to-br from-primary/10 to-blue-600/5 p-6 rounded-2xl border border-primary/30 space-y-5 shadow-lg">
                <h3 className="text-xl font-bold flex items-center gap-2">🔑 Get Access — Generate &amp; Verify your API Key</h3>

                {/* Step A: generate */}
                <div className="space-y-2">
                  <label className="block text-sm font-semibold">A. Generate a tenant key</label>
                  <div className="flex flex-col sm:flex-row gap-2">
                    <input
                      type="text"
                      value={namespace}
                      onChange={e => setNamespace(e.target.value)}
                      placeholder="namespace e.g. acme-corp"
                      className="flex-1 bg-background border border-primary/30 rounded-lg px-3 py-2 text-sm text-text-main focus:outline-none focus:border-primary transition-colors"
                    />
                    <button
                      onClick={handleGenerate}
                      disabled={generating || !namespace.trim()}
                      className="px-5 py-2 bg-primary/15 border border-primary/40 text-primary rounded-lg text-sm font-semibold hover:bg-primary/25 transition-all disabled:opacity-50"
                    >
                      {generating ? "Generating…" : "Generate Key"}
                    </button>
                  </div>
                  {generatedKey && (
                    <div className="mt-2 p-3 bg-success/10 border border-success/30 rounded-xl space-y-1">
                      <p className="text-xs text-text-main/70">Copy this now — it will not be shown again.</p>
                      <div className="flex items-center gap-2">
                        <code className="flex-1 bg-background p-2 rounded text-xs text-text-main truncate select-all">{generatedKey}</code>
                        <button onClick={copyKey} className="px-3 py-2 bg-success/80 hover:bg-success text-white rounded text-xs font-semibold transition-colors">
                          {copied ? "Copied" : "Copy"}
                        </button>
                      </div>
                    </div>
                  )}
                </div>

                {/* Step B: verify */}
                <div className="space-y-2">
                  <label className="block text-sm font-semibold">B. Verify your key</label>
                  <div className="flex flex-col sm:flex-row gap-2">
                    <input
                      type="text"
                      value={keyInput}
                      onChange={e => { setKeyInput(e.target.value); setVerifiedNamespace(null); }}
                      placeholder="nx_core_…"
                      className="flex-1 bg-background border border-primary/30 rounded-lg px-3 py-2 text-sm font-mono text-text-main focus:outline-none focus:border-primary transition-colors"
                    />
                    <button
                      onClick={handleVerify}
                      disabled={verifying || !keyInput.trim()}
                      className="px-5 py-2 bg-primary/15 border border-primary/40 text-primary rounded-lg text-sm font-semibold hover:bg-primary/25 transition-all disabled:opacity-50"
                    >
                      {verifying ? "Verifying…" : "Verify"}
                    </button>
                  </div>
                  {verifyError && <p className="text-sm text-error font-medium">✗ {verifyError}</p>}
                  {verifiedNamespace && <p className="text-sm text-success font-semibold">✓ Verified — namespace &ldquo;{verifiedNamespace}&rdquo;. You&apos;re ready.</p>}
                </div>

                {/* Step C: enter the dashboard */}
                <button
                  onClick={() => router.push("/dashboard")}
                  disabled={!verifiedNamespace}
                  className="w-full px-6 py-3 bg-gradient-to-r from-primary to-blue-600 hover:from-primary/80 hover:to-blue-500 text-white rounded-lg font-bold shadow-lg transition-transform enabled:hover:scale-[1.02] flex items-center justify-center gap-2 disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  Go to the SaaS Dashboard &rarr;
                </button>
              </div>

              <div className="space-y-4">
                <h3 className="text-xl font-bold">1. Install Daemon Dependencies</h3>
                <p className="text-text-main/80 text-sm">Open a PowerShell window and install the lightweight Python packages required by the daemon:</p>
                <pre className="bg-gray-900 text-green-400 p-4 rounded-md overflow-x-auto shadow-inner border border-gray-700">
                  <code>pip install psutil requests</code>
                </pre>
              </div>

              <div className="space-y-4">
                <h3 className="text-xl font-bold">2. Download the Daemon Script</h3>
                <p className="text-text-main/80 text-sm">Run this command to download the script to your computer:</p>
                <pre className="bg-gray-900 text-green-400 p-4 rounded-md overflow-x-auto shadow-inner border border-gray-700">
                  <code>Invoke-WebRequest -Uri "https://raw.githubusercontent.com/Susan5504R/NexusCore/main/frontend/public/nexus_daemon.py" -OutFile "nexus_daemon.py"</code>
                </pre>
              </div>

              <div className="space-y-4">
                <h3 className="text-xl font-bold">3. Start Pushing Telemetry!</h3>
                <p className="text-text-main/80 text-sm">Run the daemon with your newly generated API key. Use backticks (`) for multi-line commands in PowerShell:</p>
                <pre className="bg-gray-900 text-blue-300 p-4 rounded-md overflow-x-auto shadow-inner border border-gray-700">
                  <code>python nexus_daemon.py `{'\n'}  --api-key nx_core_YOUR_KEY_HERE `{'\n'}  --server-url https://nexuscore-rdc1.onrender.com</code>
                </pre>
              </div>

              <div className="space-y-4">
                <h3 className="text-xl font-bold">4. Verify it Works!</h3>
                <ul className="list-decimal list-inside space-y-2 text-text-main/90 bg-background/50 p-4 rounded-lg border border-primary/10">
                  <li>Your terminal should say <strong>[OK] Telemetry sent</strong> every 5 seconds.</li>
                  <li>Click <strong>Go to the SaaS Dashboard</strong> above.</li>
                  <li>In the dashboard, you will see your active telemetry streaming in!</li>
                </ul>
              </div>

            </div>
          )}

        </div>
      </div>
    </main>
  );
}
