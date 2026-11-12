# 🎙️ DJ Neon

Ta radio personnelle, hébergée chez toi : une petite IA qui contrôle ton Spotify sur simple demande, propose des musiques selon ton humeur, et peut prendre le rôle d'un animateur radio avec des transitions entre les morceaux.

## Fonctionnalités (v1)

- **Interface texte** dans le terminal, en langage naturel (français)
- **Contrôle Spotify** uniquement sur demande explicite : playlists, morceaux, file d'attente, volume, pause/suivant/précédent
- **Recommandations** construites à partir de tes titres likés, tes artistes les plus écoutés et une recherche par thème
- **Mode DJ** : une session d'antenne continue sur un thème, avec annonces et transitions générées entre les morceaux
- **Cerveau 100 % local** via [Ollama](https://ollama.com) — aucune demande ne quitte ta machine (sauf celles destinées à l'API Spotify)

## Prérequis

- **Python 3.10+**
- **[Ollama](https://ollama.com/download)** installé et lancé
- Un compte **Spotify** ajouté comme utilisateur de ton app sur le [dashboard développeur](https://developer.spotify.com/dashboard)
- **Spotify Premium** est requis pour contrôler la lecture à distance (l'API de Spotify l'impose). Avec un compte gratuit, seules les lectures de données (playlists, recherche) fonctionnent.
- Spotify doit être **ouvert sur au moins un appareil** (appli mobile, appli bureau, lecteur web) pour lancer une lecture.

## Installation

```bash
git clone https://github.com/Wellonyx63/DJ_Neon.git
cd DJ_Neon

python3 -m venv .venv
source .venv/bin/activate        # Windows : .venv\Scripts\activate

pip install -r requirements.txt
```

Télécharge le modèle local (une seule fois, ~5 Go) :

```bash
ollama pull llama3.1:8b
```

## Configuration

Copie le modèle de configuration puis remplis tes identifiants :

```bash
cp .env.example .env
```

Sur le [dashboard développeur Spotify](https://developer.spotify.com/dashboard), crée une app (ex. `DJ Neon`) :
- **Redirect URI** : `http://127.0.0.1:8888/callback`
- APIs utilisées : **Web API**
- Dans **User Management**, ajoute ton compte Spotify

Puis renseigne dans `.env` :
- `SPOTIFY_CLIENT_ID` et `SPOTIFY_CLIENT_SECRET` (Settings de ton app)

⚠️ Ne partage jamais ton `.env` ni ton `Client Secret` — il est déjà exclu du dépôt via `.gitignore`.

## Utilisation

```bash
python main.py
```

Au premier lancement, ton navigateur s'ouvre pour autoriser DJ Neon sur ton compte Spotify.

Exemples de demandes :

```
toi > montre-moi mes playlists
toi > lance ma playlist Sport
toi > mets du Daft Punk
toi > ajoute One More Time à la file
toi > qu'est-ce qui passe en ce moment ?
toi > volume à 40
toi > propose-moi des morceaux pour une soirée calme
toi > mode DJ sur le thème des années 80
```

Commandes spéciales : `/help` (aide), `/quit` (sortir). Pendant une session DJ, `Ctrl+C` fait sortir de l'antenne sans fermer l'application.

## Architecture

```
main.py             Interface texte (boucle de conversation)
brain.py            Cerveau Ollama : compréhension + tool calling
tools.py            Actions que l'IA peut déclencher (schémas + handlers)
spotify_client.py   Couche Spotify : authentification, playlists, lecture
dj.py               Mode DJ : setlist, annonces, transitions, surveillance de la lecture
config.py           Chargement de la configuration (.env)
```

Le cerveau est isolé derrière `brain.py` : si tu veux passer à l'API Mistral plus tard, seule cette fichier change.

## Dépannage

| Problème | Solution |
|---|---|
| « Ollama est injoignable » | Lance `ollama serve` puis `ollama pull llama3.1:8b` |
| « Aucun appareil Spotify détecté » | Ouvre Spotify (appli ou web) et lance une lecture, puis réessaie |
| Erreur 403 | Vérifie que ton compte est dans **User Management** de l'app, et que tu as Premium |
| L'IA n'appelle jamais les outils | Utilise un modèle qui supporte le tool calling : `llama3.1:8b`, `mistral-nemo`, `qwen2.5:14b`… |
| Session expirée (401) | Supprime le fichier `.spotify_token_cache` et relance |

## Feuille de route

- [ ] Interface vocale : micro (Whisper) + voix de synthèse (Piper) pour le mode DJ
- [ ] Bascule optionnelle vers l'API Mistral pour un cerveau plus puissant
- [ ] Petite interface web au lieu du terminal
- [ ] Déploiement serveur : service systemd ou conteneur Docker
