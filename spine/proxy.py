"""
SYSTEM: OMEGA Proxy
VaultID: AMOS://ProjectOMEGA/Proxy/v1.0
GlyphSig: ⟡⟦PROXY⟧ · ⟡⟦SOVEREIGN⟧

The Gateway to Sovereignty.
Intercepts Chat Completions, Injects Symbiotic Context, and Proxies to Ollama.
"""

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse
import requests
import json
import uvicorn
from contextlib import asynccontextmanager

from spine.interpreter import SymbioticInterpreter

# Configuration
OLLAMA_URL = "http://localhost:11434/v1/chat/completions"
PROXY_PORT = 5500

# Global Interpreter
interpreter = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global interpreter
    print("⟡ OMEGA: Initializing Symbiotic Spine...")
    interpreter = SymbioticInterpreter()
    print("⟡ OMEGA: Spine Online.")
    yield
    print("⟡ OMEGA: Shutting Down.")

app = FastAPI(lifespan=lifespan)

@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    """
    The Core Symbiotic Injection Loop.
    """
    try:
        body = await request.json()
        messages = body.get("messages", [])
        
        # 1. Extract User Input
        user_input = ""
        for msg in reversed(messages):
            if msg["role"] == "user":
                user_input = msg["content"]
                break
        
        if not user_input:
             # Pass-through if no user input (rare)
             return await forward_to_ollama(body)

        # 2. Symbiotic Processing (Memory + Rights + prompt gen)
        print(f"⟡ OMEGA: Intercepting -> '{user_input[:30]}...'")
        symbiotic_prompt = interpreter.process(user_input)
        
        # 3. Inject System Prompt
        # We replace the user's message with the FULL context from the interpreter
        # OR we prepend a System message.
        # Strategy: Replace the SYSTEM message if it exists, or add one.
        
        new_messages = []
        system_injected = False
        
        # Add our Constructed System Prompt
        new_messages.append({"role": "system", "content": symbiotic_prompt})
        
        # Keep history but filter out old system prompts to avoid confusion?
        # For MVP, we simply append the user message interaction history (omitted for brevity in MVP)
        # Actually, standard behavior is: System (Context) + History + New User Message.
        # But 'symbiotic_prompt' ALREADY contains the user input at the end!
        # So we send: [System (with user input embedded)]? 
        # No, 'UniversalDecoder' output ends with 'USER: {user_input}'.
        # So we can just send that as a single prompts task?
        
        # Let's align with OpenAI API.
        # We will use the 'symbiotic_prompt' as the USER message content? 
        # No, better to put it as System.
        # But 'UniversalDecoder' hardcodes the user input into the prompt.
        # So we send ONE message: role='user', content=symbiotic_prompt.
        # This overrides previous history context in the model, managed by Spine instead.
        # This is "Spine-Managed Context".
        
        forward_body = body.copy()
        forward_body["messages"] = [{"role": "user", "content": symbiotic_prompt}]
        
        return await forward_to_ollama(forward_body)

    except Exception as e:
        print(f"✕ OMEGA ERROR: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

async def forward_to_ollama(json_body):
    """Streams the response from Ollama back to the client."""
    resp = requests.post(OLLAMA_URL, json=json_body, stream=True)
    
    def iter_content():
        for chunk in resp.iter_content(chunk_size=1024):
            yield chunk
            
    return StreamingResponse(iter_content(), media_type="application/json")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PROXY_PORT)
