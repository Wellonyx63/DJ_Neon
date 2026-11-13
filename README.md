# 🎙️ DJ Neon

Ta radio personnelle, hébergée chez toi : une petite IA qui contrôle ton Spotify sur simple demande, propose des musiques selon ton humeur, et peut prendre le rôle d'un animateur radio avec des transitions entre les morceaux.

## Fonctionnalités (v1)

- **Interface texte** dans le terminal, en langage naturel (français)
- **Contrôle Spotify** uniquement sur demande explicite : playlists, morceaux, file d'attente, volume, pause/suivant/précédent
- **Recommandations** construites à partir de tes titres likés, tes artistes les plus écoutés et une recherche par thème
- **Mode DJ** : session d'antenne continue sur un thème, avec annonces et transitions générées entre les morceaux *(en pause — sera repris une fois le reste stabilisé)*
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

### Interface web (recommandée)

```bash
python web.py
```

L'interface s'ouvre automatiquement sur `http://127.0.0.1:8000` : conversation en langage naturel, boutons pause/suivant/précédent/aléatoire, volume et morceau en cours affiché en permanence. Elle n'est accessible que depuis le PC où tourne DJ Neon.

### Terminal

```bash
python main.py
```

Au premier lancement, ton navigateur s'ouvre pour autoriser DJ Neon sur ton compte Spotify.

Exemples de demandes :

```
toi > montre-moi mes playlists
toi > lance ma playlist Sport
toi > mets du Daft Punk
toi > joue du Johnny Hallyday
toi > ajoute One More Time à la file
toi > qu'est-ce qui passe en ce moment ?
toi > volume à 40
toi > propose-moi des morceaux pour une soirée calme
toi > cherche des morceaux de funk
toi > lance une playlist funk de Spotify
toi > mets la lecture en aléatoire
```

Commandes spéciales : `/help` (aide), `/quit` (sortir).

Les commandes simples (suivant, précédent, pause, reprise, volume, aléatoire) sont traitées directement, sans passer par le modèle : elles sont instantanées et fiables.

## Lancement automatique (Windows)

Deux scripts sont fournis dans `windows/` (sans fenêtre visible, en arrière-plan) :

- `start_neon_when_spotify.vbs` — attend que Spotify soit lancé, puis démarre DJ Neon
- `start_neon.vbs` — démarre DJ Neon dès l'ouverture de session

Installation : `Win+R` → tape `shell:startup` → Enter. Dans le dossier qui s'ouvre, colle un **raccourci** vers le script choisi (clic droit sur le script → « Créer un raccourci », puis déplace le raccourci). Au prochain démarrage, DJ Neon se lancera tout seul — l'interface reste disponible sur `http://127.0.0.1:8000`.

Condition : le projet doit rester dans son dossier avec son `.venv` (le script y fait référence).

## Architecture

```
web.py              Interface web locale (chat + contrôles de lecture)
static/index.html   Page de l'interface web (thème sombre néon)
windows/            Scripts de lancement automatique (démarrage session ou au lancement de Spotify)
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
| L'IA n'appelle jamais les outils, ou raconte n'importe quoi | `llama3.1:8b` gère mal le tool calling : essaie `ollama pull qwen2.5:7b` puis `OLLAMA_MODEL=qwen2.5:7b` dans `.env` |
| « Invalid limit » sur une recherche | Limite de l'API Spotify réduite à 10 résultats par recherche depuis février 2026 — DJ Neon plafonne automatiquement, ne pas dépasser |
| Session expirée (401) | Supprime le fichier `.spotify_token_cache` et relance |

## Feuille de route

- [ ] Réactiver et fiabiliser le mode DJ (setlist par thème, annonces d'animateur)
- [ ] Interface vocale : micro (Whisper) + voix de synthèse (Piper)
- [ ] Bascule optionnelle vers l'API Mistral pour un cerveau plus puissant
- [ ] Déploiement serveur : service systemd ou conteneur Docker
