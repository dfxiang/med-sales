<p align="center">
  <a href="README.md">简体中文</a> ·
  <a href="README.en.md">English</a> ·
  <strong>Deutsch</strong> ·
  <a href="README.fr.md">Français</a>
</p>

# med-sales — Vertriebsmanagementsystem für pharmazeutische Produkte

## 📱 Mobile Demo

[![Mobile Demo von med-sales](https://i0.hdslb.com/bfs/archive/016f6b1605ed0a0f41d2d0ef63496fee8cb18bef.jpg)](https://www.bilibili.com/video/BV1WtnQ6BE7F/)

[![Mobile Demo auf Bilibili ansehen](https://img.shields.io/badge/Bilibili-Mobile_Demo_ansehen-00A1D6?logo=bilibili&logoColor=white)](https://www.bilibili.com/video/BV1WtnQ6BE7F/)
[![Android-APK herunterladen](https://img.shields.io/badge/GitHub_Releases-Android_APK_herunterladen-2ea44f?logo=android&logoColor=white)](https://github.com/dfxiang/med-sales/releases/download/26.10.1/medsales-release-unsigned-26.10.26.1.apk)

Der mobile Vertriebsarbeitsplatz ist für Android verfügbar. Er umfasst das betriebliche Dashboard,
Vertriebsaufträge, die Lagerbestandsabfrage, GSP-Ablaufwarnungen und die Profileinstellungen. Die Demo
dauert 41 Sekunden; die APK unterstützt Android 8.0 (API 26) und neuer. Die Adresse des API-Servers
kann konfiguriert werden.

> Download: `medsales-release-unsigned-26.10.26.1.apk`
> ([Release 26.10.1](https://github.com/dfxiang/med-sales/releases/tag/26.10.1)). Dieses Release ist
> nicht signiert. Android verlangt daher die Erlaubnis, Apps aus unbekannten Quellen zu installieren.
> Signieren Sie die APK für die Produktionsverteilung mit Ihrem eigenen Zertifikat. Hinweise zum Build
> und zur Sicherheit finden Sie im [Android-Client](android/README.md).

Ein Vertriebsmanagementsystem für **Grosshändler von Arzneimitteln, Impfstoffen und Medizinprodukten**.
Es deckt die gesamte Geschäftskette ab: Kunden, Produkte, Einkauf, Vertrieb, Lagerbestand, Retouren,
Forderungen, Auswertungen und die chinesische GSP-Konformität.

Backend: FastAPI (vollständig asynchron) auf PostgreSQL 17. Frontend: Vue 3 + Element Plus. Das
Repository enthält einen deterministischen Generator für Testdaten, der Geschäftsdaten für
viereinhalb Jahre erzeugt, sowie eine Docker-Compose-Konfiguration für den gesamten Technologie-Stack.

[![License](https://img.shields.io/badge/License-Apache--2.0%20%2B%20Commons%20Clause-3b6ea5.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-async-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Vue](https://img.shields.io/badge/Vue-3-42b883.svg?logo=vuedotjs&logoColor=white)](https://vuejs.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-17-4169E1.svg?logo=postgresql&logoColor=white)](https://www.postgresql.org/)

## Screenshots

![Vertriebsauswertung](docs/images/sales-report.png)

![Vertriebsaufträge](docs/images/sales-orders.png)

![Lagerbestand](docs/images/inventory-stock.png)

## Funktionen

| Modul | Beschreibung |
| --- | --- |
| Authentifizierung | JWT-Anmeldung, Tokenaustausch per API-Schlüssel für die Systemintegration, Self-Service für Profil, Avatar und Passwort |
| Systemverwaltung | Benutzer (Anzeigename, Telefon, E-Mail, Avatar), Rollen, Berechtigungen, Audit-Protokoll und Zurücksetzen von Passwörtern durch Administratoren |
| Organisation | Abteilungen und Personaldaten |
| Kunden | Kundendaten, Typ und Stufe, Kreditlimit und Status |
| Produkte | Produkte, Kategorien, Hersteller und Preisänderungsverlauf |
| Lieferanten | Lieferantendaten, Zahlungsbedingungen und Kooperationsstatus |
| Lagerhäuser | Landesweite Lagerdaten und Kühlkettenfähigkeit |
| Einkauf | Bestellungen, Wareneingang (auch Teillieferungen) und Einlagerung |
| Vertrieb | Vertriebsaufträge, automatische Preisberechnung, Bestandsprüfung, Versand und Stornierung |
| Lagerbestand | Bestandsübersicht mit Warnstatus, Eröffnungsbestände und vollständige Nachverfolgung der Warenbewegungen |
| Retouren | Rücksendungen, Rückgabegründe und Einlagerung |
| Forderungen | Zahlungserfassung, Auftragsabgleich und Fälligkeitsanalyse |
| Auswertungen | Tägliche und monatliche Umsätze, Zusammenfassungen nach Kunde, Vertriebsmitarbeiter und Produkt, Auftragsdetails und Dashboard |
| GSP-Konformität | Erstlieferanten-Qualifikationsakten (Prüfung von Nachweisen und gescannten Anhängen), Transaktionssperren, Warnzentrum für ablaufende Nachweise sowie Chargen- und Verfallsverfolgung |
| Mobile App | Android-Client ab Version 8.0 auf WebView-Basis mit Dashboard, Vertriebsaufträgen, Lagerbestand, GSP-Warnungen und Profil |

## Technologie-Stack

| Ebene | Auswahl |
| --- | --- |
| Backend | Python 3.12, FastAPI, SQLAlchemy 2.0 (asynchron), Pydantic v2, JWT (Passwort-Hashing mit PBKDF2-SHA256) |
| Frontend | Vue 3, TypeScript, Vite, Element Plus, Pinia, Vue Router 4, Axios, ECharts |
| Datenbank | PostgreSQL 17 (asyncpg); In-Memory-SQLite (aiosqlite) für Unit-Tests |
| Objektspeicher | MinIO (S3-kompatibel) für GSP-Nachweise und Avatare |
| Tests | pytest + httpx (API), Playwright (E2E und Regressionstests für laufende Umgebungen) |
| Bereitstellung | Docker / Docker Compose, nginx (statische Dateien + `/api`-Proxy mit gleichem Ursprung) |

## Repository-Struktur

```
med-sales/
├── docs/                       # Dokumentation zu API, Datenbank, Berechtigungen, GSP, Auswertungen und Benutzerprofilen
│   └── images/                 # Screenshots für die README-Dateien
├── api/                        # Backend (FastAPI, vollständig asynchron)
│   ├── app/                    # Anwendungscode (core / models / schemas / api/routes / services)
│   ├── tests/                  # API-Tests für das Backend
│   ├── scripts/                # Admin-Initialisierung, Berechtigungskatalog, API-Dokumentation, Report-Rollup
│   ├── Dockerfile              # Backend-Image (python:3.12-slim, ohne Root-Rechte)
│   └── docker-compose.yml      # Compose-Konfiguration nur für das Backend
├── frontend/                   # Frontend (Vue 3 + TypeScript)
│   ├── src/                    # Seiten, Komponenten, Router, Stores und Request-Schicht
│   ├── tests/e2e/              # Isolierte Playwright-Suite (eigenes Backend + Seed-Daten)
│   ├── tests/live/             # Regressionstests für eine laufende Bereitstellung
│   ├── Dockerfile              # Mehrstufiger Build: Node-Build → nginx
│   └── nginx.conf              # Statische Dateien + /api-Reverse-Proxy
├── android/                    # Mobiler Android-Arbeitsbereich (WebView + native Netzwerkbrücke)
├── db/                         # Datenbankinitialisierung und Generierung der Testdaten
│   ├── schema.sql              # DDL für 18 Geschäftstabellen + 7 Views (chinesische Kommentare)
│   ├── mock_params.py          # Datenumfang, Zeitraum und Jahresziele
│   ├── generate_mock_data.py   # Erzeugt Testdaten für viereinhalb Jahre
│   └── run_all.py              # Erstellen → Generieren → Prüfen
├── docker-compose.yml          # Datenbank + Objektspeicher + Backend + Frontend
├── .env.example                # Vorlage für Ports, Passwörter und Zeitzone
├── .github/                    # Issue-Formulare und PR-Vorlage
├── AGENTS.md                   # Entwicklungsrichtlinien des Repositories
└── LICENSE
```

## Schnellstart

```bash
git clone https://github.com/dfxiang/med-sales.git
cd med-sales
```

### Voraussetzungen

- Docker und Docker Compose v2;
- Python 3.12 oder neuer, nur wenn Sie die Testdaten selbst erzeugen möchten.

PostgreSQL 17 und MinIO sind in `docker-compose.yml` enthalten. Die Datenbank muss **UTF-8 mit der
ICU-Sortierfolge `zh-u-co-pinyin`** verwenden (chinesische Zeichen werden nach Pinyin sortiert).
Hinweise zur containerisierten und lokalen Installation finden Sie in der chinesischen Anleitung
[docs/数据库部署与配置.md](docs/数据库部署与配置.md).

### Erster Start

```bash
# 1. Zuerst die Datenbank starten (der Rest folgt später)
docker compose up -d medsales-db

# 2. Schema erstellen, Testdaten für 4,5 Jahre erzeugen und prüfen (ca. 2 Minuten)
cd db
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python run_all.py
cd ..

# 3. Backend, Frontend und Objektspeicher starten
docker compose up -d --build

# 4. Einmalig nach dem ersten Start ein Administratorkonto anlegen
docker compose exec medsales-api python scripts/create_admin.py --username admin --password IHR_PASSWORT

# 5. Report-Rollup-Tabellen befüllen (andernfalls zeigen Auswertungen nur 0 an)
docker compose exec medsales-api python scripts/rebuild_sales_rollup.py
```

Ports, Passwörter und Zeitzone können über die Datei `.env` im Repository-Stamm konfiguriert werden
(`cp .env.example .env`). Wenn der Host-Port 5688 bereits belegt ist, ändern Sie
`MEDSALES_DB_PORT` und verweisen Sie die Datenskripte mit `MEDSALESDB_PORT=<port>` auf denselben Port.

| Einstiegspunkt | URL |
| --- | --- |
| Web-Oberfläche | http://127.0.0.1:8088 |
| API | http://127.0.0.1:8001 |
| Swagger | http://127.0.0.1:8001/docs |
| MinIO-Konsole | http://127.0.0.1:9021 |

### Lokale Entwicklung (ohne Docker)

```bash
# Backend
cd api
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env                                          # Datenbankverbindung anpassen
.venv/bin/python scripts/create_admin.py --username admin --password IHR_PASSWORT
.venv/bin/python scripts/seed_permissions.py --with-roles     # optional: integrierte Rollenvorlagen
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000

# Frontend
cd frontend
npm install
npm run dev                                                   # http://127.0.0.1:5273
```

Der Entwicklungsserver ruft `http://127.0.0.1:8001/api` auf (siehe
`frontend/.env.development`). In Containern wird der relativ zum Frontend aufgelöste Pfad `/api` über
nginx weitergeleitet.

### Konfiguration

Die Backend-Einstellungen stammen aus Umgebungsvariablen oder `api/.env` (siehe
`api/.env.example`). In Containern werden sie durch `docker-compose.yml` bereitgestellt. Die
wichtigsten Einstellungen:

| Variable | Standardwert | Beschreibung |
| --- | --- | --- |
| `DATABASE_URL` | `postgresql+asyncpg://postgres:pass01!@medsales-db:5432/medsalesdb` | Datenbankverbindung (für externe Datenbanken ändern) |
| `TZ` | `Asia/Shanghai` | Container-Zeitzone; darin werden Kennzahlen für „heute“, Forderungsfälligkeiten und Ablaufdaten von Nachweisen berechnet |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | `postgres` / `pass01!` / `medsalesdb` | Zugangsdaten der mitgelieferten Datenbank (**in der Produktion ändern**) |
| `POSTGRES_INITDB_ARGS` | ICU `zh-u-co-pinyin` + UTF8 | Gilt nur, wenn das Daten-Volume leer ist |
| `MEDSALES_DB_PORT` / `MEDSALES_API_PORT` / `MEDSALES_WEB_PORT` | `5688` / `8001` / `8088` | Portzuordnungen auf dem Host |
| `JWT_SECRET` | `medsales-change-me-…` | **In der Produktion unbedingt ändern** |
| `SYS_API_KEYS` | leer | API-Schlüssel für die Systemintegration (durch Kommas getrennt, Rotation wird unterstützt) |
| `CORS_ORIGINS` | `*` | Zulässige Ursprünge; in der Produktion einschränken |
| `MINIO_ROOT_USER` / `MINIO_ROOT_PASSWORD` | `medsales` / `medsales-minio-secret` | Zugangsdaten des Objektspeichers (**in der Produktion ändern**) |
| `GSP_ENFORCE_QUALIFICATION` | `true` | Transaktionen sperren, wenn Nachweise einer registrierten Organisation abgelaufen, ausstehend oder abgelehnt sind |
| `GSP_STRICT_QUALIFICATION` | `false` | Strenger Modus: Organisationen ohne Qualifikationsakte werden ebenfalls gesperrt |
| `GSP_EXPIRY_WARNING_DAYS` | `90` | Vorwarnzeit für ablaufende Nachweise in Tagen |

> Sicherheitscheckliste für die Bereitstellung: [SECURITY.md](SECURITY.md) (chinesisch).

## Datenbank und Testdaten

Voraussetzungen: **PostgreSQL 17**, Kodierung `UTF8` und ICU-Sortierfolge `zh-u-co-pinyin`. Hinweise
zur containerisierten und lokalen Installation, Sortierfolge und Zeitzone, zum Anschluss einer
bestehenden Datenbank sowie zu Sicherung und Wiederherstellung finden Sie in der chinesischen
Anleitung [docs/数据库部署与配置.md](docs/数据库部署与配置.md).

Die ursprüngliche Datenbank enthält 18 Geschäftstabellen und 7 Auswertungs-Views. Das Projekt ergänzt
Systemtabellen für Benutzer und Berechtigungen, Chargen und Nachweise. Diese werden beim Start der API
automatisch angelegt; vorhandene Tabellen bleiben unverändert.

```bash
cd db
.venv/bin/python run_all.py            # Datenbank bei Bedarf erstellen und initialisieren
.venv/bin/python run_all.py --reset    # Löschen und neu erstellen
```

Auswertungen lesen vorab aggregierte Rollup-Tabellen. Nach dem Erzeugen der Daten müssen diese daher
einmal befüllt werden:
`docker compose exec medsales-api python scripts/rebuild_sales_rollup.py`.

## Tests

```bash
# Backend (In-Memory-SQLite, keine echte Datenbank erforderlich)
cd api && .venv/bin/python -m pytest -q

# Frontend-Build
cd frontend && npm run build

# Frontend-E2E (startet ein isoliertes Backend auf Port 8002 und einen Dev-Server auf Port 5273)
cd frontend && npx playwright test

# Regressionstests gegen eine laufende Bereitstellung (8088/8001 müssen laufen)
cd frontend && npx playwright test --config playwright.live.config.ts
```

## Dokumentation

Alle derzeit verfügbaren Detaildokumente sind auf Chinesisch verfasst:

| Dokument | Inhalt |
| --- | --- |
| [docs/API接口文档.md](docs/API接口文档.md) | Automatisch erzeugte chinesische API-Referenz mit Parametern und Beispielen |
| [docs/数据库部署与配置.md](docs/数据库部署与配置.md) | PostgreSQL-17-Bereitstellung, UTF-8 + chinesische Pinyin-Sortierfolge, Zeitzone, Sicherung/Wiederherstellung |
| [docs/GSP合规闭环.md](docs/GSP合规闭环.md) | GSP-Prozess: Qualifikationsprüfung, Transaktionssperren, Ablaufwarnungen und Archivierung erneuerter Nachweise |
| [docs/权限控制说明.md](docs/权限控制说明.md) | Berechtigungsmodell, Namenskonventionen und Erweiterungsanleitung |
| [docs/销售报表汇总表.md](docs/销售报表汇总表.md) | Rollup-Tabellen, Wartungsreihenfolge, Befüllung und Abgleich |
| [docs/用户资料扩展设计.md](docs/用户资料扩展设计.md) | Profilfelder, Selbstverwaltung des Passworts, Zurücksetzen durch Administratoren und Sicherheit von Avataren |
| [docs/许可与商用说明.md](docs/许可与商用说明.md) | Erlaubte Nutzung und Fälle, die eine kommerzielle Lizenz erfordern (chinesisch) |
| [db/README.md](db/README.md) | Skripte für die Demodatenbank, Verbindungsparameter und Datenumfang |
| [api/README.md](api/README.md) · [frontend/README.md](frontend/README.md) | Technische Details zu Backend und Frontend |

## Mitwirken

Issues und Pull Requests sind willkommen. Informationen zu Umgebung, Ablauf und Codestandards finden
Sie in [CONTRIBUTING.md](CONTRIBUTING.md) (chinesisch). Sicherheitsprobleme melden Sie bitte
vertraulich über den in [SECURITY.md](SECURITY.md) beschriebenen Weg.

## Lizenz und kommerzielle Nutzung

Das Projekt steht unter der **Apache License 2.0 mit der Commons-Clause-Bedingung v1.0**. Der
vollständige Text befindet sich in [LICENSE](LICENSE).

| Sie dürfen | Sie dürfen nicht |
| --- | --- |
| Das Projekt kommerziell für Ihr eigenes Unternehmen einsetzen, ändern und darauf aufbauen (Ihre Änderungen dürfen geschlossen bleiben) | Die Software (oder im Wesentlichen ihre Funktionalität) in ein Produkt oder einen Dienst einbetten und Dritten dafür Gebühren berechnen |
| Das Projekt kostenlos kopieren und weitergeben (Urheberrechts- und Lizenzhinweise müssen erhalten bleiben) | Die Software als kostenpflichtigen Hostingdienst (SaaS), kostenpflichtige Beratung oder kostenpflichtigen Support anbieten |
| Das Projekt studieren und für Schulungen verwenden | Urheberrechts- oder Lizenzhinweise entfernen oder verändern |

> Hinweis: Aufgrund der Bedingung „nicht verkaufen“ ist dieses Projekt **source-available, aber kein
> von der OSI zertifiziertes Open Source** (GitHub zeigt die Lizenz als „Other“ an). Eine vollständige
> Erläuterung finden Sie in [docs/许可与商用说明.md](docs/许可与商用说明.md).

Kommerzielle Lizenzen, kundenspezifische Entwicklung und Support (der Urheberrechtsinhaber kann
gesonderte Bedingungen gewähren): `4198166@qq.com` · WeChat `4198166` · Telefon `+86 185 7281 7101`.

## Haftungsausschluss

- Alle im Repository enthaltenen Unternehmen und Geschäftsdaten (einschließlich der fiktiven
  „华康医药销售有限公司“, ihrer Kunden, Preise und Belege) werden **von Skripten erzeugt** und stehen
  in keiner Verbindung zu realen Organisationen. Verwenden Sie sie nicht für geschäftliche
  Entscheidungen.
- Dieses Projekt ist eine allgemeine Vertriebsmanagementsoftware. Es ist kein Medizinprodukt und
  enthält keine medizinischen Empfehlungen oder Verschreibungshinweise.
- Die GSP-Funktionen sind Hilfsmittel zur Strukturierung von Konformitätsprozessen und **keine
  Konformitätsgarantie**. Der tatsächliche Betrieb muss lokale Vorschriften einhalten und von
  qualifizierten Mitarbeitern geprüft werden.
- Die Software wird „wie besehen“ ohne ausdrückliche oder stillschweigende Gewährleistung
  bereitgestellt. Führen Sie vor dem Produktionseinsatz eine Sicherheitsprüfung durch und erstellen
  Sie Datensicherungen.

## Projekt unterstützen

Wenn Ihnen dieses Projekt hilft, können Sie mir gern einen Kaffee spendieren. Spenden sind völlig
freiwillig und haben keinen Einfluss auf Ihre Nutzungsrechte.

<table>
  <tr>
    <td align="center">
      <img src="weixin.jpg" alt="WeChat-QR-Code des Autors" width="260"><br>
      <sub>QR-Code scannen und über WeChat austauschen</sub>
    </td>
    <td align="center">
      <img src="donation.jpg" alt="Spenden-QR-Code für das Projekt" width="260"><br>
      <sub>Einen Kaffee spendieren und die laufende Pflege unterstützen</sub>
    </td>
  </tr>
</table>
