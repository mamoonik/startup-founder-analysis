



########
#########################################
#########################################
import json
import os
from typing import Any, Dict

try:
    from openai import OpenAI
    _HAS_OPENAI = True
except Exception:
    _HAS_OPENAI = False

# # Optional Gemini client --- not implemented yet but could lead to significant latency reduction
# try:
#     import google.generativeai as genai
#     _HAS_GEMINI = True
# except Exception:
#     _HAS_GEMINI = False


PROMPT_PATH = os.path.join(os.path.dirname(__file__), "..", "prompts", "eo_prompt.txt")

def _load_system_prompt() -> str:
    with open(PROMPT_PATH, "r", encoding="utf-8") as f:
        return f.read()

def _to_user_message(profile: Dict[str, Any]) -> str:
    print(profile)
    return (
        "Analyze the following EnrichLayer profile JSON for entreneurial orientaton "
        "using the scoring rubric. The profile may contain per-experience 'company_enrichment' "
        "objects from the EnrichLayer Compny API. Return JSON only.\n\nPROFILE_JSON:\n" +
        json.dumps(profile, ensure_ascii=False)
    )

def score_with_llm(profile: Dict[str, Any]) -> Dict[str, Any]:
    system_prompt = _load_system_prompt()
    user_msg = _to_user_message(profile)

    if not _HAS_OPENAI:
        return {"score": 0, "band": "No/Negative", "reasons": ["LLM not working"], "matched_rules": [], "evidence": [], "confidence": 0.2}

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    resp = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_msg},
        ]
    )
    text = resp.choices[0].message.content.strip()

    try:
        ##Parse the JSON returned by the model. If this fails, the exception below returns a “Parse error” result.
        data = json.loads(text)
        score = int(data.get("score", 0))
        
        band = data.get("band") or {0:"No/Negative",1:"Low",2:"Moderate",3:"Strong",4:"Exceptional"}.get(score,"No/Negative")
        
        reasons = data.get("reasons") or []

        if isinstance(reasons, str):
            reasons = [reasons]
        matched = data.get("matched_rules") or []
        evidence = data.get("evidence") or []
        conf = float(data.get("confidence", 0.6))
        
        score = max(0, min(4, score))
        
        conf = max(0.0, min(1.0, conf))
        
        return {
            "score": score,
            "band": band,
            "reasons": reasons,
            "matched_rules": matched,
            "evidence": evidence,
            "confidence": conf
        }
    except Exception:
        return {"score": 0, "band": "No/Negative", "reasons": ["Parse error"], "matched_rules": [], "evidence": [], "confidence": 0.2}

        # return {"score": 0, "band": "No/Negative", "confidence": 0.2}



###############################################
###############################################
