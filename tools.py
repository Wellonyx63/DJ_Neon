import spotify_client
from spotify_client import SpotifyError


def _fmt_track(track):
    return f"« {track['name']} » de {track['artist']}"


def list_playlists():
    playlists = spotify_client.list_playlists()
    if not playlists:
        return "Aucune playlist trouvée sur ce compte."
    lines = [f"- {p['name']} ({p['tracks']} morceaux)" for p in playlists]
    return "Playlists de l'utilisateur :\n" + "\n".join(lines)


def play_playlist(name):
    playlist = spotify_client.play_playlist(name)
    if playlist is None:
        known = ", ".join(p["name"] for p in spotify_client.list_playlists())
        return (
            f"Playlist « {name} » introuvable. Playlists disponibles : {known or 'aucune'}. "
            "Demande à l'utilisateur de préciser."
        )
    return f"Lecture lancée : playlist « {playlist['name']} » ({playlist['tracks']} morceaux)."


def play_track(query):
    track = spotify_client.play_track(query)
    return f"Lecture lancée : {_fmt_track(track)}."


def queue_track(query):
    tracks = spotify_client.search_tracks(query, limit=1)
    if not tracks:
        return f"Aucun morceau trouvé pour « {query} »."
    spotify_client.add_to_queue(tracks[0]["uri"])
    return f"Ajouté à la file d'attente : {_fmt_track(tracks[0])}."


def recommend_tracks(theme, limit=5):
    tracks = spotify_client.recommend_tracks(theme, limit=limit)
    if not tracks:
        return f"Aucune suggestion trouvée pour le thème « {theme} »."
    lines = [f"- {_fmt_track(t)}" for t in tracks]
    return (
        f"Suggestions pour « {theme} » :\n"
        + "\n".join(lines)
        + "\nPrésente-les à l'utilisateur ; il peut demander à en lancer une avec play_track."
    )


def dj_mode(theme, tracks_count=8):
    from dj import run_dj_session

    return run_dj_session(theme, tracks_count)


def current_track():
    state = spotify_client.get_current_track()
    if state is None:
        return "Aucune lecture en cours."
    status = "en lecture" if state["is_playing"] else "en pause"
    return f"Morceau actuel ({status}) : {_fmt_track(state)}."


def playback_control(action):
    spotify_client.playback_control(action)
    labels = {
        "pause": "Lecture mise en pause.",
        "resume": "Lecture relancée.",
        "next": "Passage au morceau suivant.",
        "previous": "Retour au morceau précédent.",
    }
    return labels.get(action, f"Action {action} effectuée.")


def set_volume(percent):
    spotify_client.set_volume(percent)
    return f"Volume réglé à {percent} %."


TOOL_HANDLERS = {
    "list_playlists": list_playlists,
    "play_playlist": play_playlist,
    "play_track": play_track,
    "queue_track": queue_track,
    "recommend_tracks": recommend_tracks,
    "dj_mode": dj_mode,
    "current_track": current_track,
    "playback_control": playback_control,
    "set_volume": set_volume,
}

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "list_playlists",
            "description": "Lister les playlists Spotify de l'utilisateur.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "play_playlist",
            "description": "Lancer la lecture d'une playlist de l'utilisateur à partir de son nom.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Nom de la playlist (une partie du nom suffit)",
                    }
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "play_track",
            "description": (
                "Lancer immédiatement la lecture d'un morceau à partir d'un titre, "
                "d'un artiste ou d'une description."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Titre, artiste ou description du morceau"}
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "queue_track",
            "description": "Ajouter un morceau à la file d'attente sans couper la lecture en cours.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Titre, artiste ou description du morceau"}
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "recommend_tracks",
            "description": "Proposer des morceaux correspondant à un thème, une ambiance ou un genre.",
            "parameters": {
                "type": "object",
                "properties": {
                    "theme": {"type": "string", "description": "Thème, ambiance ou genre demandé"},
                    "limit": {"type": "integer", "description": "Nombre de suggestions (défaut : 5)"},
                },
                "required": ["theme"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "dj_mode",
            "description": (
                "Lancer le mode DJ : une session d'antenne continue sur un thème, avec des morceaux "
                "enchaînés et des annonces d'animateur radio entre chacun. Bloquant jusqu'à la fin "
                "de la session ou l'interruption par l'utilisateur."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "theme": {"type": "string", "description": "Thème de la session DJ"},
                    "tracks_count": {
                        "type": "integer",
                        "description": "Nombre de morceaux dans la setlist (défaut : 8)",
                    },
                },
                "required": ["theme"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "current_track",
            "description": "Donner le morceau en cours de lecture et son état.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "playback_control",
            "description": "Contrôler la lecture en cours.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["pause", "resume", "next", "previous"],
                        "description": "Action à effectuer sur la lecture",
                    }
                },
                "required": ["action"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_volume",
            "description": "Régler le volume de la lecture.",
            "parameters": {
                "type": "object",
                "properties": {
                    "percent": {"type": "integer", "minimum": 0, "maximum": 100}
                },
                "required": ["percent"],
            },
        },
    },
]
