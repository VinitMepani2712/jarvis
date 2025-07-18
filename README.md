# Jarvis 🤖

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Build Status](https://img.shields.io/github/actions/workflow/status/VinitMepani2712/jarvis/ci.yml?branch=master)](https://github.com/VinitMepani2712/jarvis/actions)

Welcome to **Jarvis**, your Windows-based, voice-controlled personal assistant. It listens for a wake word and carries out commands—from opening apps and browsing the web to managing files and system functions—all powered by a local LLM fallback.

## 🚀 Features

* 🎙️ **Voice Activation**: Hotword detection via PicoVoice Porcupine (`"Jarvis"`).
* 📋 **Application Control**: Launch, close, minimize, maximize windows.
* 🌐 **Web Interaction**: Open browsers, perform searches (Google, YouTube, ChatGPT, LinkedIn).
* 📂 **File System Operations**: Create, delete, find, open files & folders.
* 💻 **System Automation**:

  * ⏰ Get time, date, IP address, CPU/RAM/battery status.
  * ⌨️ Type text into active windows (Notepad, VS Code, etc.).
  * 🔌 Power controls (shutdown, restart, lock).
* 🎵 **Media & Volume**:

  * ▶️ Play music from a folder.
  * ⏯️ Play/pause/next/prev track, adjust/mute volume.
* 📸 **Desktop Tools**: Screenshots, screen recording.
* 🤖 **Conversational AI**: GPT4All Llama 3 fallback for chit-chat and non-command queries.

## 🛠️ Tech Stack

| Component               | Library/Tool                                  |
| ----------------------- | --------------------------------------------- |
| 🔑 Wake Word Detection  | `pvporcupine` (PicoVoice Porcupine)           |
| 🎤 Speech-to-Text (STT) | `SpeechRecognition` (Google STT)              |
| 🔊 Text-to-Speech (TTS) | Windows SAPI via `win32com.client`            |
| 🧠 NLU & Fallback       | Regex rules + `gpt4all` with Llama 3 Instruct |
| 🖥️ Desktop Automation  | `pyautogui`, `pygetwindow`, `psutil`          |

## 📦 Installation

1. **Clone the repo**

   ```bash
   git clone https://github.com/VinitMepani2712/jarvis.git
   cd jarvis
   ```
2. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```
3. **Configure environment**

   * Copy `.env.example` → `.env`
   * Add your PicoVoice key:

     ```dotenv
     PV_ACCESS_KEY="YOUR_PICOVOICE_ACCESS_KEY"
     ```

## ▶️ Usage

Run the assistant:

```bash
python jarvis_entry.py
```

1. Say **"Jarvis"** to wake.
2. After prompt (**"How can I help you?"**), speak your command.

### Example Commands

| Intent               | Phrase                                  |
| -------------------- | --------------------------------------- |
| Open browser         | "Open browser"                          |
| Google search        | "Search web for the latest Python news" |
| Type text in Notepad | "Type 'Hello world' in notepad"         |
| System info          | "What time is it?"                      |
| Window management    | "Minimize window"                       |
| File operations      | "Create folder 'Project' on Desktop"    |
| Screenshot           | "Take a screenshot"                     |
| Power control        | "Shutdown"                              |
| Tell a joke          | "Tell me a joke"                        |

## 📁 Project Structure

```
├── jarvis_entry.py   # Main script & event loop
├── jarvis_core.py    # STT/TTS, command handlers
├── jarvis_wake.py    # Wake-word detection
├── jarvis_llm.py     # GPT4All integration
├── jarvis_nlu.py     # Intent parsing rules
├── mice.py           # Microphone device utility
├── requirements.txt  # Dependency list
└── .env.example      # Sample environment variables
```

## 🤝 Contributing

1. Fork the repo
2. Create a feature branch
3. Submit a pull request

## 📄 License

This project is licensed under the [MIT License](LICENSE).
