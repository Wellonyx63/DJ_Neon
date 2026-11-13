import threading
import webbrowser

from flask import Flask, jsonify, request, send_from_directory

import brain
import config
import spotify_client
from spotify_client import SpotifyError

app = Flask(__name__)

history = []


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/api/chat", methods=["POST"])
def api_chat():
    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()
    if not message:
        return jsonify({"error": "Message vide."}), 400
    try:
        reply = brain.chat(message, history)
    except brain.BrainError as exc:
        return jsonify({"error": str(exc)})
    except Exception as exc:
        return jsonify({"error": f"Erreur inattendue : {exc}"})
    history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": reply})
    if len(history) > 20:
        del history[:-20]
    return jsonify({"reply": reply})


@app.route("/api/state")
def api_state():
    try:
        return jsonify(spotify_client.get_playback_state())
    except SpotifyError as exc:
        return jsonify(
            {"playing": False, "track": None, "artist": None, "shuffle": None, "error": str(exc)}
        )


@app.route("/api/control", methods=["POST"])
def api_control():
    data = request.get_json(silent=True) or {}
    action = data.get("action")
    try:
        if action == "volume":
            spotify_client.set_volume(int(data.get("value", 50)))
            return jsonify({"ok": True})
        if action == "shuffle":
            spotify_client.set_shuffle(bool(data.get("value", True)))
            return jsonify({"ok": True})
        if action in ("pause", "resume", "next", "previous"):
            spotify_client.playback_control(action)
            return jsonify({"ok": True})
        return jsonify({"error": f"Action inconnue : {action}"}), 400
    except (SpotifyError, ValueError) as exc:
        return jsonify({"error": str(exc)})


def main():
    missing = config.missing_spotify_config()
    if missing:
        print(f"⚠️  Configuration Spotify incomplète : {', '.join(missing)}")
        print("   Copie .env.example en .env et remplis tes identifiants.")
        raise SystemExit(1)

    print("🔐 Connexion à Spotify (ton navigateur peut s'ouvrir pour l'autorisation)…")
    try:
        spotify_client.list_playlists()
        brain.check_connection()
    except (SpotifyError, brain.BrainError) as exc:
        print(f"⚠️  {exc}")
        raise SystemExit(1)

    port = 8000
    url = f"http://127.0.0.1:{port}"
    print(f"🎧 DJ Neon est en ligne : {url}")
    print("   (Ctrl+C pour quitter — l'interface n'est accessible que depuis ce PC)")
    threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    app.run(host="127.0.0.1", port=port, debug=False)


if __name__ == "__main__":
    main()
