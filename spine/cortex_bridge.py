from flask import Flask, request, jsonify, send_file
import os
import subprocess
import time
import requests

# Fix HF Cache permissions
os.environ["HF_HOME"] = "/Users/mirror-admin/.cache/huggingface"

import subprocess
try:
    import mlx_whisper
    USE_MLX = True
    print("⟡ Loading MLX-Whisper (Apple Silicon Optimized)...")
except ImportError:
    import whisper
    USE_MLX = False
    print("⟡ Loading OpenAI-Whisper (Standard)...")
    model = whisper.load_model("base")

app = Flask(__name__)
SAVE_DIR = "/Users/mirror-admin/Documents/MirrorDNA-Vault/00_INBOX"
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>MirrorLink</title>
    <style>
        body { background: #000; color: #0f0; font-family: monospace; display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100vh; margin: 0; }
        .btn { width: 200px; height: 200px; border-radius: 50%; border: 2px solid #0f0; background: #000; color: #0f0; font-size: 24px; cursor: pointer; transition: all 0.2s; display: flex; align-items: center; justify-content: center; user-select: none; }
        .btn:active, .btn.recording { background: #0f0; color: #000; box-shadow: 0 0 50px #0f0; }
        #log { margin-top: 20px; text-align: center; font-size: 14px; max-width: 90%; }
        input { display: none; }
    </style>
</head>
<body>
    <div id="mic" class="btn">HOLD<br>TO<br>SPEAK</div>
    <div id="log">System Online</div>

    <script>
        const btn = document.getElementById('mic');
        const log = document.getElementById('log');
        let chunks = [];
        let recorder = null;

        async function start() {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                recorder = new MediaRecorder(stream);
                recorder.ondataavailable = e => chunks.push(e.data);
                recorder.onstop = send;
                
                btn.ontouchstart = (e) => { e.preventDefault(); chunks=[]; recorder.start(); btn.classList.add('recording'); log.innerText = "Recording..."; };
                btn.onmousedown = (e) => { e.preventDefault(); chunks=[]; recorder.start(); btn.classList.add('recording'); log.innerText = "Recording..."; };
                
                const stop = (e) => { e.preventDefault(); if(recorder.state === 'recording') recorder.stop(); btn.classList.remove('recording'); log.innerText = "Sending..."; };
                btn.onmouseup = stop;
                btn.ontouchend = stop;
                
            } catch (e) {
                log.innerText = "Error: " + e;
            }
        }



        async function send() {
            if (chunks.length === 0) return;
            const blob = new Blob(chunks, { type: 'audio/webm' });
            const fd = new FormData();
            fd.append('audio', blob, 'cmd.webm');
            
            try {
                log.innerText = "Thinking...";
                const res = await fetch('/command', { method: 'POST', body: fd });
                
                if (res.headers.get("content-type") === "audio/mpeg") {
                    log.innerText = "Speaking...";
                    const audioBlob = await res.blob();
                    const url = URL.createObjectURL(audioBlob);
                    const audio = new Audio(url);
                    audio.play();
                    log.innerText = "Clone Identity Active.";
                } else {
                    const txt = await res.text();
                    log.innerText = txt;
                }
                
            } catch (e) {
                log.innerText = "Network Error";
            }
        }

        start();
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return HTML_TEMPLATE

@app.route('/command', methods=['POST'])
def command():
    print("⟡ Audio Signal Received")
    if 'audio' not in request.files:
        return "No audio", 400
    
    file = request.files['audio']
    path = os.path.join(SAVE_DIR, "voice_command.webm")
    file.save(path)
    
    # 1. Transcribe (Whisper)
    print("Transcribing...")
    try:
        if USE_MLX:
            # MLX Whisper
            result = mlx_whisper.transcribe(path, path_or_hf_repo="mlx-community/whisper-large-v3-turbo")
            text = result["text"].strip()
        else:
            # CPU Whisper
            result = model.transcribe(path)
            text = result["text"].strip()
            
        print(f"Heard: {text}")
        
        if not text: return "I didn't hear anything."
        
        # 2. Intelligence (Ollama Phi-4)
        print(f"Asking Phi-4: {text}")
        r = requests.post('http://localhost:11434/api/generate', 
            json={'model': 'phi4:latest', 'prompt': text, 'stream': False})
        
        if r.status_code == 200:
            ans = r.json()['response']
            print(f"Answer: {ans[:50]}...")
            
            # Generate Mac Voice Audio
            # Clean up text for 'say'
            clean_ans = ans.replace('"', '').replace("'", "")
            subprocess.run(f"say -o {SAVE_DIR}/response.aiff '{clean_ans}'", shell=True)
            # Convert to mp3 for browser compatibility
            subprocess.run(f"ffmpeg -y -i {SAVE_DIR}/response.aiff {SAVE_DIR}/response.mp3", shell=True, stderr=subprocess.DEVNULL)
            
            return send_file(f"{SAVE_DIR}/response.mp3", mimetype="audio/mpeg")
        else:
            return "My AI Brain is offline."
            
    except Exception as e:
        print(f"Error: {e}")
        return f"Error: {e}"

if __name__ == '__main__':
    print("⟡ MirrorBrain Cortex Web Interface Active on 5002...")
    # SSL required for getUserMedia on non-localhost
    print("⟡ Serving Securely (Tailscale Certs)...")
    
    # Paths to Tailscale Certs
    CERT = "mirror-admins-mac-mini.taildfee74.ts.net.crt"
    KEY = "mirror-admins-mac-mini.taildfee74.ts.net.key"
    
    # Check if certs exist in current dir (where we ran the command) or ~/.mirrordna
    # We ran it in ~/.mirrordna via cwd
    BASE = "/Users/mirror-admin/.mirrordna"
    CERT_PATH = os.path.join(BASE, CERT)
    KEY_PATH = os.path.join(BASE, KEY)
    
    # SSL handled by Tailscale Serve (TLS Termination)
    # We listen on HTTP 5002, Tailscale proxies HTTPS 443 -> HTTP 5002
    print("⟡ Serving internally on 5002 (Tailscale will wrap this)...")
    app.run(host='0.0.0.0', port=5002)
