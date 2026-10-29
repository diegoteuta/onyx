<div align="center">

# Onyx

**Turn any company website into an auditable RAG corpus through a Bronze/Silver/Gold pipeline.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.13+](https://img.shields.io/badge/python-3.13%2B-blue.svg)](https://www.python.org/downloads/)
[![CI](https://github.com/diegoteuta/onyx/actions/workflows/ci.yml/badge.svg)](https://github.com/diegoteuta/onyx/actions/workflows/ci.yml)
[![Managed with uv](https://img.shields.io/badge/managed%20with-uv-de5fe9.svg)](https://github.com/astral-sh/uv)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=precommit&logoColor=white)](./.pre-commit-config.yaml)
[![Conventional Commits](https://img.shields.io/badge/Conventional%20Commits-1.0.0-fe5196.svg)](https://conventionalcommits.org)

</div>

---

## 📖 Descripción general

Casi nunca hay una API ni un dataset: hay un sitio web. **Onyx** lo convierte en un corpus
propio, auditable y reproducible, separando la captura (frágil y cara) del procesamiento
(determinista y repetible).

```text
        sitio web
            │
            ▼
┌───────────────────────┐   data/raw/<site>/        HTML tal cual + capture.jsonl
│  🥉 Bronze (crudo)    │   inmutable, nunca editado a mano
└───────────┬───────────┘
            ▼
┌───────────────────────┐   data/processed/<site>/  texto sin menús, cookies,
│  🥈 Silver (limpio)   │   footer ni scripts; deduplicado y normalizado
└───────────┬───────────┘
            ▼
┌───────────────────────┐   data/gold/<site>/       Markdown + frontmatter YAML
│  🥇 Gold (enriquecido)│   fuente, título, sección, idioma, tokens
└───────────────────────┘
            │
            ▼
          RAG
```

**¿Por qué Markdown y no texto plano en Gold?** Porque los encabezados son fronteras
naturales de *chunk*, las tablas y listas sobreviven, se gastan muchos menos tokens que
con HTML y los metadatos permiten filtrar («solo la sección de productos»), citar la
fuente y refrescar únicamente lo que cambió.

> 📘 La verdad técnica central —stack, decisiones, convenciones y flujo— vive en
> [`CONSTITUTION.md`](./CONSTITUTION.md). Es de lectura obligatoria antes de contribuir.

## 📑 Tabla de contenidos

- [Descripción general](#-descripción-general)
- [Estado del proyecto](#-estado-del-proyecto)
- [Stack tecnológico](#️-stack-tecnológico)
- [Instalación](#-instalación)
- [Uso](#-uso)
- [Agregar una empresa nueva](#-agregar-una-empresa-nueva)
- [Ética, límites y legalidad](#️-ética-límites-y-legalidad)
- [Estructura del repositorio](#-estructura-del-repositorio)
- [Calidad y automatización](#-calidad-y-automatización)
- [Contribución](#-contribución)
- [Licencia](#-licencia)

## 🚧 Estado del proyecto

| Área | Estado |
|------|:------:|
| Descubrimiento (sitemap + crawl de respaldo) | ✅ |
| Bronze / Silver / Gold | ✅ |
| Captura incremental (`ETag` + `sha256`) | ✅ |
| Perfiles de sitio en TOML | ✅ |
| Perfil de ejemplo (`sites/hv.toml`) | ✅ |
| Skill publicable en skills.sh | ✅ |
| Extracción de datos de producto (precio, SKU) | ⏳ |
| Sitios SPA (navegador headless) | ⏳ |

## 🛠️ Stack tecnológico

| Categoría | Tecnología |
|-----------|------------|
| **Lenguaje** | Python 3.13+ |
| **Gestor de paquetes** | [`uv`](https://docs.astral.sh/uv/) |
| **Build backend** | `uv_build` (src-layout) |
| **HTTP** | [`httpx`](https://www.python-httpx.org/) |
| **Parseo HTML** | [`beautifulsoup4`](https://www.crummy.com/software/BeautifulSoup/) + `lxml` |
| **HTML → Markdown** | [`markdownify`](https://github.com/matthewwithanm/python-markdownify) |
| **Conteo de tokens** | [`tiktoken`](https://github.com/openai/tiktoken) |
| **Tipado estático** | [`ty`](https://github.com/astral-sh/ty) |
| **Testing** | [`pytest`](https://docs.pytest.org/) |
| **Linting / Formato** | [Ruff](https://docs.astral.sh/ruff/) |
| **CI/CD** | [GitHub Actions](.github/workflows/ci.yml) |

## 🚀 Instalación

### Requisitos previos

- [Python 3.13+](https://www.python.org/downloads/)
- [`uv`](https://docs.astral.sh/uv/getting-started/installation/)
- [Git](https://git-scm.com/)

### Pasos

```bash
git clone git@github.com:diegoteuta/onyx.git
cd onyx

uv sync
uv run pre-commit install   # equivalente a: make dev
make check                  # lint + formato + tipos + pruebas
```

> ⚠️ **Regla del proyecto:** toda gestión de dependencias y entornos pasa por `uv`.
> Está **prohibido** `pip` y `requirements.txt`.

## 📦 Uso

```bash
# 1. Ver qué URLs se ingerirían (no descarga nada)
uv run onyx discover --site hv

# 2. Correr el pipeline completo
uv run onyx ingest --site hv

# 3. Refrescar sin reescribir lo que no cambió
uv run onyx ingest --site hv --refresh

# 4. Recalcular Silver y Gold sin volver a descargar (tras cambiar selectores)
uv run onyx rebuild --site hv

# 5. Estado del corpus
uv run onyx report --site hv
```

Cada capa dibuja su barra de progreso en **stderr** (`[hv:bronze] [####----] 84/400 (21%)`),
así que podés redirigir la salida sin romper nada. Para CI o scripting, `--quiet` deja solo
el resumen de stdout.

Equivalente con `make`:

```bash
make discover SITE=hv
make ingest SITE=hv
make report SITE=hv
```

Salida de ejemplo:

```text
[hv] descubiertas=442 guardadas=2 omitidas=0 silver=2/442 gold=2/442 tokens=205248
```

`silver` y `gold` se leen como **escritas / total**: en una corrida sin cambios verás
`silver=0/442`, porque las capas se saltean lo que no cambió (el crudo por `sha256`,
el Markdown por `content_hash` + versión del renderer). `descartadas` cuenta las páginas
que quedaron sin contenido útil: se les borra el Silver y el Gold para que el corpus no
arrastre documentos obsoletos.

### Un documento Gold

```markdown
---
source: https://www.hv.com.co/sala-de-prensa/noticias/...
site: hv
title: Harinera del Valle destacada en el Valle del Cauca
section: sala-de-prensa
lang: es
captured_at: '2026-10-29T01:16:13+00:00'
content_hash: beab246a...
tokens: 134
---

# Harinera del Valle destacada en el Valle del Cauca

Harinera del Valle fue destacada por el Diario La República...
```

## 🏭 Agregar una empresa nueva

Nada de tocar código: se agrega un archivo en `sites/`.

```toml
name = "acme"
base_url = "https://www.acme.com"
lang = "es"
rate_limit_seconds = 1.0
max_pages = 200
sitemaps = ["/sitemap.xml"]
sitemap_exclude = ["attachment-sitemap", "category-sitemap"]
exclude_patterns = ["/wp-content/", "/feed/"]

[extract]
content_selectors = ["main", "article"]
drop_selectors = ["nav", "header", "footer", "script", "style"]
```

```bash
uv run onyx discover --site acme   # valida el perfil sin descargar
uv run onyx ingest --site acme
```

> 💡 Si el sitio publica un `sitemap_index.xml` con sitemaps de adjuntos, categorías o
> taxonomías, listalos en `sitemap_exclude`: son ruido y consumen turnos de rate limit.
> Cuidado con excluir sitemaps que sí traen productos (en HV, `portfolio-sitemap` tenía
> las 40 fichas de `/productos/`).

## ⚖️ Ética, límites y legalidad

Reglas **duras** del proyecto (detalle en [`CONSTITUTION.md`](./CONSTITUTION.md) §8-bis):

1. **Solo contenido público.** Nada detrás de login, formularios ni áreas privadas.
2. **Cero datos personales.** Sin hojas de vida, contactos de personas naturales ni
   envíos de formularios.
3. **`robots.txt` manda.** Se consulta y se respeta por defecto; también se honra
   `Crawl-delay`. `--ignore-robots` es solo para servidores propios.
4. **Cortesía activa.** Rate limit por sitio y User-Agent identificable.
5. **Atribución.** Cada documento Gold lleva `source:` con la URL original.
6. **Términos del sitio.** Si el sitio prohíbe la extracción, no se ingesta.

## 🗂️ Estructura del repositorio

```text
onyx/
├── src/onyx/                # paquete: cli, discovery, fetch, bronze, silver, gold
├── sites/                   # perfiles de sitio (hv.toml, ...)
├── skills/onyx/SKILL.md     # la skill publicable en skills.sh
├── tests/                   # pytest + fixtures HTML
├── data/                    # corpus generado (NO versionado)
│   ├── raw/                 # Bronze
│   ├── processed/           # Silver
│   └── gold/                # Gold
├── docs/                    # documentación y ADRs
├── .github/                 # gobernanza (PR, issues, CI, Dependabot, labels)
├── CONSTITUTION.md          # verdad central del proyecto
├── AGENTS.md                # contexto para agentes LLM
├── Makefile                 # automatización de tareas
├── pyproject.toml           # metadatos y dependencias (uv)
└── uv.lock                  # lockfile determinista
```

## ✅ Calidad y automatización

| Comando | Descripción |
|---------|-------------|
| `make help` | Lista los objetivos disponibles. |
| `make dev` | `uv sync` + instala los hooks de pre-commit. |
| `make check` | Verificación completa (lint + formato + tipos + pruebas). |
| `make lint` / `make format` | Ruff. |
| `make typecheck` | `ty check`. |
| `make test` | `pytest`. |
| `make build` | Construye el paquete (sdist + wheel). |

## 🤝 Contribución

> 📘 La guía completa está en [`CONTRIBUTING.md`](./CONTRIBUTING.md). Resumen:

1. Crea una rama: `git checkout -b feat/nombre-corto`.
2. Desarrolla y verifica: `make check`.
3. Commitea con [Conventional Commits](https://www.conventionalcommits.org/).
4. Abre un Pull Request con la plantilla oficial.
5. Mantén `CONSTITUTION.md` actualizado ante cambios arquitectónicos o tecnológicos.

## 📄 Licencia

Distribuido bajo la [Licencia MIT](./LICENSE).

---

<div align="center">
<sub>Hecho con ❤️ por diegoteuta</sub>
</div>
