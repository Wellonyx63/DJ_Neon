import re
import time

import spotipy
from spotipy.exceptions import SpotifyException

from config import (
    SPOTIFY_CLIENT_ID,
    SPOTIFY_CLIENT_SECRET,
    SPOTIFY_REDIRECT_URI,
    SPOTIFY_SCOPES,
    TOKEN_CACHE_PATH,
)

_spotify = None
SEARCH_LIMIT_MAX = 10


class SpotifyError(Exception):
    pass


def _friendly_error(exc):
    if exc.http_status == 403:
        return (
            "Spotify a refusé l'action (403). Vérifie que ton compte est bien ajouté dans "
            "User Management de ton app développeur, et que tu as Spotify Premium pour "
            "contrôler la lecture."
        )
    if exc.http_status == 401:
        return "Session Spotify expirée : supprime le fichier .spotify_token_cache et relance."
    if exc.http_status == 404:
        return (
            "Aucun appareil Spotify actif trouvé. Ouvre Spotify sur ton téléphone ou ton "
            "ordinateur, lance une lecture, puis réessaie."
        )
    return f"Erreur Spotify ({exc.http_status}) : {exc.msg}"


def _call(action):
    try:
        return action()
    except SpotifyException as exc:
        raise SpotifyError(_friendly_error(exc)) from exc


def get_spotify():
    global _spotify
    if _spotify is None:
        if not SPOTIFY_CLIENT_ID or not SPOTIFY_CLIENT_SECRET:
            raise SpotifyError(
                "Configuration Spotify manquante : copie .env.example en .env et remplis "
                "SPOTIFY_CLIENT_ID et SPOTIFY_CLIENT_SECRET."
            )
        auth_manager = spotipy.SpotifyOAuth(
            client_id=SPOTIFY_CLIENT_ID,
            client_secret=SPOTIFY_CLIENT_SECRET,
            redirect_uri=SPOTIFY_REDIRECT_URI,
            scope=" ".join(SPOTIFY_SCOPES),
            cache_path=TOKEN_CACHE_PATH,
            open_browser=True,
        )
        _spotify = spotipy.Spotify(auth_manager=auth_manager)
    return _spotify


def ensure_device():
    sp = get_spotify()
    devices = _call(lambda: sp.devices()).get("devices", [])
    if not devices:
        raise SpotifyError(
            "Aucun appareil Spotify détecté. Ouvre Spotify quelque part (appli mobile, "
            "appli bureau ou lecteur web), puis réessaie."
        )
    active = next((d for d in devices if d.get("is_active")), None)
    return (active or devices[0])["id"]


def _track_brief(track):
    return {
        "name": track["name"],
        "artist": ", ".join(a["name"] for a in track["artists"]),
        "uri": track["uri"],
    }


def list_playlists(limit=50):
    sp = get_spotify()
    result = _call(lambda: sp.current_user_playlists(limit=limit))
    playlists = []
    for p in result.get("items", []):
        if not p:
            continue
        info = p.get("items") or p.get("tracks") or {}
        total = info.get("total", 0) if isinstance(info, dict) else len(info)
        playlists.append({"name": p["name"], "tracks": total, "uri": p["uri"]})
    return playlists


def find_playlist(name):
    target = name.strip().lower()
    for playlist in list_playlists():
        if target in playlist["name"].lower():
            return playlist
    return None


def play_playlist(name):
    playlist = find_playlist(name)
    if playlist is None:
        return None
    device_id = ensure_device()
    sp = get_spotify()
    _call(lambda: sp.start_playback(device_id=device_id, context_uri=playlist["uri"]))
    return playlist


def _search_limit(limit):
    return max(1, min(int(limit), SEARCH_LIMIT_MAX))


def search_tracks(query, limit=5):
    sp = get_spotify()
    limit = _search_limit(limit)
    result = _call(lambda: sp.search(q=query, type="track", limit=limit))
    return [
        {
            "name": t["name"],
            "artist": ", ".join(a["name"] for a in t["artists"]),
            "album": t["album"]["name"],
            "uri": t["uri"],
            "duration_min": round(t["duration_ms"] / 60000, 1),
        }
        for t in result.get("tracks", {}).get("items", [])
        if t
    ]


def play_tracks(uris):
    device_id = ensure_device()
    sp = get_spotify()
    _call(lambda: sp.start_playback(device_id=device_id, uris=list(uris)))


def _is_playing(sp, uri):
    state = _call(lambda: sp.current_playback())
    return (
        bool(state)
        and state.get("item", {}).get("uri") == uri
        and state.get("is_playing", False)
    )


def play_track(query):
    queries = [query.strip()]
    match = re.match(r"^(.*?)\s+(?:de|par|du|by)\s+(.+)$", query.strip(), flags=re.IGNORECASE)
    if match:
        title, artist = match.group(1).strip(), match.group(2).strip()
        if title and artist:
            queries.insert(0, f"track:{title} artist:{artist}")
            queries.append(title)
    tracks = []
    for candidate in queries:
        tracks = search_tracks(candidate, limit=1)
        if tracks:
            break
    if not tracks:
        raise SpotifyError(f"Aucun morceau trouvé pour « {query} ».")
    track = tracks[0]
    device_id = ensure_device()
    sp = get_spotify()
    _call(lambda: sp.start_playback(device_id=device_id, uris=[track["uri"]]))
    time.sleep(2)
    if not _is_playing(sp, track["uri"]):
        _call(lambda: sp.start_playback(device_id=device_id, uris=[track["uri"]]))
        time.sleep(2)
    if not _is_playing(sp, track["uri"]):
        _call(lambda: sp.add_to_queue(track["uri"]))
        _call(lambda: sp.next_track(device_id=device_id))
        time.sleep(2)
        if not _is_playing(sp, track["uri"]):
            raise SpotifyError(
                "La lecture n'a pas démarré sur l'appareil. Vérifie que Spotify est ouvert "
                "et actif sur un appareil, puis réessaie."
            )
    return track


def play_artist(query):
    artist_name = query.strip()
    tracks = search_tracks(f"artist:{artist_name}", limit=SEARCH_LIMIT_MAX)
    if not tracks:
        tracks = search_tracks(artist_name, limit=SEARCH_LIMIT_MAX)
    if not tracks:
        artists = search_artists(artist_name, limit=1)
        if artists:
            tracks = search_tracks(f"artist:{artists[0]['name']}", limit=SEARCH_LIMIT_MAX)
    if not tracks:
        raise SpotifyError(f"Aucun morceau de « {artist_name} » trouvé sur Spotify.")
    play_tracks([t["uri"] for t in tracks])
    return tracks


def search_playlists(query, limit=5):
    sp = get_spotify()
    limit = _search_limit(limit)
    result = _call(lambda: sp.search(q=query, type="playlist", limit=limit))
    playlists = []
    for p in result.get("playlists", {}).get("items", []):
        if not p:
            continue
        info = p.get("items") or p.get("tracks") or {}
        total = info.get("total", 0) if isinstance(info, dict) else len(info)
        playlists.append(
            {
                "name": p["name"],
                "owner": (p.get("owner") or {}).get("display_name") or "Spotify",
                "tracks": total,
                "uri": p["uri"],
            }
        )
    return playlists


def search_artists(query, limit=5):
    sp = get_spotify()
    limit = _search_limit(limit)
    result = _call(lambda: sp.search(q=query, type="artist", limit=limit))
    return [
        {
            "name": a["name"],
            "genres": ", ".join(a.get("genres", [])[:3]),
            "uri": a["uri"],
        }
        for a in result.get("artists", {}).get("items", [])
        if a
    ]


def search_albums(query, limit=5):
    sp = get_spotify()
    limit = _search_limit(limit)
    result = _call(lambda: sp.search(q=query, type="album", limit=limit))
    return [
        {
            "name": al["name"],
            "artist": ", ".join(a["name"] for a in al["artists"]),
            "uri": al["uri"],
        }
        for al in result.get("albums", {}).get("items", [])
        if al
    ]


def play_public_playlist(query):
    playlists = search_playlists(query, limit=5)
    if not playlists:
        raise SpotifyError(
            f"Aucune playlist trouvée dans le catalogue Spotify pour « {query} »."
        )
    device_id = ensure_device()
    sp = get_spotify()
    _call(lambda: sp.start_playback(device_id=device_id, context_uri=playlists[0]["uri"]))
    return playlists[0]


def add_to_queue(uri):
    sp = get_spotify()
    _call(lambda: sp.add_to_queue(uri))


def get_playback_state():
    sp = get_spotify()
    state = _call(lambda: sp.current_playback())
    if not state or not state.get("item"):
        return {"playing": False, "track": None, "artist": None, "shuffle": None}
    item = state["item"]
    return {
        "playing": state.get("is_playing", False),
        "track": item["name"],
        "artist": ", ".join(a["name"] for a in item["artists"]),
        "shuffle": state.get("shuffle_state"),
    }


def get_current_track():
    sp = get_spotify()
    state = _call(lambda: sp.current_playback())
    if not state or not state.get("item"):
        return None
    item = state["item"]
    return {
        "name": item["name"],
        "artist": ", ".join(a["name"] for a in item["artists"]),
        "uri": item["uri"],
        "progress_ms": state.get("progress_ms") or 0,
        "duration_ms": item["duration_ms"],
        "is_playing": state.get("is_playing", False),
    }


def playback_control(action):
    sp = get_spotify()
    if action == "pause":
        _call(lambda: sp.pause_playback())
    elif action == "resume":
        _call(lambda: sp.start_playback(device_id=ensure_device()))
    elif action == "next":
        _call(lambda: sp.next_track())
    elif action == "previous":
        _call(lambda: sp.previous_track())
    else:
        raise SpotifyError(f"Action de lecture inconnue : {action}")


def set_shuffle(state):
    device_id = ensure_device()
    sp = get_spotify()
    _call(lambda: sp.shuffle(bool(state), device_id=device_id))


def set_volume(percent):
    device_id = ensure_device()
    sp = get_spotify()
    _call(lambda: sp.volume(int(percent), device_id=device_id))


def get_top_tracks(limit=10):
    sp = get_spotify()
    result = _call(lambda: sp.current_user_top_tracks(limit=limit, time_range="short_term"))
    if not result.get("items"):
        result = _call(lambda: sp.current_user_top_tracks(limit=limit, time_range="medium_term"))
    return [_track_brief(t) for t in result.get("items", []) if t]


def get_saved_tracks(limit=20):
    sp = get_spotify()
    result = _call(lambda: sp.current_user_saved_tracks(limit=limit))
    return [_track_brief(i["track"]) for i in result.get("items", []) if i.get("track")]


def recommend_tracks(theme, limit=6):
    theme_lower = theme.strip().lower()
    candidates = []
    seen = set()

    def add(track):
        if track and track["uri"] not in seen:
            seen.add(track["uri"])
            candidates.append(track)

    for pool in (get_top_tracks(limit=15), get_saved_tracks(limit=15), search_tracks(theme, limit=15)):
        try:
            for track in pool:
                add(track)
        except SpotifyError:
            continue

    def score(track):
        text = f"{track['name']} {track['artist']}".lower()
        return 2 if theme_lower and theme_lower in text else 0

    candidates.sort(key=score, reverse=True)
    return candidates[:limit]
