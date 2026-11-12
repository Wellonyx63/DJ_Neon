import time

import brain
import spotify_client
from spotify_client import SpotifyError

POLL_SECONDS = 5
MAX_WAIT_MINUTES = 15
MAX_POLL_ERRORS = 12

DJ_PROMPT = (
    "Tu es DJ Neon, l'animateur d'une radio personnelle. Écris en français des liens d'antenne "
    "très courts (une à deux phrases maximum), chaleureux et pleins d'énergie, sans répéter "
    "les formules de salutation d'une annonce à l'autre."
)


def _fmt(track):
    return f"« {track['name']} » de {track['artist']}"


def _announce(prompt, fallback):
    return brain.simple_chat(DJ_PROMPT, prompt, fallback)


def _wait_track_change(current_uri):
    deadline = time.time() + MAX_WAIT_MINUTES * 60
    errors = 0
    while time.time() < deadline:
        time.sleep(POLL_SECONDS)
        try:
            state = spotify_client.get_current_track()
            errors = 0
        except SpotifyError:
            errors += 1
            if errors >= MAX_POLL_ERRORS:
                return None
            continue
        if state is None:
            return None
        if state["uri"] != current_uri:
            return state
    return None


def run_dj_session(theme, tracks_count=8):
    setlist = spotify_client.recommend_tracks(theme, limit=max(tracks_count, 2))
    if len(setlist) < 2:
        raise SpotifyError(f"Pas assez de morceaux trouvés pour le thème « {theme} ».")

    spotify_client.play_tracks([setlist[0]["uri"]])

    use_queue = True
    for track in setlist[1:]:
        try:
            spotify_client.add_to_queue(track["uri"])
        except SpotifyError:
            use_queue = False
            break

    first = setlist[0]
    intro = _announce(
        f"La session vient de commencer sur le thème « {theme} ». "
        f"Le premier morceau est {_fmt(first)}. Écris l'annonce d'ouverture de l'antenne.",
        f"Bienvenue sur DJ Neon ! En route pour un voyage « {theme} », "
        f"ça commence avec {_fmt(first)}.",
    )
    print(f"\n🎙️  {intro}")
    print(f"🎵  Maintenant : {_fmt(first)}\n")

    played = 1
    try:
        while played < len(setlist):
            current = setlist[played - 1]
            upcoming = setlist[played]
            new_state = _wait_track_change(current["uri"])
            if new_state is None:
                print("\n🎙️  La lecture s'est arrêtée — DJ Neon quitte l'antenne. À bientôt !")
                break
            if new_state["uri"] != upcoming["uri"]:
                positions = {t["uri"]: i for i, t in enumerate(setlist)}
                if new_state["uri"] in positions and positions[new_state["uri"]] > played - 1:
                    played = positions[new_state["uri"]]
                    upcoming = setlist[played]
                else:
                    print("\n🎙️  Programme modifié en cours d'antenne — DJ Neon s'efface. À bientôt !")
                    break
            transition = _announce(
                f"Thème de la session : « {theme} ». Le morceau précédent était {_fmt(current)}. "
                f"Le prochain est {_fmt(upcoming)}. Écris la transition entre les deux.",
                f"Et maintenant, cap sur {_fmt(upcoming)} !",
            )
            print(f"🎙️  {transition}")
            print(f"🎵  Maintenant : {_fmt(upcoming)}\n")
            played += 1
            if not use_queue:
                spotify_client.play_tracks([upcoming["uri"]])
    except KeyboardInterrupt:
        print("\n🎙️  DJ Neon quitte l'antenne. À bientôt !")

    return f"Session DJ « {theme} » : {played} morceau(x) diffusé(s)."
