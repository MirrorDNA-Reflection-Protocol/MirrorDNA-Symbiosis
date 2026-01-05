#!/usr/bin/env python3
"""
SUPERAGENT — Multi-AI Consortium v1.0
Strict Epistemic Instrument for Daily Decision Support.

Per Spec:
- Models have distinct lenses (Narrative, Fact, Noise, Nuance)
- Synthesis is strict (Max 15 bullets, Must include "Ignore" section)
- Output to Vault/Superagent/briefings/ + Email

Usage:
    python3 consortium.py digest [--email]
    python3 consortium.py ask "Question"
    python3 consortium.py debate "Topic"
"""

import os
import json
import asyncio
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import argparse

# Load .env
ENV_FILE = Path(__file__).parent / ".env"
if ENV_FILE.exists():
    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            if value:
                os.environ[key] = value

# Config
VAULT = Path.home() / "Library/Mobile Documents/iCloud~md~obsidian/Documents/MirrorDNA-Vault"
BRIEFINGS_DIR = VAULT / "Superagent" / "briefings"
RESULTS_DIR = VAULT / "Superagent" / "consortium_results"
EMAILS = ["paul@activemirror.ai", "pauldesai@gmail.com"]

# Model Roles (Distinct Lenses)
ROLES = {
    "gpt": {
        "role": "Narrative & Framing",
        "prompt": "Identify narratives and framing shifts. What stories are being told? What is the angle?"
    },
    "deepseek": {
        "role": "Facts & Metrics",
        "prompt": "Extract concrete facts, specifications, metrics, and official releases. Ignore opinion."
    },
    "groq": {
        "role": "Noise Filter",
        "prompt": "Detect fast-moving noise vs durable change. What is hype? What will matter in 6 months?"
    },
    "mistral": {
        "role": "Nuance & Dissent",
        "prompt": "Find the dissent. What is being overlooked? What is the counter-narrative?"
    }
}

MODELS = {
    "gpt": {
        "name": "ChatGPT", 
        "api_key_env": "OPENAI_API_KEY",
        "model": "gpt-4o-mini",
        "endpoint": "https://api.openai.com/v1/chat/completions",
        "cost_per_1m": 0.15
    },
    "deepseek": {
        "name": "DeepSeek",
        "api_key_env": "DEEPSEEK_API_KEY",
        "model": "deepseek-chat",
        "endpoint": "https://api.deepseek.com/v1/chat/completions",
        "cost_per_1m": 0.14
    },
    "groq": {
        "name": "Groq",
        "api_key_env": "GROQ_API_KEY",
        "model": "llama-3.3-70b-versatile",
        "endpoint": "https://api.groq.com/openai/v1/chat/completions",
        "cost_per_1m": 0.00
    },
    "mistral": {
        "name": "Mistral",
        "api_key_env": "MISTRAL_API_KEY",
        "model": "mistral-small-latest",
        "endpoint": "https://api.mistral.ai/v1/chat/completions",
        "cost_per_1m": 0.25
    }
}


def ensure_dirs():
    BRIEFINGS_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)


async def query_model(model_key: str, prompt: str, lens_prompt: str = "") -> Dict:
    import aiohttp
    config = MODELS[model_key]
    api_key = os.getenv(config["api_key_env"])
    
    if not api_key:
        return {"model": model_key, "error": "No key"}

    full_prompt = f"LENS: {lens_prompt}\n\nTASK: {prompt}\n\nKeep it concise."
    
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": config["model"],
        "messages": [{"role": "user", "content": full_prompt}],
        "temperature": 0.5
    }
    
    # Adjust for non-OpenAI endpoints if needed (Mistral/DeepSeek/Groq all compatible)
    # Mistral/DeepSeek use /chat/completions compatible schema
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(config["endpoint"], headers=headers, json=payload, timeout=60) as resp:
                if resp.status != 200:
                    return {"model": model_key, "error": f"HTTP {resp.status}"}
                data = await resp.json()
                content = data["choices"][0]["message"]["content"]
                return {"model": model_key, "name": config["name"], "response": content, "role": lens_prompt}
    except Exception as e:
        return {"model": model_key, "error": str(e)}


async def run_digest(topic: str = "Critical AI Developments in last 24h"):
    """Run the daily digest with strict roles."""
    print(f"⟡ Running Daily Digest: {topic}")
    
    tasks = []
    active_models = []
    
    for key, role_conf in ROLES.items():
        if os.getenv(MODELS[key]["api_key_env"]):
            tasks.append(query_model(key, topic, role_conf["prompt"]))
            active_models.append(key)
            
    if not tasks:
        print("❌ No active models")
        return

    results = await asyncio.gather(*tasks)
    
    # Synthesis (Using ChatGPT to synthesize strictly)
    synth_prompt = f"""
    You are the Consortium Hub. synthesize these inputs into a strict Daily Brief.
    
    INPUTS:
    {json.dumps([r for r in results if "response" in r])}
    
    OUTPUT FORMAT (Markdown):
    # ⟡ Daily Consortium Brief — {datetime.now().strftime('%Y-%m-%d')}
    
    1. What Changed (Max 5 bullets)
    2. What Matters (Max 3 bullets)
    3. What Can Be Ignored (Max 3 bullets)
    4. Risks / Drift (Optional)
    5. Suggested Action (Do X / Monitor Y / No action)
    6. Dissenting View (If any)
    
    RULES:
    - Max 15 bullets total
    - No prose paragraphs
    - "Boring is success"
    - If confidence is low, recommend "No action"
    """
    
    # Self-query for synthesis (using GPT-4o-mini as synthesizer)
    print("⟡ Synthesizing...")
    final_digest = await query_model("gpt", synth_prompt, "You are the strict synthesizer.")
    
    content = final_digest.get("response", "Synthesis failed")
    
    # Save
    ensure_dirs()
    filename = f"{datetime.now().strftime('%Y%m%d')}_Briefing.md"
    file_path = BRIEFINGS_DIR / filename
    file_path.write_text(content)
    print(f"✓ Saved to {file_path}")
    
    return content


def send_email(content: str):
    """Send digest via SMTP."""
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASS")
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", 587))
    
    if not smtp_user or not smtp_pass:
        print("⚠️ No SMTP credentials. Email skipped. Add SMTP_USER/PASS to .env")
        return

    msg = MIMEMultipart()
    msg['From'] = f"Consortium <{smtp_user}>"
    msg['To'] = ", ".join(EMAILS)
    msg['Subject'] = f"⟡ Daily Brief — {datetime.now().strftime('%Y-%m-%d')}"
    msg.attach(MIMEText(content, 'markdown'))

    try:
        if smtp_port == 465:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port)
        else:
            server = smtplib.SMTP(smtp_host, smtp_port)
            server.starttls()
            
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)
        server.quit()
        print(f"✓ Email sent to {EMAILS}")
    except Exception as e:
        print(f"❌ Email failed: {e}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["digest", "ask", "debate", "pulse", "models", "publish"])
    parser.add_argument("prompt", nargs="?", default="Critical AI Developments 24h")
    parser.add_argument("--email", action="store_true") # Flag to enable email sending
    parser.add_argument("--models", "-m", help="Comma-separated list of models") # For explicit model selection
    args = parser.parse_args()
    
    if args.command == "digest":
        content = asyncio.run(run_digest(args.prompt))
        if args.email and content:
            send_email(content)
            
    elif args.command == "ask":
        if not args.prompt:
            print("❌ Prompt required")
            return
        # Simple parallel query without strict roles
        tasks = []
        for key in MODELS:
            if os.getenv(MODELS[key]["api_key_env"]):
                tasks.append(query_model(key, args.prompt, "Be concise."))
        
        if not tasks:
            print("❌ No active models")
            return
            
        print(f"⟡ Querying {len(tasks)} models...")
        results = asyncio.run(asyncio.gather(*tasks))
        
        print("\n" + "="*50)
        for r in results:
            if "response" in r:
                print(f"## {r.get('name', r['model'])}\n{r['response']}\n")
                
    elif args.command == "pulse":
        import aiohttp
        from bs4 import BeautifulSoup
        from urllib.parse import urljoin, urlparse

        target_url = args.prompt if args.prompt != "Critical AI Developments 24h" else "https://activemirror.ai"
        print(f"⟡ Pulding Site Health: {target_url}")
        
        async def check_site():
            clean_url = target_url.rstrip("/")
            domain = urlparse(clean_url).netloc
            report = f"# ⟡ Pulse Report — {datetime.now().strftime('%Y-%m-%d')}\n\n"
            report += f"**Target:** {target_url}\n\n"
            
            async with aiohttp.ClientSession() as session:
                # 1. Main Health Check
                try:
                    start = datetime.now()
                    async with session.get(clean_url, timeout=10) as resp:
                        latency = (datetime.now() - start).total_seconds()
                        status = resp.status
                        report += f"### Main Status\n"
                        report += f"- **Code:** {status} {'✅' if status == 200 else '❌'}\n"
                        report += f"- **Latency:** {latency:.2f}s\n\n"
                        
                        if status == 200:
                            content = await resp.text()
                            soup = BeautifulSoup(content, 'html.parser')
                            links = [urljoin(clean_url, a.get('href')) for a in soup.find_all('a', href=True)]
                            
                            internal_links = set([l for l in links if domain in urlparse(l).netloc])
                            external_links = set([l for l in links if domain not in urlparse(l).netloc and l.startswith('http')])
                            
                            report += f"### Link Analysis\n"
                            report += f"- Found {len(links)} total links.\n"
                            report += f"- {len(internal_links)} internal pages.\n"
                            report += f"- {len(external_links)} external references.\n\n"
                            
                            # Check a sample of internal links (max 5)
                            report += "### Deep Check (Sample 5)\n"
                            for link in list(internal_links)[:5]:
                                try:
                                    async with session.get(link, timeout=5) as sub_resp:
                                        report += f"- {sub_resp.status} : {link}\n"
                                except Exception as e:
                                    report += f"- ❌ Error : {link} ({str(e)})\n"
                        else:
                            report += "**CRITICAL:** Main site is down.\n"

                except Exception as e:
                    report += f"❌ FATAL: Could not reach site. {e}\n"
            
            return report

        try:
            report_content = asyncio.run(check_site())
            print("\n" + report_content)
            
            # Save report
            ensure_dirs()
            filename = f"{datetime.now().strftime('%Y%m%d')}_Pulse.md"
            path = BRIEFINGS_DIR / filename
            path.write_text(report_content)
            print(f"✓ Saved to {path}")
            
            if args.email:
                send_email(report_content)
                
        except ImportError:
            print("❌ Missing dependency. Run: pip3 install beautifulsoup4")

    elif args.command == "publish":
        # Publishing Logic
        # 1. Take input file (args.prompt)
        # 2. Copy to activemirror-site/public/briefings/
        # 3. Git add/commit/push
        
        source_file = Path(args.prompt)
        if not source_file.exists():
            print(f"❌ File not found: {source_file}")
            return
            
        SITE_REPO = Path.home() / "Documents/GitHub/activemirror-site"
        PUBLIC_BRIEFINGS = SITE_REPO / "public/briefings"
        PUBLIC_BRIEFINGS.mkdir(parents=True, exist_ok=True)
        
        dest_file = PUBLIC_BRIEFINGS / source_file.name
        
        # Read and Sanitize (Simple pass)
        content = source_file.read_text()
        # Ensure Frontmatter for eventual blog logic
        if not content.startswith("---"):
            frontmatter = f"---\ntitle: Daily Brief {datetime.now().strftime('%Y-%m-%d')}\ndate: {datetime.now().strftime('%Y-%m-%d')}\n---\n\n"
            content = frontmatter + content
            
        dest_file.write_text(content)
        print(f"✓ Copied to {dest_file}")
        
        # Git Operations
        try:
            import subprocess
            def git(cmd):
                result = subprocess.run(cmd, cwd=SITE_REPO, shell=True, capture_output=True, text=True)
                if result.returncode != 0:
                    print(f"⚠️ Git Error: {result.stderr}")
                return result.stdout.strip()
                
            print(git("git pull"))
            print(git(f"git add public/briefings/{dest_file.name}"))
            print(git(f"git commit -m 'Publish Briefing: {dest_file.name}'"))
            print(git("git push origin main")) # Assuming main
            print(f"🚀 Published to https://activemirror.ai/briefings/{dest_file.name}")
            
        except Exception as e:
            print(f"❌ Git Automation Failed: {e}")

    elif args.command == "debate":
        print("Coming in v1.1")

if __name__ == "__main__":
    main()
