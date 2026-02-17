import os
import json
import re
from groq import Groq


def clean_json(text):
    """Clean AI response to make valid JSON"""
    
    # Remove code blocks
    text = text.replace("```json", "").replace("```", "")
    
    # Remove control characters
    text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
    
    # Remove BOM if any
    text = text.replace('\ufeff', '')
    
    return text.strip()


def fallback_script(topic, video_type):
    """Emergency fallback if AI JSON fails"""

    return {
        "title": f"{topic.title()} - Kids Fun Video",
        "description": f"Fun and educational {video_type} about {topic}. Perfect for kids and children learning.",
        "tags": ["kids", "cartoon", "fun", "education", topic],
        "script": f"Welcome to this fun video about {topic}! [PAUSE] Let's learn together in a fun way!",
        "sections": [
            {"time": "0:00", "title": "Intro", "text": f"Welcome to {topic}"},
            {"time": "1:00", "title": "Story", "text": "Fun learning part"},
            {"time": "2:00", "title": "Moral", "text": "What we learned today"}
        ]
    }


def generate_script(topic, video_type):
    """Generate video script using Groq API"""

    client = Groq(api_key=os.getenv('GROQ_API_KEY'))

    # 🎯 SPECIAL PROMPT FOR TOONS / KIDS
    prompt = f"""
Create a KIDS FRIENDLY YouTube TOONS video script about: {topic}

STYLE RULES:
- Simple English for children
- Friendly cartoon tone
- Characters + short dialogues
- Fun moral at end
- No complex words
- 3-5 minutes narration

STRUCTURE:
- Catchy hook
- Small story
- Fun learning
- Moral
- CTA to subscribe

Return ONLY valid JSON in this format:

{{
    "title": "Cute kids friendly title (max 60 chars)",
    "description": "SEO description for kids video",
    "tags": ["kids", "cartoon", "story", "fun"],
    "script": "Narration with [PAUSE] markers",
    "sections": [
        {{"time": "0:00", "title": "Intro", "text": "..."}},
        {{"time": "1:00", "title": "Story", "text": "..."}},
        {{"time": "2:00", "title": "Moral", "text": "..."}}
    ]
}}
"""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": "You are a kids cartoon YouTube script expert. Always respond ONLY in JSON."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.6,
            max_tokens=2000
        )

        script_json = response.choices[0].message.content

        # Clean response
        script_json = clean_json(script_json)

        try:
            script_data = json.loads(script_json)

        except Exception as e:
            print("⚠ JSON parse failed — using fallback")
            print("RAW RESPONSE:\n", script_json)

            script_data = fallback_script(topic, video_type)

    except Exception as api_error:
        print("❌ Groq API Error:", api_error)
        script_data = fallback_script(topic, video_type)

    # Save script safely
    os.makedirs("output/scripts", exist_ok=True)

    filename = f"output/scripts/{topic.replace(' ', '_')[:30]}.json"

    with open(filename, 'w', encoding="utf-8") as f:
        json.dump(script_data, f, indent=2, ensure_ascii=False)

    return script_data
