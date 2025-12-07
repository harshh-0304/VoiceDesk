# VoiceDesk – AI Voice Support Agent

VoiceDesk is a Python-based Voice AI system that listens to user speech, converts it to text using Whisper ASR, generates intelligent responses using an LLM, and replies back using Text‑to‑Speech (TTS). It simulates a real customer‑support voice agent with flow control, persona prompting, and natural interactions.

---

## 🚀 Features
- 🎤 Voice input via microphone  
- 🧠 Whisper ASR → converts speech to text  
- 🤖 LLM response generation with structured system prompts  
- 🔊 ElevenLabs / TTS output  
- 🔁 Continuous voice conversation loop  
- 💬 Persona-based dialogue  
- ⚠️ Error handling & graceful fallbacks  

---

## 🧠 Architecture
1. User speaks  
2. Microphone records audio  
3. Whisper converts audio → text  
4. LLM processes the text with system prompt  
5. TTS converts text → audio  
6. Bot speaks response  
7. Loop continues with memory  

---

## 📁 Project Structure
```
VoiceDesk/
│── main.py
│── asr.py
│── llm.py
│── tts.py
│── memory.py
│── prompts/
│     └── system_prompt.txt
│── utils/
│     └── audio.py
│── requirements.txt
│── README.md
```

---

## 🔧 Installation

### 1. Clone the project
```
git clone https://github.com/yourusername/VoiceDesk.git
cd VoiceDesk
```

### 2. Install dependencies
```
pip install -r requirements.txt
```

### 3. Add API Keys  
Create `.env` file:
```
OPENAI_API_KEY=your_key
ELEVEN_API_KEY=your_key
```

---

## ▶️ Run the Project
```
python main.py
```

Speak when prompted. The bot will reply with natural voice.

---

## 🛠️ Core Technologies
- Python  
- OpenAI Whisper ASR  
- GPT LLM  
- ElevenLabs TTS  
- PyAudio  
- Playsound  

---

## 📌 System Prompt (Persona)
Found in: `prompts/system_prompt.txt`
```
You are VoiceDesk, a friendly and professional AI support agent.
Speak concisely.
Always ask a follow-up question.
Use simple and helpful tone.
```

---

## 🌱 Future Enhancements
- Real-time streaming ASR  
- Sentiment-based emotional TTS  
- Multi-language support  
- FastAPI backend & web UI  
- Conversation analytics  

---

## 🏆 Author
Harsh (Kiyo) Jadav  
Aspiring AI Engineer – Voice & Conversational AI  
# VoiceDesk
