# NexusCore SRE — Real-Time Dashboard

A Next.js 14 (App Router) frontend for the NexusCore autonomous agent.

## Features
- **Server-Sent Events (SSE)**: Parses live chunked updates from the backend LangGraph engine using a custom Fetch/TextDecoder implementation.
- **Custom Theming**: Seamless palette swapping powered by Tailwind CSS v4 variables.
- **Terminal Simulator**: Auto-scrolling terminal log reflecting live AI thought processes and patch outputs.

## Setup
```bash
npm install
npm run dev
```

Ensure `NEXT_PUBLIC_API_BASE_URL` in `.env.local` points to your backend instance (default: `http://127.0.0.1:8000`).
