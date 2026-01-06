import json
import os
import asyncio
import argparse
from pathlib import Path
from datetime import datetime

# ═══════════════════════════════════════════════════════════════
# SWARM DISTRIBUTOR v1.0
# "Fracturing coherence into virality."
# ═══════════════════════════════════════════════════════════════

INPUT_FILE = Path("public/data.json")
OUTPUT_FILE = Path("public/social_artifacts.json")

async def load_briefing():
    """Load the latest briefing data."""
    if not INPUT_FILE.exists():
        print(f"❌ Error: {INPUT_FILE} not found.")
        return None
    with open(INPUT_FILE, 'r') as f:
        return json.load(f)

def fracture_to_x(data):
    """Fracture the briefing into an X (Twitter) thread."""
    brief = data.get('briefing', {})
    headline = brief.get('headline', 'Daily Intelligence')
    summary = brief.get('summary', '')
    
    thread = []
    
    # 1. The Hook
    thread.append(f"🧵 {headline}\n\n{summary}\n\nA short thread on what matters today ⬇️")
    
    # 2. The Core Shifts
    sections = brief.get('sections', {})
    for item in sections.get('changed', [])[:2]:
        thread.append(f"🔹 {item['text']}\n\n{item['detail']}\n\nSignal: {item['voice'].upper()}")
        
    # 3. The Prediction
    preds = data.get('predictions', [])
    if preds:
        top_pred = preds[0]
        thread.append(f"🔮 PREDICTION: {top_pred['text']}\n\nConfidence: {top_pred['probability']['updated']}%\nDecay: {top_pred['probability']['decay']}\n\nWe are tracking this live.")
        
    # 4. The Closer
    thread.append(f"The signal is shifting. Don't operate on yesterday's reality.\n\nRead the full brief: https://brief.activemirror.ai\n\n#MirrorIntelligence #AI #Strategy")
    
    return thread

def frame_for_linkedin(data):
    """Frame the briefing for LinkedIn (Professional/Strategic)."""
    brief = data.get('briefing', {})
    headline = brief.get('headline', 'Daily Intelligence')
    summary = brief.get('summary', '')
    
    post = f"""🚨 {headline}

{summary}

Three critical shifts observed today:

"""
    
    sections = brief.get('sections', {})
    for i, item in enumerate(sections.get('changed', [])[:3]):
        post += f"{i+1}. {item['text']} — {item['detail']}\n"
        
    post += """
My take: The gap between signal and noise is widening. Only one of these actually changes the board state for next quarter.

Constructive thoughts?

#Strategy #AI #Leadership #MirrorIntelligence"""
    
    return post

async def activate_swarm():
    print("⟡ SWARM: Waking up...")
    data = await load_briefing()
    if not data:
        return
    
    print("⟡ SWARM: Fracturing coherence...")
    
    artifacts = {
        "meta": {
            "generated_at": datetime.now().isoformat(),
            "source": data['meta']['date']
        },
        "x_thread": fracture_to_x(data),
        "linkedin_post": frame_for_linkedin(data)
    }
    
    # Simulate processing time for "Agentic Feel"
    await asyncio.sleep(1)
    
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(artifacts, f, indent=2)
        
    print(f"⟡ SWARM: Artifacts deposited at {OUTPUT_FILE}")
    print("⟡ SWARM: Going dormant.")

if __name__ == "__main__":
    asyncio.run(activate_swarm())
