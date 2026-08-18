import json
import logging
import requests
from typing import Dict, Any, List
from app.core.config import settings

logger = logging.getLogger(__name__)

class LLMAdapter:
    @staticmethod
    def generate_json(prompt: str, system_prompt: str = "") -> Dict[str, Any]:
        provider = settings.LLM_PROVIDER.lower()
        if provider == "openai" and settings.LLM_API_KEY:
            return LLMAdapter._call_openai(prompt, system_prompt)
        elif provider == "ollama":
            return LLMAdapter._call_ollama(prompt, system_prompt)
        else:
            return LLMAdapter._call_ollama(prompt, system_prompt)

    @staticmethod
    def _call_ollama(prompt: str, system_prompt: str) -> Dict[str, Any]:
        try:
            url = f"{settings.LLM_BASE_URL.rstrip('/')}/api/generate"
            payload = {
                "model": settings.LLM_MODEL,
                "prompt": f"{system_prompt}\n\n{prompt}\nReturn ONLY valid JSON.",
                "stream": False,
                "format": "json"
            }
            res = requests.post(url, json=payload, timeout=25)
            if res.status_code == 200:
                response_text = res.json().get("response", "")
                return LLMAdapter._clean_and_parse_json(response_text)
        except Exception as e:
            logger.warning(f"Ollama LLM call failed or unavailable ({e}). Using deterministic analytical synthesis engine.")
        
        return {}

    @staticmethod
    def _call_openai(prompt: str, system_prompt: str) -> Dict[str, Any]:
        try:
            headers = {
                "Authorization": f"Bearer {settings.LLM_API_KEY}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": settings.LLM_MODEL or "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": system_prompt + " Respond with valid JSON strictly."},
                    {"role": "user", "content": prompt}
                ],
                "response_format": {"type": "json_object"}
            }
            res = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload, timeout=25)
            if res.status_code == 200:
                content = res.json()["choices"][0]["message"]["content"]
                return json.loads(content)
        except Exception as e:
            logger.warning(f"OpenAI LLM call failed ({e}). Falling back to analytical synthesis.")
        return {}

    @staticmethod
    def _clean_and_parse_json(raw_text: str) -> Dict[str, Any]:
        try:
            text = raw_text.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            return json.loads(text.strip())
        except Exception:
            return {}

    @staticmethod
    def parse_unstructured_process_to_activities(
        process_name: str,
        description: str,
        current_process_text: str,
        problems_text: str = ""
    ) -> List[Dict[str, Any]]:
        """
        Extracts structured activities from free-text process descriptions.
        Grounded rule: Extract explicit roles and systems present in input.
        Use 'Not specified' only if role, system, or problem cannot be determined.
        """
        system_prompt = (
            "You are a business process architecture expert. "
            "Analyze the given retail process overview, activities text, and key problems text. "
            "Extract 2 to 5 distinct operational activities. "
            "Return JSON with key 'activities' containing a list of objects with fields:\n"
            "- sequence_order: integer\n"
            "- name: concise activity title\n"
            "- description: detailed description of the activity based strictly on user input\n"
            "- role: human role explicitly mentioned or performing this step (e.g. 'Support staff', 'Store or warehouse staff', 'Finance', 'Inventory staff'). If no role is stated, use 'Not specified'.\n"
            "- system: software/tools/systems explicitly mentioned with this step (e.g. 'Zendesk', 'ERP', 'Email', 'POS', 'Manual clipboard'). If no system is stated, use 'Not specified'.\n"
            "- operational_problem: the specific operational problem or bottleneck from the problems text that semantically describes this activity's pain point. If no problem applies to this activity, use 'Not specified'.\n"
            "\nGROUNDING RULE: Extract explicit roles and systems accurately. Do NOT invent unstated roles/systems. Map operational problems semantically based on topic relevance."
        )
        
        prompt = (
            f"Process Name: {process_name}\n"
            f"Overview: {description}\n"
            f"Current Process / Activities Text:\n{current_process_text}\n\n"
            f"Key Problems / Bottlenecks Text:\n{problems_text}"
        )
        
        result = LLMAdapter.generate_json(prompt, system_prompt)
        activities = result.get("activities", [])
        
        if not activities or not isinstance(activities, list):
            activities = LLMAdapter._fallback_process_parser(
                process_name, description, current_process_text, problems_text
            )
            
        cleaned_activities = []
        for idx, act in enumerate(activities, start=1):
            role_val = str(act.get("role", "")).strip()
            system_val = str(act.get("system", "")).strip()
            prob_val = str(act.get("operational_problem", "")).strip()
            
            cleaned_activities.append({
                "sequence_order": act.get("sequence_order", idx),
                "name": str(act.get("name", f"Activity {idx}")).strip() or f"Activity {idx}",
                "description": str(act.get("description", "")).strip() or description,
                "role": role_val if role_val and role_val.lower() != "none" else "Not specified",
                "system": system_val if system_val and system_val.lower() != "none" else "Not specified",
                "operational_problem": prob_val if prob_val and prob_val.lower() != "none" else "Not specified"
            })
            
        return cleaned_activities

    @staticmethod
    def _fallback_process_parser(
        process_name: str,
        description: str,
        current_process_text: str,
        problems_text: str = ""
    ) -> List[Dict[str, Any]]:
        """
        Rule-based fallback parser when LLM is unavailable.
        Extracts explicit roles/systems and semantically maps problems.
        """
        import re

        lines = [line.strip(" *-•1234567890.)") for line in (current_process_text or "").splitlines() if line.strip()]
        if not lines:
            lines = [(current_process_text or "").strip() or (description or "").strip() or f"Execute {process_name}"]
        lines = lines[:5]

        # Roles extraction patterns
        role_patterns = [
            r'\b(support staff|customer service|customer support|warehouse worker|warehouse staff|store or warehouse staff|store staff|finance team|finance staff|finance|inventory staff|inventory planner|store associate|store manager|operational staff|planner|analyst|agent|worker|staff|associate|manager)\b',
        ]
        
        # Systems extraction patterns
        system_patterns = [
            r'\b(zendesk|erp|pos|excel|spreadsheet|email|e-mail|barcode scanner|web portal|crm|wms|payment gateway|database|clipboard|manual paper|sap|oracle)\b',
        ]

        # Parse problem entries
        problem_entries = [p.strip(" *-•1234567890.)") for p in (problems_text or "").splitlines() if p.strip()]
        if not problem_entries and problems_text:
            problem_entries = [problems_text.strip()]

        stopwords = {"the", "a", "an", "is", "are", "was", "were", "and", "or", "in", "on", "at", "to", "for", "with", "by", "of", "from", "it", "this", "that", "causes", "delay", "delays"}

        fallback_activities = []
        for idx, line in enumerate(lines, start=1):
            line_lower = line.lower()
            
            # Extract explicit role if present
            found_role = "Not specified"
            for pat in role_patterns:
                match = re.search(pat, line_lower, re.IGNORECASE)
                if match:
                    found_role = match.group(1).title()
                    break
            
            # Extract explicit system if present
            found_system = "Not specified"
            for pat in system_patterns:
                match = re.search(pat, line_lower, re.IGNORECASE)
                if match:
                    found_system = match.group(1).upper() if len(match.group(1)) <= 4 else match.group(1).title()
                    break
            
            # Semantic Problem Matching via keyword overlap
            best_prob = "Not specified"
            best_score = 0
            
            activity_words = set(w for w in re.findall(r'\b\w+\b', line_lower) if len(w) > 3 and w not in stopwords)
            
            for prob in problem_entries:
                prob_words = set(w for w in re.findall(r'\b\w+\b', prob.lower()) if len(w) > 3 and w not in stopwords)
                common = activity_words.intersection(prob_words)
                score = len(common)
                if score > best_score:
                    best_score = score
                    best_prob = prob

            # Fallback if no semantic match score > 0
            if best_score == 0 and problem_entries:
                if idx - 1 < len(problem_entries):
                    best_prob = problem_entries[idx - 1]
                else:
                    best_prob = problem_entries[0]

            name = line[:55] + ("..." if len(line) > 55 else "")
            
            fallback_activities.append({
                "sequence_order": idx,
                "name": name,
                "description": line,
                "role": found_role,
                "system": found_system,
                "operational_problem": best_prob
            })
            
        return fallback_activities

