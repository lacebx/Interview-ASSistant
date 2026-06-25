# Interview Assistant

A real-time AI interview coaching tool that helps you articulate your existing experience more effectively during technical interviews. Think of it as a "memory index" for your career—not a replacement for it.

> **Philosophy**: This tool is designed to help you **remember and articulate what you already know**, not to fabricate expertise you don't have. Use it as stepping stones, not robot legs.

> its currently crappy since you need to have like 3 tabs open and focusing on the microphone one.. ik its such a drag but im lazy to make it better now, working on other ideas and loathing self

***

## What It Does

Interview Assistant listens to interview questions in real-time and instantly surfaces relevant points from your actual experience—projects you've built, technologies you've used, and challenges you've overcome. It then streams contextual suggestions that you **paraphrase in your own words**.

**Key Principle**: The knowledge base should only contain things you've actually done. The AI helps you connect the dots and structure your thoughts—it doesn't invent them for you.

## How It Works

1. **Upload Your Experience** → Resume, project READMEs, documentation of your actual work
2. **Capture Interview Audio** → Browser transcribes the interviewer's questions via Web Speech API
3. **Get Contextual Suggestions** → AI surfaces relevant experience from your knowledge base
4. **Speak Naturally** → Paraphrase the suggestions; don't read them verbatim
5. **Log Your Answer** → Record what you actually said to build conversation context

## Quick Start

### Prerequisites

- Python 3.9+
- Chrome or Edge browser
- [VB-Audio Virtual Cable](https://vb-audio.com/Cable/index.htm) (Windows) or [BlackHole](https://github.com/ExistentialAudio/BlackHole) (Mac)
- A [Groq API key](https://console.groq.com/) (free tier available)

### Installation

```bash
git clone https://github.com/yourusername/interview-assistant.git
cd interview-assistant

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install flask flask-socketio groq pypdf2 python-docx pynput python-dotenv

# Set up environment variables
echo "GROQ_API_KEY=your_key_here" > .env
echo "SECRET_KEY=your_secret_here" >> .env
```

### Running

```bash
python server.py
```

Then:

- Open `http://localhost:5000` in Chrome (Tab 1 - Interviewer Audio and where you see model suggestions or answers to questions asked.)
- Open `http://localhost:5000/mic` in Chrome (Tab 2 - Your Mic, with transcription of what you are saying)
- Configure VB-CABLE: Set `CABLE Input` as default playback in Windows Sound settings
- In Tab 1, select `CABLE Output` as microphone source
- In Tab 2, select your physical microphone
- Press `[END]` to activate listening

## Usage Workflow

| Step | Action | Purpose |
|------|--------|---------|
| 1 | Upload resume/projects | Build your knowledge index |
| 2 | Press `[END]` | Activate listening mode |
| 3 | Interviewer speaks | Auto-transcribed via Web Speech API |
| 4 | AI suggests answers | Pulled from your actual experience |
| 5 | You paraphrase | Speak naturally, don't read verbatim |
| 6 | Press `[SPACE]` (in mic tab) | Log your actual answer to history |

## Configuration

### Knowledge Base

Upload via the web interface:

- **Resume** (PDF/TXT) - Your background and skills
- **Projects** (DOCX/TXT) - Detailed project descriptions(all projects you've ever worked on)
- **README** (MD/TXT) - Technical documentation(Any more details you would like for the model to know)

All data is stored locally in `knowledge_base.json`.

### Smart Response Rules

The system automatically adjusts response length:

- **Simple questions** (definitions, preferences): 2-3 bullets, 5-8 words
- **Medium questions** (how you did something): 3-5 bullets, 10-15 words
- **Complex questions** (architecture, design): 5-7 bullets or 2-3 short paragraphs

**You can change that to your liking**

## Ethical Use Guidelines

### DO:

- Fill knowledge base only with experience you actually have
- Use suggestions as memory prompts, not scripts
- Paraphrase everything in your natural speaking style
- Disclose to interviewers if required by their policy

### DON'T:

- Invent projects or skills you don't possess
- Read AI suggestions verbatim without understanding them
- Use this to fake expertise in areas you've never worked in
- Treat it as a "cheat code" rather than a memory aid

Remember: The goal is to help you articulate your legitimate experience under pressure—not to misrepresent your capabilities.

## Technical Architecture

```text
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Browser Tab 1  │────▶│  Flask-SocketIO  │────▶│   Groq API      │
│ (Interviewer    │     │  Python Server   │     │  (LLM + Fast    │
│  Audio via      │◄────│                  │◄────│   Inference)    │
│  VB-CABLE)      │     └──────────────────┘     └─────────────────┘
└─────────────────┘              │
                                 ▼
┌─────────────────┐     ┌──────────────────┐
│  Browser Tab 2  │◄────│  Knowledge Base  │
│ (Your Mic -     │     │  (Local JSON)    │
│  SPACE to log)  │     └──────────────────┘
└─────────────────┘
```

- **Transcription**: Web Speech API (browser-native, no cloud, currently supporting only chromium)
- **LLM**: Groq API (`llama-3.3-70b-versatile`, I currently have it use the slightly smaller model as is faster, streaming)
- **Communication**: Socket.IO for real-time bidirectional messaging
- **Storage**: Local JSON files (no external database)

## Why Open Source?

This project is open source because it values:

- **Transparency**: You should know exactly what the tool does with your data
- **Customization**: Everyone's interview style is different—fork and adapt
- **Accessibility**: Interview prep tools shouldn't be paywalled
- **Community**: Better ideas come from many perspectives

## Contributing

Contributions are welcome. Areas of interest include:

- Better audio source handling (eliminate VB-CABLE requirement)
- Support for more document formats
- Improved silence detection algorithms
- UI/UX enhancements
- Documentation translations

Please read the Contributing Guide and Code of Conduct.

## License

MIT License - See `LICENSE`

## Disclaimer

This tool is provided for educational and personal development purposes. Users are responsible for complying with the policies of their interviewers and employers. The maintainers do not endorse using this tool to misrepresent skills or experience.

Use responsibly. Interview integrity matters.

> "The best interview performance comes from authentic experience, well-articulated.... I think, might or might not be"
