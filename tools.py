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


def play_artist(query):
    tracks = spotify_client.play_artist(query)
    first = tracks[0]
    return (
        f"Lecture lancée : {len(tracks)} morceaux de {first['artist']}, en commençant par "
        f"« {first['name']} »."
    )


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


def search_music(query, search_type="track", limit=5):
    limit = max(1, min(int(limit), 10))
    if search_type == "track":
        tracks = spotify_client.search_tracks(query, limit=limit)
        if not tracks:
            return f"Aucun morceau trouvé pour « {query} »."
        lines = [f"- « {t['name']} » de {t['artist']} ({t['duration_min']} min)" for t in tracks]
        return (
            f"Résultats pour « {query} » :\n"
            + "\n".join(lines)
            + "\nPrésente-les à l'utilisateur ; il peut demander à en lancer un avec play_track."
        )
    if search_type == "playlist":
        playlists = spotify_client.search_playlists(query, limit=limit)
        if not playlists:
            return f"Aucune playlist trouvée pour « {query} »."
        lines = [f"- « {p['name']} » de {p['owner']} ({p['tracks']} morceaux)" for p in playlists]
        return (
            f"Playlists trouvées pour « {query} » :\n"
            + "\n".join(lines)
            + "\nL'utilisateur peut en lancer une avec play_public_playlist."
        )
    if search_type == "artist":
        artists = spotify_client.search_artists(query, limit=limit)
        if not artists:
            return f"Aucun artiste trouvé pour « {query} »."
        lines = [
            f"- {a['name']}" + (f" ({a['genres']})" if a["genres"] else "")
            for a in artists
        ]
        return f"Artistes trouvés pour « {query} » :\n" + "\n".join(lines)
    if search_type == "album":
        albums = spotify_client.search_albums(query, limit=limit)
        if not albums:
            return f"Aucun album trouvé pour « {query} »."
        lines = [f"- « {al['name']} » de {al['artist']}" for al in albums]
        return f"Albums trouvés pour « {query} » :\n" + "\n".join(lines)
    return f"Type de recherche inconnu : {search_type} (track, playlist, artist ou album)."


def play_public_playlist(query):
    playlist = spotify_client.play_public_playlist(query)
    return (
        f"Lecture lancée : playlist « {playlist['name']} » de {playlist['owner']} "
        f"({playlist['tracks']} morceaux)."
    )


def set_shuffle(state):
    if isinstance(state, str):
        state = state.strip().lower() in (
            "true", "on", "1", "oui", "yes", "active", "activé", "enable", "enabled",
        )
    spotify_client.set_shuffle(bool(state))
    return "Mode aléatoire activé." if state else "Mode aléatoire désactivé."


TOOL_HANDLERS = {
    "list_playlists": list_playlists,
    "play_playlist": play_playlist,
    "play_track": play_track,
    "queue_track": queue_track,
    "recommend_tracks": recommend_tracks,
    "play_artist": play_artist,
    "search_music": search_music,
    "play_public_playlist": play_public_playlist,
    "set_shuffle": set_shuffle,
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
            "name": "play_artist",
            "description": (
                "Lancer immédiatement la lecture des meilleurs morceaux d'un artiste, en cherchant "
                "dans tout le catalogue Spotify. À utiliser pour « joue du <artiste> » ou "
                "« mets du <artiste> », même si l'artiste n'est pas dans la bibliothèque de "
                "l'utilisateur."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Nom de l'artiste"}
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_music",
            "description": (
                "Rechercher dans tout le catalogue Spotify (pas seulement les playlists de "
                "l'utilisateur) : morceaux, playlists, artistes ou albums."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Ce qu'il faut rechercher (titre, artiste, genre, ambiance...)",
                    },
                    "search_type": {
                        "type": "string",
                        "enum": ["track", "playlist", "artist", "album"],
                        "description": "Type de résultat souhaité (défaut : track)",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Nombre de résultats (défaut : 5, maximum : 10)",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "play_public_playlist",
            "description": (
                "Rechercher une playlist dans tout le catalogue Spotify (y compris les playlists "
                "officielles ou d'autres utilisateurs, non enregistrées par l'utilisateur) et "
                "lancer la lecture de la meilleure correspondance."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Thème, genre ou nom de la playlist recherchée",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_shuffle",
            "description": "Activer ou désactiver le mode aléatoire (shuffle) de la lecture.",
            "parameters": {
                "type": "object",
                "properties": {
                    "state": {
                        "type": "boolean",
                        "description": "true pour activer le mode aléatoire, false pour le désactiver. Le mode aléatoire intelligent (smart shuffle) n'est pas disponible via l'API.",
                    }
                },
                "required": ["state"],
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
