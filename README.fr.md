<p align="center">
  <a href="README.md">简体中文</a> ·
  <a href="README.en.md">English</a> ·
  <a href="README.de.md">Deutsch</a> ·
  <strong>Français</strong>
</p>

# med-sales — Système de gestion des ventes pharmaceutiques

## 📱 Démonstration mobile

[![Démonstration mobile de med-sales](https://i0.hdslb.com/bfs/archive/016f6b1605ed0a0f41d2d0ef63496fee8cb18bef.jpg)](https://www.bilibili.com/video/BV1WtnQ6BE7F/)

[![Regarder la démonstration mobile sur Bilibili](https://img.shields.io/badge/Bilibili-Regarder_la_d%C3%A9mo-00A1D6?logo=bilibili&logoColor=white)](https://www.bilibili.com/video/BV1WtnQ6BE7F/)
[![Télécharger l’APK Android](https://img.shields.io/badge/GitHub_Releases-T%C3%A9l%C3%A9charger_l%27APK_Android-2ea44f?logo=android&logoColor=white)](https://github.com/dfxiang/med-sales/releases/download/26.10.1/medsales-release-unsigned-26.10.26.1.apk)

L’espace de travail mobile des ventes est disponible sur Android. Il comprend le tableau de bord
d’activité, les commandes de vente, la consultation des stocks, les alertes d’expiration GSP et les
paramètres du profil. La démonstration dure 41 secondes ; l’APK prend en charge Android 8.0 (API 26)
et les versions ultérieures, avec une adresse de serveur API configurable.

> Téléchargement : `medsales-release-unsigned-26.10.26.1.apk`
> ([Release 26.10.1](https://github.com/dfxiang/med-sales/releases/tag/26.10.1)). Cette version n’est
> pas signée. Android demande donc l’autorisation d’installer des applications de sources inconnues.
> Signez l’APK avec votre propre certificat pour une distribution en production. Consultez le
> [client Android](android/README.md) pour les instructions de compilation et les aspects de sécurité.

Un système de gestion des ventes destiné aux **grossistes en médicaments, vaccins et dispositifs
médicaux**. Il couvre toute la chaîne métier : clients, produits, achats, ventes, stocks, retours,
encaissements, rapports et conformité GSP chinoise.

Backend : FastAPI (entièrement asynchrone) sur PostgreSQL 17. Frontend : Vue 3 + Element Plus. Le
dépôt fournit un générateur déterministe de données de démonstration couvrant quatre ans et demi
d’activité, ainsi qu’une configuration Docker Compose pour l’ensemble de la pile.

[![License](https://img.shields.io/badge/License-Apache--2.0%20%2B%20Commons%20Clause-3b6ea5.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-async-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Vue](https://img.shields.io/badge/Vue-3-42b883.svg?logo=vuedotjs&logoColor=white)](https://vuejs.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-17-4169E1.svg?logo=postgresql&logoColor=white)](https://www.postgresql.org/)

## Captures d’écran

![Rapport des ventes](docs/images/sales-report.png)

![Commandes de vente](docs/images/sales-orders.png)

![Consultation des stocks](docs/images/inventory-stock.png)

## Fonctionnalités

| Module | Description |
| --- | --- |
| Authentification | Connexion JWT, échange de jeton par clé API pour l’intégration système, gestion autonome du profil, de l’avatar et du mot de passe |
| Administration système | Utilisateurs (nom affiché, téléphone, e-mail, avatar), rôles, autorisations, journal d’audit et réinitialisation des mots de passe par un administrateur |
| Organisation | Départements et dossiers du personnel |
| Clients | Fiches clients, type et niveau, limite de crédit et statut |
| Produits | Produits, catégories, fabricants et historique des modifications de prix |
| Fournisseurs | Fiches fournisseurs, conditions de règlement et statut de collaboration |
| Entrepôts | Données des entrepôts nationaux et capacité de chaîne du froid |
| Achats | Bons de commande, réception des marchandises (y compris partielle) et entrée en stock |
| Ventes | Commandes de vente, calcul automatique des prix, contrôle des stocks, expédition et annulation |
| Stocks | Consultation des stocks avec statut d’alerte, soldes d’ouverture et traçabilité complète des mouvements |
| Retours | Bons de retour, motifs et traitement de la remise en stock |
| Encaissements | Enregistrement des paiements, rapprochement des commandes et analyse du vieillissement des créances |
| Rapports | Ventes quotidiennes et mensuelles, synthèses par client, commercial et produit, détails des commandes et tableau de bord |
| Conformité GSP | Dossiers de qualification des premiers approvisionnements (contrôle des certificats et pièces numérisées), blocage des transactions, centre d’alertes d’expiration et suivi des lots et des dates de péremption |
| Mobile | Client Android 8.0+ basé sur WebView avec tableau de bord, commandes de vente, stocks, alertes GSP et profil |

## Technologies

| Couche | Technologie |
| --- | --- |
| Backend | Python 3.12, FastAPI, SQLAlchemy 2.0 (asynchrone), Pydantic v2, JWT (hachage des mots de passe PBKDF2-SHA256) |
| Frontend | Vue 3, TypeScript, Vite, Element Plus, Pinia, Vue Router 4, Axios, ECharts |
| Base de données | PostgreSQL 17 (asyncpg) ; SQLite en mémoire (aiosqlite) pour les tests unitaires |
| Stockage d’objets | MinIO (compatible S3) pour les certificats GSP et les avatars |
| Tests | pytest + httpx (API), Playwright (E2E et régression sur un déploiement actif) |
| Déploiement | Docker / Docker Compose, nginx (fichiers statiques + proxy `/api` de même origine) |

## Arborescence du dépôt

```
med-sales/
├── docs/                       # Documentation sur l’API, la base de données, les droits, GSP, les rapports et les profils
│   └── images/                 # Captures d’écran utilisées par les fichiers README
├── api/                        # Backend (FastAPI, entièrement asynchrone)
│   ├── app/                    # Code applicatif (core / models / schemas / api/routes / services)
│   ├── tests/                  # Tests de l’API backend
│   ├── scripts/                # Initialisation admin, catalogue de droits, docs API, agrégats de rapports
│   ├── Dockerfile              # Image backend (python:3.12-slim, sans privilèges root)
│   └── docker-compose.yml      # Configuration Compose pour le backend seul
├── frontend/                   # Frontend (Vue 3 + TypeScript)
│   ├── src/                    # Pages, composants, routeur, stores et couche de requêtes
│   ├── tests/e2e/              # Suite Playwright isolée (backend et données de test dédiés)
│   ├── tests/live/             # Tests de régression sur un déploiement actif
│   ├── Dockerfile              # Build multi-étapes : compilation Node → nginx
│   └── nginx.conf              # Fichiers statiques + proxy inverse /api
├── android/                    # Espace mobile Android (WebView + pont réseau natif)
├── db/                         # Initialisation de la base et génération des données de démonstration
│   ├── schema.sql              # DDL de 18 tables métier + 7 vues (commentaires en chinois)
│   ├── mock_params.py          # Volume de données, période et objectifs annuels
│   ├── generate_mock_data.py   # Génère quatre ans et demi de données de démonstration
│   └── run_all.py              # Créer → générer → vérifier
├── docker-compose.yml          # Base de données + stockage d’objets + backend + frontend
├── .env.example                # Modèle pour les ports, mots de passe et fuseau horaire
├── .github/                    # Formulaires d’issue et modèle de PR
├── AGENTS.md                   # Conventions de développement du dépôt
└── LICENSE
```

## Démarrage rapide

```bash
git clone https://github.com/dfxiang/med-sales.git
cd med-sales
```

### Prérequis

- Docker et Docker Compose v2 ;
- Python 3.12 ou version ultérieure, uniquement pour générer les données de démonstration.

PostgreSQL 17 et MinIO sont inclus dans `docker-compose.yml`. La base de données doit utiliser
**UTF-8 avec le classement ICU `zh-u-co-pinyin`** (tri des caractères chinois par pinyin). Consultez
le guide en chinois [docs/数据库部署与配置.md](docs/数据库部署与配置.md) pour les installations
avec conteneur ou natives.

### Premier démarrage

```bash
# 1. Démarrer d’abord la base de données (le reste suivra)
docker compose up -d medsales-db

# 2. Créer le schéma, générer 4,5 ans de données et les vérifier (environ 2 minutes)
cd db
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python run_all.py
cd ..

# 3. Démarrer le backend, le frontend et le stockage d’objets
docker compose up -d --build

# 4. Créer une seule fois le compte administrateur après le premier démarrage
docker compose exec medsales-api python scripts/create_admin.py --username admin --password VOTRE_MOT_DE_PASSE

# 5. Remplir les tables d’agrégats des rapports (sinon les rapports affichent 0)
docker compose exec medsales-api python scripts/rebuild_sales_rollup.py
```

Les ports, mots de passe et le fuseau horaire peuvent être configurés dans le fichier `.env` à la
racine du dépôt (`cp .env.example .env`). Si le port hôte 5688 est déjà utilisé, modifiez
`MEDSALES_DB_PORT` et indiquez le même port aux scripts de données avec
`MEDSALESDB_PORT=<port>`.

| Point d’entrée | URL |
| --- | --- |
| Interface Web | http://127.0.0.1:8088 |
| API | http://127.0.0.1:8001 |
| Swagger | http://127.0.0.1:8001/docs |
| Console MinIO | http://127.0.0.1:9021 |

### Développement local (sans Docker)

```bash
# Backend
cd api
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env                                          # adapter la connexion à la base
.venv/bin/python scripts/create_admin.py --username admin --password VOTRE_MOT_DE_PASSE
.venv/bin/python scripts/seed_permissions.py --with-roles     # facultatif : modèles de rôles intégrés
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000

# Frontend
cd frontend
npm install
npm run dev                                                   # http://127.0.0.1:5273
```

Le serveur de développement appelle `http://127.0.0.1:8001/api` (voir
`frontend/.env.development`). Dans les conteneurs, il utilise le chemin relatif `/api`, redirigé par
nginx.

### Configuration

Les paramètres du backend proviennent de variables d’environnement ou de `api/.env` (voir
`api/.env.example`) ; dans les conteneurs, ils sont injectés par `docker-compose.yml`. Voici les
principaux paramètres :

| Variable | Valeur par défaut | Description |
| --- | --- | --- |
| `DATABASE_URL` | `postgresql+asyncpg://postgres:pass01!@medsales-db:5432/medsalesdb` | Chaîne de connexion à la base (à modifier pour une base externe) |
| `TZ` | `Asia/Shanghai` | Fuseau horaire des conteneurs ; utilisé pour les indicateurs « aujourd’hui », l’ancienneté des créances et l’expiration des certificats |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | `postgres` / `pass01!` / `medsalesdb` | Identifiants de la base intégrée (**à modifier en production**) |
| `POSTGRES_INITDB_ARGS` | ICU `zh-u-co-pinyin` + UTF8 | Appliqué uniquement lorsque le volume de données est vide |
| `MEDSALES_DB_PORT` / `MEDSALES_API_PORT` / `MEDSALES_WEB_PORT` | `5688` / `8001` / `8088` | Mappages des ports de l’hôte |
| `JWT_SECRET` | `medsales-change-me-…` | **À modifier impérativement en production** |
| `SYS_API_KEYS` | vide | Clés API pour l’intégration système (séparées par des virgules, rotation prise en charge) |
| `CORS_ORIGINS` | `*` | Origines autorisées ; à restreindre en production |
| `MINIO_ROOT_USER` / `MINIO_ROOT_PASSWORD` | `medsales` / `medsales-minio-secret` | Identifiants du stockage d’objets (**à modifier en production**) |
| `GSP_ENFORCE_QUALIFICATION` | `true` | Bloquer les transactions lorsqu’un certificat d’une entité enregistrée est expiré, en attente ou refusé |
| `GSP_STRICT_QUALIFICATION` | `false` | Mode strict : bloquer également les entités sans dossier de qualification |
| `GSP_EXPIRY_WARNING_DAYS` | `90` | Délai d’alerte avant l’expiration d’un certificat (en jours) |

> Liste de contrôle de sécurité pour le déploiement : [SECURITY.md](SECURITY.md) (en chinois).

## Base de données et données de démonstration

Prérequis : **PostgreSQL 17**, encodage `UTF8` et classement ICU `zh-u-co-pinyin`. Consultez le guide
en chinois [docs/数据库部署与配置.md](docs/数据库部署与配置.md) pour l’installation avec conteneur ou
native, le classement et le fuseau horaire, le raccordement à une base existante ainsi que la
sauvegarde et la restauration.

La base d’origine contient 18 tables métier et 7 vues de rapports. Le projet ajoute des tables système
pour les utilisateurs et autorisations, les lots et les certificats. Elles sont créées automatiquement
au démarrage de l’API ; les tables existantes ne sont pas modifiées.

```bash
cd db
.venv/bin/python run_all.py            # créer et initialiser la base si nécessaire
.venv/bin/python run_all.py --reset    # supprimer puis recréer
```

Les rapports lisent des tables d’agrégats. Après la génération des données, il faut donc les remplir
une fois :
`docker compose exec medsales-api python scripts/rebuild_sales_rollup.py`.

## Tests

```bash
# Backend (SQLite en mémoire, aucune base réelle requise)
cd api && .venv/bin/python -m pytest -q

# Build du frontend
cd frontend && npm run build

# E2E du frontend (démarre un backend isolé sur le port 8002 et un serveur de dev sur le port 5273)
cd frontend && npx playwright test

# Tests de régression sur un déploiement actif (8088/8001 doivent être disponibles)
cd frontend && npx playwright test --config playwright.live.config.ts
```

## Documentation

Toutes les documentations détaillées actuellement disponibles sont rédigées en chinois :

| Document | Contenu |
| --- | --- |
| [docs/API接口文档.md](docs/API接口文档.md) | Référence API chinoise générée automatiquement, avec paramètres et exemples |
| [docs/数据库部署与配置.md](docs/数据库部署与配置.md) | Déploiement PostgreSQL 17, UTF-8 + classement pinyin, fuseau horaire, sauvegarde/restauration |
| [docs/GSP合规闭环.md](docs/GSP合规闭环.md) | Processus GSP : contrôle des qualifications, blocage des transactions, alertes d’expiration et archivage des renouvellements |
| [docs/权限控制说明.md](docs/权限控制说明.md) | Modèle d’autorisations, conventions de nommage et guide d’extension |
| [docs/销售报表汇总表.md](docs/销售报表汇总表.md) | Tables d’agrégats, ordre de maintenance, remplissage et rapprochement |
| [docs/用户资料扩展设计.md](docs/用户资料扩展设计.md) | Champs du profil, gestion autonome du mot de passe, réinitialisation par l’administrateur et sécurité des avatars |
| [docs/许可与商用说明.md](docs/许可与商用说明.md) | Utilisations autorisées et cas nécessitant une licence commerciale (en chinois) |
| [db/README.md](db/README.md) | Scripts de la base de démonstration, paramètres de connexion et volume de données |
| [api/README.md](api/README.md) · [frontend/README.md](frontend/README.md) | Détails techniques du backend et du frontend |

## Contribution

Les issues et pull requests sont les bienvenues. Consultez [CONTRIBUTING.md](CONTRIBUTING.md) (en
chinois) pour l’environnement, le processus et les conventions de code. Signalez les problèmes de
sécurité de manière confidentielle en suivant la procédure décrite dans [SECURITY.md](SECURITY.md).

## Licence et utilisation commerciale

Ce projet est distribué sous **Apache License 2.0 avec la condition Commons Clause v1.0**. Le texte
intégral se trouve dans [LICENSE](LICENSE).

| Vous pouvez | Vous ne pouvez pas |
| --- | --- |
| L’utiliser à des fins commerciales dans votre propre entreprise, le modifier et le faire évoluer (vos modifications peuvent rester fermées) | Intégrer le logiciel (ou l’essentiel de ses fonctionnalités) à un produit ou service et facturer des tiers pour son utilisation |
| Le copier et le redistribuer gratuitement (en conservant les mentions de copyright et de licence) | Le proposer sous forme de service d’hébergement payant (SaaS), de conseil payant ou de support payant |
| L’étudier et l’utiliser à des fins pédagogiques | Supprimer ou modifier les mentions de copyright et de licence |

> Remarque : en raison de la condition d’interdiction de vente, ce projet est **source-available et ne
> constitue pas un logiciel open source certifié par l’OSI** (GitHub affiche la licence comme
> « Other »). Explications complètes dans [docs/许可与商用说明.md](docs/许可与商用说明.md).

Licences commerciales, développement sur mesure et support (le titulaire des droits peut accorder des
conditions distinctes) : `4198166@qq.com` · WeChat `4198166` · téléphone `+86 185 7281 7101`.

## Avertissement

- Toutes les entreprises et données métier présentes dans ce dépôt (y compris la société fictive
  « 华康医药销售有限公司 », ses clients, ses prix et ses documents) sont **générées par des scripts**
  et sans rapport avec une organisation réelle. Ne les utilisez pas pour prendre des décisions
  commerciales.
- Ce projet est un logiciel générique de gestion des ventes. Il ne s’agit pas d’un dispositif médical
  et il ne fournit aucun conseil médical ou de prescription.
- Les fonctions GSP sont des outils auxiliaires destinés à structurer un processus de conformité ;
  elles **ne garantissent pas la conformité**. L’exploitation réelle doit respecter la réglementation
  locale et être contrôlée par des responsables qualité qualifiés.
- Le logiciel est fourni « en l’état », sans garantie explicite ou implicite. Avant une mise en
  production, réalisez votre propre évaluation de sécurité et conservez des sauvegardes.

## Soutenir le projet

Si ce projet vous est utile, vous pouvez m’offrir un café. Les dons sont entièrement facultatifs et
n’ont aucune incidence sur vos droits d’utilisation.

<table>
  <tr>
    <td align="center">
      <img src="weixin.jpg" alt="QR code WeChat de l’auteur" width="260"><br>
      <sub>Scannez le QR code pour échanger sur WeChat</sub>
    </td>
    <td align="center">
      <img src="donation.jpg" alt="QR code de don pour le projet" width="260"><br>
      <sub>Offrez-moi un café et soutenez la maintenance du projet</sub>
    </td>
  </tr>
</table>
