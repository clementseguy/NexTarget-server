# NexTarget Server

Backend OAuth pour application mobile NexTarget.
Authentification déléguée à Google et Facebook — aucun mot de passe stocké.

## Stack

Python 3.10+ · FastAPI · SQLModel · SQLite · PyJWT · httpx

## Démarrage rapide

```bash
pip install -r requirements.txt
cp .env.example .env  # puis configurer les valeurs
uvicorn app.main:app --reload
```

La documentation interactive (Swagger) est disponible sur `/docs`.

📖 [Guide détaillé](docs/guides/quickstart.md)

## Configuration

Toute la configuration passe par variables d'environnement (fichier `.env`).
Voir `.env.example` pour la liste complète des variables requises.

## API

La liste complète des endpoints, schémas et exemples est dans la documentation OpenAPI :
- **En local** : `http://localhost:8000/docs`
- **Spec YAML** : [docs/nextarget-api-v0.1.0.yaml](docs/nextarget-api-v0.1.0.yaml)

## Tests

```bash
pytest -q
```

## Déploiement

Configuré pour Render.com via `render.yaml`. Voir [docs/tech/render_setup.md](docs/tech/render_setup.md).

## Documentation

| Document | Contenu |
|---|---|
| [docs/guides/quickstart.md](docs/guides/quickstart.md) | Guide de démarrage rapide |
| [docs/tech/architecture.md](docs/tech/architecture.md) | Architecture et flows OAuth |
| [docs/tech/render_setup.md](docs/tech/render_setup.md) | Guide de déploiement Render |
| [docs/reviews/SECURITY_ANALYSIS.md](docs/reviews/SECURITY_ANALYSIS.md) | Analyse de sécurité |
| [docs/specs/](docs/specs/) | Spécifications et backlog |
| [CHANGELOG.md](CHANGELOG.md) | Historique des changements |
