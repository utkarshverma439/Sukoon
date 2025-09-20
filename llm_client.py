import requests
import json
import os
from pathlib import Path
import toml

def load_api_key():
    """Load API key from secrets.toml or environment variable"""
    secrets_path = Path("secrets.toml")
    if secrets_path.exists():
        try:
            secrets = toml.load(secrets_path)
            return secrets.get("OPENROUTER_API_KEY")
        except Exception:
            pass
    return os.environ.get("OPENROUTER_API_KEY")

SYSTEM_PROMPTS = {
    "aarav": """You are Aarav, a calm, grounding male mental-wellness assistant tailored for Indian youth. 

IMPORTANT LANGUAGE RULES:
- ALWAYS respond in the SAME LANGUAGE the user writes in (English, Hindi, Hinglish, or any mix)
- If user writes "kaise ho", respond in Hinglish/Hindi
- If user writes "how are you", respond in English
- If user mixes languages, mirror their style exactly
- Use natural code-switching like Indian youth do

PERSONALITY & APPROACH:
- Calm, logical, and grounding presence
- Use empathetic, concise language
- Acknowledge feelings first, then provide 2 short actionable coping steps
- Ask one uplifting follow-up question
- Use culturally relevant examples (family, studies, career pressure, etc.)
- Reference Indian context when appropriate (festivals, family dynamics, academic stress)

SAFETY:
- Do not diagnose mental health conditions
- If user reports self-harm or imminent danger, provide crisis resources immediately
- Encourage professional help when needed

Keep responses under 150 words. Be authentic and relatable like a supportive older brother.""",
    
    "meera": """You are Meera, a warm, empathetic female mental-wellness assistant tailored for Indian youth.

IMPORTANT LANGUAGE RULES:
- ALWAYS respond in the SAME LANGUAGE the user writes in (English, Hindi, Hinglish, or any mix)
- If user writes "kya haal hai", respond in Hinglish/Hindi
- If user writes "what's up", respond in English  
- If user mixes languages, mirror their style exactly
- Use natural code-switching like Indian youth do

PERSONALITY & APPROACH:
- Warm, nurturing, and emotionally validating
- Offer emotional validation first, then 2 practical coping steps
- Ask caring follow-up questions
- Use culturally sensitive references (family expectations, social pressures, relationships)
- Reference Indian context (festivals, traditions, family dynamics, academic/career stress)
- Be like a supportive elder sister or close friend

SAFETY:
- Do not diagnose mental health conditions
- If high risk detected, provide immediate crisis help resources
- Encourage professional support when appropriate

Keep responses under 150 words. Be genuine and caring like a trusted friend."""
}

SUMMARIZATION_PROMPT = """Create a personalized user profile summary for future conversations. Include:

1. USER PROFILE:
   - Preferred language/communication style (English/Hindi/Hinglish/mix)
   - Main concerns and recurring themes
   - Current emotional state and mood patterns
   - Personal context (studies, family, relationships, work)

2. CONVERSATION INSIGHTS:
   - What coping strategies worked well for them
   - Their communication preferences and triggers
   - Cultural/personal references they relate to
   - Topics that help them feel better

3. RECOMMENDATIONS FOR FUTURE:
   - How to approach this user (tone, language, examples)
   - What support style works best for them
   - Key areas to focus on in future conversations

Keep under 200 words. This will help provide personalized support in future chats."""

async def chat_with_bot(bot_name: str, message: str, conversation_history: list = None, user_summaries: list = None):
    """Send message to OpenRouter API and get response with personalization"""
    api_key = load_api_key()
    if not api_key:
        raise ValueError("OpenRouter API key not found")
    
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # Detect user's language style and adapt prompt
    detected_style = detect_language_style(message)
    system_content = await get_language_adaptive_prompt(bot_name, message, detected_style)
    
    # Add personalization from previous summaries
    if user_summaries:
        recent_summaries = user_summaries[-3:]  # Last 3 summaries for context
        personalization = "\n\nPERSONALIZATION CONTEXT (from previous conversations):\n"
        for i, summary in enumerate(recent_summaries, 1):
            personalization += f"Session {i}: {summary.summary_text}\n"
        personalization += f"\nUser's detected communication style: {detected_style}. Use this context to provide personalized, culturally appropriate responses matching their preferred language style."
        system_content += personalization
    
    messages = [{"role": "system", "content": system_content}]
    
    # Add recent conversation history (last 6 messages to manage token usage)
    if conversation_history:
        recent_history = conversation_history[-6:]
        for chat in recent_history:
            messages.append({"role": "user", "content": chat.message})
            messages.append({"role": "assistant", "content": chat.reply})
    
    messages.append({"role": "user", "content": message})
    
    payload = {
        "model": "deepseek/deepseek-chat-v3.1:free",
        "messages": messages,
        "temperature": 0.7,  # Slightly higher for more natural responses
        "max_tokens": 512
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()
        return result["choices"][0]["message"]["content"]
    except requests.exceptions.RequestException as e:
        raise Exception(f"API request failed: {str(e)}")
    except KeyError as e:
        raise Exception(f"Unexpected API response format: {str(e)}")

async def summarize_conversation(bot_name: str, conversation_history: list):
    """Generate a summary of the conversation"""
    api_key = load_api_key()
    if not api_key:
        raise ValueError("OpenRouter API key not found")
    
    # Create conversation text
    conv_text = ""
    for chat in conversation_history[-10:]:  # Last 10 messages
        conv_text += f"User: {chat.message}\n{bot_name.title()}: {chat.reply}\n\n"
    
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    messages = [
        {"role": "system", "content": SUMMARIZATION_PROMPT},
        {"role": "user", "content": f"Conversation to summarize:\n\n{conv_text}"}
    ]
    
    payload = {
        "model": "deepseek/deepseek-chat-v3.1:free",
        "messages": messages,
        "temperature": 0.3,
        "max_tokens": 200
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()
        return result["choices"][0]["message"]["content"]
    except Exception as e:
        raise Exception(f"Summarization failed: {str(e)}")

def detect_language_style(message: str) -> str:
    """Detect the language style of the user's message"""
    message_lower = message.lower()
    
    # Hindi/Devanagari script detection
    hindi_chars = any('\u0900' <= char <= '\u097F' for char in message)
    
    # Common Hinglish words
    hinglish_words = [
        'kya', 'hai', 'haal', 'kaise', 'ho', 'bhai', 'yaar', 'acha', 'theek', 
        'nahi', 'haan', 'kuch', 'bhi', 'matlab', 'samjha', 'dekho', 'suno',
        'chal', 'bas', 'abhi', 'phir', 'waise', 'kyun', 'kahan', 'kab',
        'accha', 'thik', 'bilkul', 'sach', 'jhooth', 'paisa', 'ghar', 'mummy',
        'papa', 'didi', 'bhaiya', 'aunty', 'uncle', 'ji', 'sahab', 'madam'
    ]
    
    # Common Hindi/Urdu words in Roman script
    hindi_roman_words = [
        'namaste', 'namaskar', 'salaam', 'adaab', 'bhagwan', 'allah', 'ram',
        'beta', 'baccha', 'ladka', 'ladki', 'shaadi', 'padhai', 'naukri',
        'padhna', 'likhna', 'bolna', 'sunna', 'dekhna', 'jana', 'aana',
        'khana', 'peena', 'sona', 'uthna', 'baithna', 'khada', 'chalna'
    ]
    
    hinglish_count = sum(1 for word in hinglish_words if word in message_lower)
    hindi_roman_count = sum(1 for word in hindi_roman_words if word in message_lower)
    
    if hindi_chars:
        return "hindi_devanagari"
    elif hinglish_count >= 2 or hindi_roman_count >= 1:
        return "hinglish"
    elif any(word in message_lower for word in ['the', 'and', 'is', 'are', 'was', 'were', 'have', 'has', 'will', 'would', 'should', 'could']):
        return "english"
    else:
        return "mixed"

async def get_language_adaptive_prompt(bot_name: str, user_message: str, detected_style: str) -> str:
    """Get language-adaptive system prompt based on user's communication style"""
    base_prompt = SYSTEM_PROMPTS[bot_name]
    
    language_instructions = {
        "hindi_devanagari": "\n\nIMPORTANT: User prefers Hindi in Devanagari script. Respond primarily in Hindi with Devanagari script, but you can mix some English words naturally as Indians do.",
        
        "hinglish": "\n\nIMPORTANT: User prefers Hinglish (Hindi-English mix). Respond in natural Hinglish style mixing Hindi and English words fluidly like: 'Yaar, that's really tough. Main samajh sakta hun how stressful ye situation hai.'",
        
        "english": "\n\nIMPORTANT: User prefers English. Respond in clear English but feel free to use Indian cultural references and occasional Hindi words that are commonly understood.",
        
        "mixed": "\n\nIMPORTANT: User uses mixed language style. Mirror their communication pattern and adapt your language to match their style naturally."
    }
    
    return base_prompt + language_instructions.get(detected_style, language_instructions["mixed"])