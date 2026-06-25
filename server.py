from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
from dotenv import load_dotenv
import groq
import os
import threading
from pynput import keyboard
from collections import deque
import PyPDF2
import docx
import json

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'secret!')
socketio = SocketIO(app, cors_allowed_origins="*")

GROQ_API_KEY = os.getenv('GROQ_API_KEY')
TOGGLE_KEY = keyboard.Key.end

# Global state
listening_enabled = False
connected_clients = set()

# NEW: Enhanced conversation history with three fields
# Each entry: {interviewer_q, model_suggestion, your_actual_answer}
conversation_history = deque(maxlen=10)
knowledge_base = {"resume": "", "projects": "", "readme": ""}

# Track pending question for answer logging
pending_question = None
pending_suggestion = None

PROJECT_PRIORITIES = """
TOPIC PRIORITIES:
• ML/AI → me0-mini_mvp
• Leadership → RadicalX  
• Maintenance → me0-mini_mvp + Openkora
• High-stakes/Financial/Gov → CBDC Rwanda (tie to CPA tax work)
• Scale/Impact → CBDC Rwanda
"""

def load_knowledge_base():
    global knowledge_base
    if os.path.exists('knowledge_base.json'):
        with open('knowledge_base.json', 'r') as f:
            knowledge_base = json.load(f)
            print(f"📚 Loaded: Resume={len(knowledge_base.get('resume',''))}, Projects={len(knowledge_base.get('projects',''))}, README={len(knowledge_base.get('readme',''))}")

def save_knowledge_base():
    with open('knowledge_base.json', 'w') as f:
        json.dump(knowledge_base, f)

def extract_pdf_text(filepath):
    text = ""
    try:
        with open(filepath, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                text += page.extract_text() + "\n"
    except Exception as e:
        print(f"Error reading PDF: {e}")
    return text

def extract_docx_text(filepath):
    text = ""
    try:
        doc = docx.Document(filepath)
        for para in doc.paragraphs:
            text += para.text + "\n"
    except Exception as e:
        print(f"Error reading DOCX: {e}")
    return text

def extract_txt_text(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    except Exception as e:
        print(f"Error reading TXT: {e}")
        return ""

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/mic')
def mic():
    return render_template('mic.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return {'error': 'No file'}, 400
    
    file = request.files['file']
    file_type = request.form.get('type', 'resume')
    
    if file.filename == '':
        return {'error': 'No filename'}, 400
    
    temp_path = f"temp_{file.filename}"
    file.save(temp_path)
    
    if file.filename.endswith('.pdf'):
        text = extract_pdf_text(temp_path)
    elif file.filename.endswith('.docx') or file.filename.endswith('.doc'):
        text = extract_docx_text(temp_path)
    elif file.filename.endswith('.txt') or file.filename.endswith('.md'):
        text = extract_txt_text(temp_path)
    else:
        text = file.read().decode('utf-8', errors='ignore')
    
    os.remove(temp_path)
    
    if file_type in knowledge_base:
        knowledge_base[file_type] = text
    
    save_knowledge_base()
    
    return {'success': True, 'chars': len(text), 'preview': text[:200]}

@socketio.on('connect')
def handle_connect():
    connected_clients.add(request.sid)
    emit('status', {'listening': listening_enabled})
    emit('history', {'history': list(conversation_history)})
    emit('knowledge_status', {
        'resume_loaded': len(knowledge_base.get('resume','')) > 0,
        'projects_loaded': len(knowledge_base.get('projects','')) > 0,
        'readme_loaded': len(knowledge_base.get('readme','')) > 0,
        'resume_preview': knowledge_base.get('resume','')[:300],
        'projects_preview': knowledge_base.get('projects','')[:300],
        'readme_preview': knowledge_base.get('readme','')[:300]
    })

@socketio.on('disconnect')
def handle_disconnect():
    connected_clients.discard(request.sid)

def format_history_for_prompt():
    """Format conversation history for the LLM prompt"""
    if not conversation_history:
        return ""
    
    formatted = "\n\nPREVIOUS CONVERSATION:\n"
    for i, entry in enumerate(conversation_history, 1):
        formatted += f"\n--- Turn {i} ---\n"
        formatted += f"Interviewer: {entry.get('interviewer_q', 'N/A')}\n"
        formatted += f"You said: {entry.get('your_actual_answer', entry.get('answer', 'N/A'))}\n"
    return formatted

@socketio.on('question')
def handle_question(data):
    global listening_enabled, pending_question, pending_suggestion
    if not listening_enabled:
        return
    
    question = data.get('text', '').lower()
    if not question or len(question.strip()) < 5:
        return
    
    print(f"📝 Question: {question[:80]}...")
    
    client = groq.Groq(api_key=GROQ_API_KEY)
    
    system_content = f"""You are a senior software engineer in a technical interview. Match response length to question complexity.

LENGTH GUIDELINES:
• SIMPLE questions: 2-3 bullets, 5-8 words each
• MEDIUM questions: 3-5 bullets, 10-15 words each
• COMPLEX questions: 5-7 bullets max, OR 2-3 short paragraphs (max 20 words each)

HARD LIMITS:
• Max 7 bullets total
• Max 3 short paragraphs
• Each bullet: max 20 words
• Each paragraph: max 25 words

RULES:
• Use bullets by default, paragraphs only for complex flow
• NO "I think", "In my opinion", "Additionally", "Furthermore"
• Use concrete numbers and tech names
• Speak as yourself (first person)
• Prioritize readability over completeness

{PROJECT_PRIORITIES}

YOUR BACKGROUND:
"""
    
    if knowledge_base.get('resume'):
        system_content += f"\nRESUME:\n{knowledge_base['resume'][:2000]}"
    
    if knowledge_base.get('projects'):
        system_content += f"\n\nPROJECTS:\n{knowledge_base['projects'][:3000]}"
    
    if knowledge_base.get('readme'):
        system_content += f"\n\nREADME:\n{knowledge_base['readme'][:1500]}"
    
    # Add conversation history for context
    system_content += format_history_for_prompt()
    
    system_content += "\n\nAnalyze question complexity and respond with appropriate length. Never ramble."

    messages = [{"role": "system", "content": system_content}]
    messages.append({"role": "user", "content": data.get('text', '')})
    
    full_answer = ""
    pending_question = data.get('text', '')
    
    try:
        stream = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            stream=True,
            max_tokens=300,
            temperature=0.4
        )
        
        for chunk in stream:
            if chunk.choices[0].delta.content:
                text = chunk.choices[0].delta.content
                full_answer += text
                emit('answer_chunk', {'text': text})
        
        # Store pending suggestion - waiting for user's actual answer via log_answer
        pending_suggestion = full_answer
        
        # Temporary entry (will be updated when user logs their answer)
        conversation_history.append({
            'interviewer_q': pending_question,
            'answer': full_answer,  # AI suggestion
            'model_suggestion': full_answer,
            'your_actual_answer': '[Waiting for your spoken answer...]'
        })
        
        for sid in list(connected_clients):
            try:
                socketio.emit('history', {'history': list(conversation_history)}, room=sid)
            except:
                pass
                
    except Exception as e:
        emit('error', {'message': str(e)})

@socketio.on('log_answer')
def handle_log_answer(data):
    """Receive the user's actual spoken answer from mic tab"""
    global pending_question, pending_suggestion
    
    user_answer = data.get('text', '').strip()
    if not user_answer:
        return
    
    print(f"🎤 Logged user answer: {user_answer[:80]}...")
    
    # Update the most recent history entry with user's actual answer
    if conversation_history:
        last_entry = conversation_history[-1]
        last_entry['your_actual_answer'] = user_answer
        
        # If we have pending question/suggestion, ensure they're set
        if pending_question:
            last_entry['interviewer_q'] = pending_question
        if pending_suggestion:
            last_entry['model_suggestion'] = pending_suggestion
        
        # Broadcast updated history to all clients
        for sid in list(connected_clients):
            try:
                socketio.emit('history', {'history': list(conversation_history)}, room=sid)
                socketio.emit('answer_logged', {
                    'question': last_entry.get('interviewer_q', ''),
                    'your_answer': user_answer
                }, room=sid)
            except:
                pass
    
    # Clear pending
    pending_question = None
    pending_suggestion = None

def toggle_listening():
    global listening_enabled
    listening_enabled = not listening_enabled
    status = "🟢 ACTIVE" if listening_enabled else "🔴 PAUSED"
    print(f"\n{status} - Press [END] to {'pause' if listening_enabled else 'activate'}")
    
    for sid in list(connected_clients):
        try:
            socketio.emit('toggle', {'listening': listening_enabled}, room=sid)
        except:
            pass

def on_press(key):
    if key == TOGGLE_KEY:
        toggle_listening()

def start_hotkey_listener():
    listener = keyboard.Listener(on_press=on_press)
    listener.daemon = True
    listener.start()
    print(f"\n⌨️  Hotkey ready: Press [END] to toggle")
    print("🔴 PAUSED - Browser ready, waiting for activation...")

@socketio.on('toggle_request')
def handle_toggle_request():
    toggle_listening()

@socketio.on('clear_history')
def handle_clear_history():
    conversation_history.clear()
    for sid in list(connected_clients):
        try:
            socketio.emit('history', {'history': []}, room=sid)
        except:
            pass

@socketio.on('clear_knowledge')
def handle_clear_knowledge():
    knowledge_base['resume'] = ""
    knowledge_base['projects'] = ""
    knowledge_base['readme'] = ""
    save_knowledge_base()
    for sid in list(connected_clients):
        try:
            socketio.emit('knowledge_status', {
                'resume_loaded': False,
                'projects_loaded': False,
                'readme_loaded': False
            }, room=sid)
        except:
            pass

if __name__ == '__main__':
    load_knowledge_base()
    threading.Thread(target=start_hotkey_listener, daemon=True).start()
    socketio.run(app, debug=False, port=5000)
