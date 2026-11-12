import json

import ollama

import tools
from config import OLLAMA_HOST, OLLAMA_MODEL

SYSTEM_PROMPT = (
    "Tu es DJ Neon, l'assistant musical personnel de l'utilisateur, hébergé sur sa propre machine. "
    "Tu contrôles son Spotify UNIQUEMENT à sa demande explicite, en utilisant les outils fournis. "
    "Réponds toujours en français, de façon concise, chaleureuse et avec le ton d'un animateur radio. "
    "Après chaque action Spotify, confirme brièvement ce que tu as fait. "
    "Si une demande est ambiguë (plusieurs playlists ou morceaux possibles), demande une précision "
    "au lieu de deviner. Ne propose jamais d'action Spotify sans que l'utilisateur l'ait demandée."
)

MAX_TOOL_ROUNDS = 5


class BrainError(Exception):
    pass


def get_client():
    return ollama.Client(host=OLLAMA_HOST)


def check_connection():
    try:
        get_client().list()
    except Exception as exc:
        raise BrainError(
            f"Ollama est injoignable sur {OLLAMA_HOST}. Démarre-le avec `ollama serve`, "
            f"puis télécharge le modèle : `ollama pull {OLLAMA_MODEL}`."
        ) from exc


def _as_dict(obj):
    if isinstance(obj, dict):
        return obj
    return obj.model_dump()


def _execute(name, arguments):
    handler = tools.TOOL_HANDLERS.get(name)
    if handler is None:
        return json.dumps({"error": f"Outil inconnu : {name}"}, ensure_ascii=False)
    try:
        result = handler(**arguments)
    except TypeError:
        return json.dumps({"error": f"Arguments invalides pour l'outil {name}."}, ensure_ascii=False)
    except Exception as exc:
        return json.dumps({"error": str(exc)}, ensure_ascii=False)
    if isinstance(result, str):
        return result
    return json.dumps(result, ensure_ascii=False)


def simple_chat(system_prompt, user_prompt, fallback=""):
    try:
        response = get_client().chat(
            model=OLLAMA_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        content = _as_dict(response["message"]).get("content", "")
        return content.strip() or fallback
    except Exception:
        return fallback


def chat(user_message, history=None):
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": user_message})

    for _ in range(MAX_TOOL_ROUNDS):
        try:
            response = get_client().chat(
                model=OLLAMA_MODEL, messages=messages, tools=tools.TOOL_SCHEMAS
            )
        except Exception as exc:
            raise BrainError(f"Erreur Ollama : {exc}") from exc

        message = _as_dict(response["message"])
        messages.append(message)
        tool_calls = message.get("tool_calls") or []
        if not tool_calls:
            return message.get("content", "").strip()

        for call in tool_calls:
            call = _as_dict(call)
            function = call.get("function", {})
            name = function.get("name")
            arguments = function.get("arguments") or {}
            if not isinstance(arguments, dict):
                arguments = dict(arguments)
            result = _execute(name, arguments)
            messages.append({"role": "tool", "name": name, "content": result})

    return "J'ai eu du mal à enchaîner les actions Spotify. Peux-tu reformuler ta demande ?"
