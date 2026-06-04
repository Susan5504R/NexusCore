# NexusCore End-to-End Testing Guide

Welcome to the **NexusCore SRE** testing guide! This document is designed for users who want a simple, step-by-step, copy-paste guide to verify that the system works exactly as expected in both **Self-Hosted** (Local) and **Cloud-Managed** (SaaS) deployment modes.

---

## 🛠️ Step 0: Common Setup (Do This First!)

No matter which mode you want to test, you first need to get the basic dependencies installed.

### Prerequisites
Make sure you have installed on your computer:
- **Python 3.10+** 
- **Node.js 18+**
- **Docker Desktop** (MUST be open and running in the background!)

### 1. Install Backend Dependencies
Open a PowerShell terminal, navigate to the project folder, and run:
```powershell
make install
```
*(This will create a Python virtual environment and install everything the backend needs).*

### 2. Install Frontend Dependencies
```powershell
cd frontend
npm ci
cd ..
```

---

## 🚀 Testing Method 1: Self-Hosted / Local Mode

In this mode, everything runs on your machine. The vector database (Chroma) runs in Docker, and the system executes self-healing patches using your local Docker daemon.

### 1. Configure the Environment
We need to tell the system to run in `local` mode.
```powershell
# Copy the template env file
cp backend/.env.example backend/.env
```
Open `backend/.env` in any text editor and make sure it looks like this:
```ini
DEPLOYMENT_MODE=local
SANDBOX_MODE=docker
CHROMA_HOST=localhost
GEMINI_API_KEY=your_actual_gemini_api_key_here
```
*(You must provide a real Gemini API Key for the AI to write code patches).*

### 2. Start the Local Infrastructure (Docker)
This starts the local Chroma database.
```powershell
make docker-up
```

### 3. Start the Backend Server
Open a **new** PowerShell window, navigate to the project, and run:
```powershell
cd backend
venv\Scripts\activate
uvicorn app.main:app --reload
```
*(Wait until you see "Application startup complete" in the console).*

### 4. Start the Frontend Dashboard
Open a **third** PowerShell window, navigate to the project, and run:
```powershell
cd frontend
npm run dev
```

### 5. Verify it Works!
1. Open your browser and go to: **http://localhost:3000**
2. You should see a status indicator saying **"Running in Self‑Hosted mode"**.
3. **Trigger the AI:** Click on the **"Simulate Spike"** button on the dashboard to artificially trigger a server anomaly.
4. **Watch the Magic:** Look at your backend terminal. You should see it detect the anomaly, search the Chroma vector database, generate a code patch using Gemini, and safely test that patch inside a Docker container!

### 6. Clean Up
When you are done testing local mode, press `Ctrl+C` in your backend and frontend terminals to stop them, then run:
```powershell
make docker-down
```

---

## ☁️ Testing Method 2: Cloud-Managed SaaS Mode

In this mode, the system simulates a hosted SaaS architecture. It uses **Pinecone** as a remote vector database instead of local Chroma, and it simulates sandbox code patches locally (as Render free-tier doesn't support nested Docker).

### 1. Configure the Environment for the Cloud
Open your `backend/.env` file and change the values to this:
```ini
DEPLOYMENT_MODE=cloud
SANDBOX_MODE=subprocess
GEMINI_API_KEY=your_actual_gemini_api_key_here
PINECONE_API_KEY=your_actual_pinecone_api_key_here
```
*(Note: You now need a Pinecone API key as well!)*

### 2. Start the Backend Server
Open a PowerShell window, navigate to the project, and run:
```powershell
cd backend
.\.venv\Scripts\activate
uvicorn app.main:app --reload
```
*(Notice we did NOT run `make docker-up` this time! The database is in the cloud).*

### 3. Start the Frontend Dashboard
Open another PowerShell window, navigate to the project, and run:
```powershell
cd frontend
npm run dev
```

### 4. Verify it Works!
1. Open your browser and go to: **http://localhost:3000**
2. You should now see a status indicator saying **"Running in Cloud‑Managed mode"**.
3. **Trigger the AI:** Click on the **"Simulate Spike"** button on the dashboard.
4. **Watch the Magic:** Look at your backend terminal. This time, you will see it connect to your remote **Pinecone** index to grab context, generate the patch via Gemini, and test the patch using the `subprocess` Sandbox mode!

---

## 🧪 Automated Testing (Optional)

If you don't want to click around the UI and just want to mathematically prove the code works, you can run the automated test suite!

**Run Backend Unit Tests (Fast):**
```powershell
make test
```

**Run End-to-End UI Tests (Playwright):**
```powershell
# You only need to run this install command once
cd frontend
npx playwright install
cd ..

# Run the automated browser tests
make e2e
```
