import sys

import brain
import config
import spotify_client
from spotify_client import SpotifyError

BANNER = r"""
  ██████╗      ██╗    ██╗███████╗ ██████╗ ███    ██╗
  ██╔══██╗     ██║    ██║██╔════╝██╔═══██╗████╗   ██║
  ██║  ██║     ██║ █╗ ██║█████╗  ██║   ██║██╔██╗  ██║
  ██║  ██║     ██║███╗██║██╔══╝  ██║   ██║██║╚██╗ ██║
  ██████╔╝     ╚███╔███╔╝███████╗╚██████╔╝██║ ╚████║
  ╚═════╝       ╚══╝╚══╝ ╚══════╝ ╚═════╝ ╚═╝  ╚═══╝
        ta radio personnelle, hébergée chez toi
"""

HELP = """Commandes :
  /help   affiche cette aide
  /quit   quitte DJ Neon

Tout le reste est du langage naturel, par exemple :
  montre-moi mes playlists
  lance ma playlist Sport
  mets du Daft Punk
  ajoute One More Time à la file
  qu'est-ce qui passe en ce moment ?
  volume à 40
  propose-moi des morceaux pour une soirée calme
  mode DJ sur le thème des années 80   (Ctrl+C pour quitter la session)
"""


def main():
    missing = config.missing_spotify_config()
    if missing:
        print(f"⚠️  Configuration Spotify incomplète : {', '.join(missing)}")
        print("   Copie .env.example en .env et remplis tes identifiants.")
        sys.exit(1)

    print(BANNER)

    try:
        brain.check_connection()
    except brain.BrainError as exc:
        print(f"⚠️  {exc}")
        sys.exit(1)

    print("🔐 Connexion à Spotify (ton navigateur peut s'ouvrir pour l'autorisation)…")
    try:
        playlists = spotify_client.list_playlists()
    except SpotifyError as exc:
        print(f"⚠️  Spotify : {exc}")
        sys.exit(1)
    print(f"✅ Spotify connecté — {len(playlists)} playlist(s) trouvée(s).")
    print(f"🧠 Modèle local : {config.OLLAMA_MODEL}")
    print("Tape /help pour l'aide, /quit pour sortir.\n")

    history = []
    while True:
        try:
            user_input = input("toi > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n👋 À bientôt !")
            break

        if not user_input:
            continue
        if user_input in ("/quit", "/q", "/exit"):
            print("👋 À bientôt !")
            break
        if user_input == "/help":
            print(HELP)
            continue

        try:
            answer = brain.chat(user_input, history)
        except brain.BrainError as exc:
            print(f"⚠️  {exc}\n")
            continue
        except KeyboardInterrupt:
            print("\n🎙️  (interrompu)\n")
            continue
        except Exception as exc:
            print(f"⚠️  Erreur inattendue : {exc}\n")
            continue

        print(f"dj neon > {answer}\n")
        history.append({"role": "user", "content": user_input})
        history.append({"role": "assistant", "content": answer})
        if len(history) > 20:
            history = history[-20:]


if __name__ == "__main__":
    main()
