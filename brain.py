import json
import re

import ollama

import tools
from config import OLLAMA_HOST, OLLAMA_MODEL

SYSTEM_PROMPT = (
    "Tu es DJ Neon, l'assistant musical personnel de l'utilisateur, hébergé sur sa propre machine. "
    "Tu contrôles son Spotify UNIQUEMENT à sa demande explicite, en utilisant les outils fournis. "
    "Règles absolues :\n"
    "- Agis directement : si la demande est claire, appelle l'outil adapté immédiatement, sans "
    "demander de confirmation et sans annoncer ce que tu vas faire.\n"
    "- Pour « joue du <artiste> » ou « mets du <artiste> », utilise play_artist : il cherche sur "
    "tout Spotify, pas seulement dans la bibliothèque de l'utilisateur.\n"
    "- Pour un titre précis, utilise play_track : il cherche dans tout le catalogue Spotify.\n"
    "- Ne prétends JAMAIS avoir fait une action sans l'avoir réellement faite avec un outil. "
    "Si un outil renvoie une erreur, dis-le simplement et propose une alternative courte.\n"
    "- Pour la musique suivante, précédente, pause, reprise, le volume ou l'aléatoire, utilise "
    "playback_control ou set_shuffle — jamais d'autre outil, jamais d'invention.\n"
    "- Le « mode aléatoire intelligent » (smart shuffle) n'existe pas dans l'API Spotify : "
    "propose uniquement le mode aléatoire simple avec set_shuffle.\n"
    "- Réponds en français, de façon concise, chaleureuse et avec le ton d'un animateur radio. "
    "Après une action réussie, confirme brièvement ce que tu as fait.\n"
    "- Si la demande est réellement ambiguë, pose UNE seule question courte, jamais une série."
)

MAX_TOOL_ROUNDS = 5

TRANSPORT_ALIASES = {
    "next": {"action": "next"},
    "previous": {"action": "previous"},
    "pause": {"action": "pause"},
    "resume": {"action": "resume"},
}

TOOL_JSON_RE = re.compile(r"\{(?:[^{}]|\{[^{}]*\})*\}")


def direct_command(user_message):
    message = user_message.strip().lower()
    if not message:
        return None
    try:
        if re.search(r"al[eé]atoire|shuffle", message):
            off = re.search(r"enl[eè]ve|d[eé]sactiv|coupe|arr[eê]te|sans|\boff\b", message)
            return tools.set_shuffle(not off)
        volume = re.search(r"volume\s*(?:à|a|:|=)?\s*(\d{1,3})", message)
        if volume:
            return tools.set_volume(min(100, int(volume.group(1))))
        if re.search(r"\bsuivante?\b|\bnext\b|passe (?:à|au|a la|à la)", message):
            return tools.playback_control("next")
        if re.search(r"pr[eé]c[eé]dente?\b|previous|en arri[eè]re", message):
            return tools.playback_control("previous")
        if re.search(r"\bpause\b|arr[eê]te|\bstop\b|coupe", message):
            return tools.playback_control("pause")
        if re.fullmatch(
            r"(reprends?|relance)(\s+(la|le|la lecture|le morceau|la musique|-la|-le))?", message
        ):
            return tools.playback_control("resume")
    except Exception as exc:
        return f"⚠️ {exc}"
    return None


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


def _extract_content_tool_call(content):
    if not content:
        return None
    match = TOOL_JSON_RE.search(content)
    if not match:
        return None
    try:
        parsed = json.loads(match.group(0))
    except ValueError:
        return None
    name = parsed.get("name")
    if not isinstance(name, str):
        return None
    arguments = parsed.get("parameters") or parsed.get("arguments") or {}
    return name, arguments


def _normalize_call(name, arguments):
    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments)
        except ValueError:
            arguments = {}
    if not isinstance(arguments, dict):
        arguments = dict(arguments)
    if name in TRANSPORT_ALIASES and "action" not in arguments:
        arguments = dict(TRANSPORT_ALIASES[name])
        name = "playback_control"
    return name, arguments


def chat(user_message, history=None):
    direct = direct_command(user_message)
    if direct is not None:
        return direct

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

        calls = []
        for call in message.get("tool_calls") or []:
            call = _as_dict(call)
            function = call.get("function", {})
            calls.append((function.get("name"), function.get("arguments") or {}))
        if not calls:
            extracted = _extract_content_tool_call(message.get("content", ""))
            if extracted is not None:
                calls.append(extracted)
        if not calls:
            return message.get("content", "").strip()

        for name, arguments in calls:
            name, arguments = _normalize_call(name, arguments)
            result = _execute(name, arguments)
            messages.append({"role": "tool", "name": name, "content": result})

    return "J'ai eu du mal à enchaîner les actions Spotify. Peux-tu reformuler ta demande ?"
