"""
gemini_ai.py - Generative AI Engine for Question Paper Studio
Integrates Google Gemini API to generate dual-language (Tamil + English) questions,
synthesize questions from textbook text, generate distractors, and translate technical terms.
"""

import os
import json
import re
import urllib.request
import urllib.error

# Candidates models in priority order
GEMINI_MODELS = [
    'gemini-3.5-flash-lite',
    'gemini-flash-latest',
    'gemini-3.5-flash',
    'gemini-pro-latest'
]

def get_api_key():
    return (
        os.environ.get('GEMINI_API_KEY') or
        os.environ.get('GOOGLE_API_KEY') or
        "AIzaSyDhNelt9uysxTfyiFKd6pNw6ht94Bls4ls"
    )

def call_gemini(prompt, system_instruction=None, json_mode=True):
    """
    Calls Google Gemini REST API using urllib (zero dependencies, lightweight).
    """
    api_key = get_api_key()
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not configured.")

    last_error = None
    for model in GEMINI_MODELS:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        
        contents = []
        if system_instruction:
            contents.append({
                "role": "user",
                "parts": [{"text": f"SYSTEM INSTRUCTION:\n{system_instruction}\n\nUSER PROMPT:\n{prompt}"}]
            })
        else:
            contents.append({
                "role": "user",
                "parts": [{"text": prompt}]
            })

        body = {
            "contents": contents,
            "generationConfig": {
                "temperature": 0.4,
                "maxOutputTokens": 4096
            }
        }
        if json_mode:
            body["generationConfig"]["responseMimeType"] = "application/json"

        data_bytes = json.dumps(body).encode('utf-8')
        req = urllib.request.Request(
            url,
            data=data_bytes,
            headers={"Content-Type": "application/json"}
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                res_data = json.loads(resp.read().decode('utf-8'))
                candidates = res_data.get('candidates', [])
                if candidates:
                    parts = candidates[0].get('content', {}).get('parts', [])
                    if parts:
                        text = parts[0].get('text', '').strip()
                        return text
        except urllib.error.HTTPError as e:
            last_error = f"HTTP {e.code}: {e.reason}"
            continue
        except Exception as e:
            last_error = str(e)
            continue

    raise RuntimeError(f"All Gemini models failed. Last error: {last_error}")

def clean_json_text(text):
    text = text.strip()
    if text.startswith('```'):
        text = re.sub(r'^```(?:json)?\s*', '', text)
        text = re.sub(r'\s*```$', '', text)
    return text.strip()

def generate_questions_ai(topic, trade="Fitter", count=5, q_type="mcq", difficulty="medium"):
    """
    Generates dual-language exam questions using Generative AI (Gemini).
    Supported q_type: 'mcq' (1 mark), 'short' (2/3 marks), 'long' (16 marks), 'mixed'
    """
    system_instruction = (
        "You are an expert technical educator and syllabus question creator for ITI (Industrial Training Institute) "
        "and engineering trades under NIMI / NCVT curriculum. "
        "You formulate high-standard, syllabus-accurate questions in both English and Tamil simultaneously."
    )

    prompt = f"""Generate {count} high-quality exam questions for the Trade/Subject: '{trade}'.
Topic/Module: '{topic}'.
Question Type: '{q_type}' (Difficulty: {difficulty}).

Requirements:
1. Every question MUST contain BOTH English ('q_en') AND proper, idiomatic Tamil ('q_ta').
2. For MCQs ('q_type' == 'mcq'):
   - Provide 4 distinct options ('opt_a_en', 'opt_a_ta', 'opt_b_en', 'opt_b_ta', 'opt_c_en', 'opt_c_ta', 'opt_d_en', 'opt_d_ta').
   - Set 'correct_ans' as 'A', 'B', 'C', or 'D'.
   - Include 'explanation_en' and 'explanation_ta'.
3. For Short Answer / 2 or 3 marks ('q_type' == 'short'):
   - Provide expected key points in English ('key_points_en') and Tamil ('key_points_ta').
   - Marks: 2 or 3.
4. For Long / 16 marks Essay Questions ('q_type' == 'long'):
   - Provide detailed evaluation criteria and breakdown of sub-questions (e.g. (a) 8 marks, (b) 8 marks).
   - Marks: 16.
5. All technical terminology in Tamil must be accurate to NIMI Tamil textbooks.

Return ONLY a valid JSON array matching this schema:
[
  {{
    "q_en": "Question in English",
    "q_ta": "தமிழில் கேள்வி",
    "type": "mcq",
    "marks": 1,
    "opt_a_en": "Option A in English",
    "opt_a_ta": "விருப்பம் A தமிழில்",
    "opt_b_en": "Option B in English",
    "opt_b_ta": "விருப்பம் B தமிழில்",
    "opt_c_en": "Option C in English",
    "opt_c_ta": "விருப்பம் C தமிழில்",
    "opt_d_en": "Option D in English",
    "opt_d_ta": "விருப்பம் D தமிழில்",
    "correct_ans": "A",
    "explanation_en": "Brief explanation in English",
    "explanation_ta": "சுருக்கமான விளக்கம் தமிழில்"
  }}
]
"""

    raw_json = call_gemini(prompt, system_instruction=system_instruction, json_mode=True)
    cleaned = clean_json_text(raw_json)
    try:
        data = json.loads(cleaned)
        if isinstance(data, dict) and "questions" in data:
            data = data["questions"]
        if not isinstance(data, list):
            data = [data]
        return data
    except Exception as e:
        raise ValueError(f"Failed to parse Gemini AI response into JSON: {e}\nRaw: {raw_json[:300]}")

def translate_to_tamil_ai(text_en):
    """
    Translates an English technical question into fluent ITI/NIMI standard Tamil.
    """
    prompt = f"""Translate the following technical ITI/engineering question into accurate, formal Tamil as used in NIMI textbooks.
English: "{text_en}"

Return JSON:
{{
  "tamil": "மொழிபெயர்ப்பு"
}}"""
    raw = call_gemini(prompt, json_mode=True)
    cleaned = clean_json_text(raw)
    try:
        data = json.loads(cleaned)
        return data.get("tamil", text_en)
    except Exception:
        return text_en

def generate_distractors_ai(question_en, correct_ans_en):
    """
    Generates 3 plausible wrong options (distractors) in both English and Tamil.
    """
    prompt = f"""For this question:
Question: "{question_en}"
Correct Answer: "{correct_ans_en}"

Generate 3 plausible but incorrect options (distractors) commonly confused by students.
Return JSON:
{{
  "distractors": [
    {{"en": "Wrong 1", "ta": "தவறான விருப்பம் 1"}},
    {{"en": "Wrong 2", "ta": "தவறான விருப்பம் 2"}},
    {{"en": "Wrong 3", "ta": "தவறான விருப்பம் 3"}}
  ]
}}"""
    raw = call_gemini(prompt, json_mode=True)
    cleaned = clean_json_text(raw)
    try:
        return json.loads(cleaned).get("distractors", [])
    except Exception:
        return []
