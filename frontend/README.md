# VoiceDesk Web Client 🎙️💻

Next.js 16 reactive frontend dashboard for VoiceDesk, built with React 19, Tailwind CSS v4, Lucide Icons, and Framer Motion.

## 🚀 Key Features

- **Duplex WebSocket Connection**: Connects to VoiceDesk backend at `ws://127.0.0.1:8000/ws/audio`.
- **Hybrid Speech Recognition**: Uses Native Web Speech API with fallback to MediaRecorder chunking and Groq Whisper ASR.
- **Audio Device Enumeration**: Select active input microphone dynamically with real-time VU meter feedback.
- **Interactive Text Prompt Bar**: Submit text questions directly into the conversational voice stream.
- **Visualizer & Glow Aura**: Real-time frequency bin visualizer synchronized to speech playback and recording.

## 🛠️ Getting Started

### 1. Configuration
Create a `.env.local` file (or copy `.env.example`):
```bash
cp .env.example .env.local
```
Ensure `NEXT_PUBLIC_WS_URL` points to your running backend:
```env
NEXT_PUBLIC_WS_URL=ws://127.0.0.1:8000/ws/audio
```

### 2. Install and Run
```bash
npm install
npm run dev
```

Visit [http://localhost:3000](http://localhost:3000) to start chatting with VoiceDesk!
