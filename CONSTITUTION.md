# CONSTITUTION — Onyx

> **Verdad central del proyecto.** Este documento define el propósito, el stack, la
> estructura, las convenciones y el flujo de trabajo de `Onyx`. Si algo aquí
> contradice al código, el código manda **y este archivo se actualiza**.

> ⚠️ **Directiva de mantenimiento:** cada vez que se realicen cambios significativos
> (nuevas funcionalidades, cambios arquitectónicos, adición de clases/módulos o ajustes
> de tecnologías), **se debe actualizar este archivo en el mismo commit** para mantener
> la verdad central del proyecto bien documentada.

---

## 0. Identidad del proyecto

| Campo | Valor |
|-------|-------|
| **Nombre** | Onyx |
| **Descripción** | Turn any company website into an auditable RAG corpus through a Bronze/Silver/Gold pipeline. |
| **Repositorio** | https://github.com/diegoteuta/onyx |
| **Autoría** | diegoteuta — diegofernandoteuta@gmail.com |
| **Licencia** | MIT |
| **Rama principal** | `main` |
| **Estado** | MVP funcional 🚧 |

## 1. Propósito y no-propósito

### Propósito

Construir, a partir del sitio web público de **cualquier** empresa, un corpus de texto
propio, auditable y reproducible, listo para alimentar un RAG. Onyx separa la captura
(frágil, lenta, dependiente del sitio) del procesamiento (determinista y repetible).

### No-propósito

- **No** es un buscador ni un motor de RAG: no genera embeddings ni responde preguntas.
  Solo produce el insumo (capa Gold).
- **No** es un crawler masivo ni un motor de scraping a escala. Está pensado para el
  sitio de una empresa, con cortesía y trazabilidad.
- **No** captura datos personales, formularios, áreas privadas ni contenido detrás de login.

## 2. Alcance

### Dentro del alcance

- Descubrimiento de URLs por `sitemap.xml` (incluye índices) y crawl acotado desde la home
  como respaldo.
- Captura del HTML crudo con registro de procedencia (`url`, fecha, estado, `sha256`, `etag`).
- Limpieza de boilerplate (menús, cookies, footer, scripts) y normalización de texto.
- Enriquecimiento a Markdown con frontmatter YAML (fuente, título, sección, idioma, tokens).
- Captura incremental: no se reescribe el crudo si el hash no cambió.
- Perfiles de sitio en TOML: agregar una empresa nueva es agregar un archivo, no tocar código.

### Fuera del alcance (por ahora)

- Extracción de datos estructurados de producto (precio, SKU, stock).
- Ejecución de JavaScript / navegador headless para sitios SPA.
- OCR de PDFs e imágenes.
- Chunking y embeddings (pertenece al módulo de RAG, no a Onyx).

## 3. Stack técnico

| Categoría | Tecnología |
|-----------|------------|
| **Lenguaje** | Python 3.13+ |
| **Gestor de paquetes y entorno** | [`uv`](https://docs.astral.sh/uv/) |
| **Build backend** | `uv_build` (src-layout) |
| **Paquete Python** | `onyx` |
| **HTTP** | [`httpx`](https://www.python-httpx.org/) |
| **Parseo HTML** | [`beautifulsoup4`](https://www.crummy.com/software/BeautifulSoup/) + `lxml` |
| **HTML → Markdown** | [`markdownify`](https://github.com/matthewwithanm/python-markdownify) |
| **Frontmatter** | [`pyyaml`](https://pyyaml.org/) |
| **Conteo de tokens** | [`tiktoken`](https://github.com/openai/tiktoken) (`cl100k_base`) |
| **Configuración** | `tomllib` (biblioteca estándar) |
| **Tipado estático** | [`ty`](https://github.com/astral-sh/ty) |
| **Testing** | [`pytest`](https://docs.pytest.org/) |
| **Linting / Formato** | [Ruff](https://docs.astral.sh/ruff/) |
| **Pre-commit** | [pre-commit](https://pre-commit.com) |
| **CI/CD** | [GitHub Actions](.github/workflows/ci.yml) |
| **Dependencias automáticas** | [Dependabot](.github/dependabot.yml) |

> ⚠️ **Regla dura:** toda gestión de dependencias y entornos pasa por `uv`. Está
> **prohibido** `pip` y `requirements.txt`.

## 4. Estructura del repositorio

```text
onyx/
├── src/onyx/                # código del paquete (src-layout)
│   ├── cli.py               # interfaz de línea de comandos
│   ├── config.py            # SiteProfile + carga de TOML
│   ├── discovery.py         # sitemap -> URLs, crawl de respaldo
│   ├── fetch.py             # HTTP cortés (robots, rate limit, reintentos)
│   ├── bronze.py            # capa 1: HTML crudo + manifest
│   ├── silver.py            # capa 2: limpieza de boilerplate
│   ├── gold.py              # capa 3: Markdown + frontmatter
│   ├── layout.py            # carpetas del corpus + manifest JSONL
│   ├── models.py            # CaptureRecord, Document
│   └── pipeline.py          # orquestación de las tres capas
├── sites/                   # perfiles de sitio (hv.toml, ...)
├── skills/onyx/SKILL.md     # la skill publicable en skills.sh
├── tests/                   # pruebas (pytest) + fixtures HTML
├── data/                    # corpus generado (NO versionado)
│   ├── raw/<site>/          # Bronze
│   ├── processed/<site>/    # Silver
│   └── gold/<site>/         # Gold
├── docs/                    # documentación, ADRs e investigación
├── .github/                 # gobernanza (PR/issue templates, CI, Dependabot, labels)
├── .opencode/rules/         # reglas para agentes (tgrep)
├── AGENTS.md                # contexto para agentes LLM
├── CONSTITUTION.md          # este archivo — verdad central
├── README.md                # puerta de entrada pública
├── CONTRIBUTING.md          # guía de contribución
├── CODE_OF_CONDUCT.md       # código de conducta
├── Makefile                 # automatización de tareas
├── pyproject.toml           # metadatos y dependencias (uv)
├── uv.lock                  # lockfile determinista (versionado)
├── .python-version          # versión de Python fijada
└── .pre-commit-config.yaml  # hooks de calidad
```

## 5. Convenciones de código

- **Estilo:** [PEP 8](https://peps.python.org/pep-0008/) y [PEP 257](https://peps.python.org/pep-0257/),
  impuesto por **Ruff** (`line-length = 100`, comillas dobles).
- **Tipado:** anotaciones en funciones y firmas públicas.
- **Nomenclatura:** `snake_case` (funciones/variables), `PascalCase` (clases),
  `UPPER_CASE` (constantes).
- **Docstrings:** en módulos, clases y funciones públicas.
- **Pruebas:** `pytest` con el patrón **AAA** (*Arrange · Act · Assert*).
- **Idioma:** UI, comentarios y commits en español; identificadores de código en inglés.
- **Reglas propias:**
  - **Ningún dominio hardcodeado en `src/`.** Todo lo específico de un sitio vive en
    `sites/<nombre>.toml`. Si aparece una URL de empresa en el código, es un bug.
  - **Bronze es inmutable.** `data/raw/<site>/*.html` nunca se edita a mano; el manifest
    `capture.jsonl` es *append-only*.
  - **Nada de red en las pruebas.** Los tests usan fixtures locales; el acceso a red se
    prueba solo con corridas manuales explícitas.
  - **Las tres capas se pueden reconstruir.** Silver y Gold deben poder regenerarse desde
    Bronze sin volver a descargar el sitio.

## 6. Calidad y automatización

| Herramienta | Rol | Comando |
|-------------|-----|---------|
| `uv` | Entornos y dependencias | `uv sync` |
| Ruff | Lint + formato | `make lint` / `make format` |
| `ty` | Verificación de tipos | `make typecheck` |
| `pytest` | Pruebas | `make test` |
| `pre-commit` | Hooks antes de cada commit | `make pre-commit` |
| GitHub Actions | CI (pre-commit + pruebas) | `.github/workflows/ci.yml` |

- Ningún commit se salta los hooks (`--no-verify` está prohibido salvo causa justificada y documentada).
- La **CI debe estar en verde** antes de fusionar un Pull Request.
- Toda dependencia nueva entra con `uv add` / `uv add --dev` (nunca editando `uv.lock` a mano).

## 7. Repositorio y Git

- **Remoto (SSH):** `git@github.com:diegoteuta/onyx.git`
- **Rama principal:** `main`
- **Estrategia de ramas:** `feat/...`, `fix/...`, `docs/...`, `refactor/...`, `test/...`, `chore/...`; integración vía Pull Request.
- **Commits:** [Conventional Commits](https://www.conventionalcommits.org/) —
  `feat:`, `fix:`, `docs:`, `refactor:`, `style:`, `test:`, `chore:`.
- **Identidad git:** se resuelve con la configuración global de la máquina
  (`user.name = diegoteuta`). No hay `includeIf` configurado para este proyecto.

## 8. Flujo diario (commit + push)

```bash
# 1. Ver cambios
git status

# 2. Verificación completa (lint + formato + tipos + pruebas)
make check

# 3. Agregar y commitear (los hooks se ejecutan solos)
git add -A
git commit -m "tipo: mensaje descriptivo"

# 4. Subir a GitHub
git push
```

## 8-bis. Régimen de datos y ética

Estas reglas son **duras**: no son recomendaciones.

1. **Solo contenido público.** Nada detrás de login, formularios, intranets ni áreas privadas.
2. **Cero datos personales.** Quedan excluidas hojas de vida, bases de contacto, correos de
   personas naturales y cualquier formulario enviado.
3. **`robots.txt` manda.** `PoliteFetcher` lo consulta y respeta por defecto. La bandera
   `--ignore-robots` existe solo para servidores propios o de prueba, y su uso contra
   terceros es una violación del proyecto.
4. **Cortesía activa.** Rate limit configurable por sitio (por defecto 1 req/s, se eleva si
   `robots.txt` declara `Crawl-delay`) y User-Agent identificable con URL del proyecto.
5. **Atribución.** Cada documento Gold lleva `source:` con la URL original.
6. **Términos del sitio.** Si el sitio prohíbe la extracción en sus términos de uso, no se
   ingesta: se documenta y se busca una fuente autorizada.

## 9. Historial de decisiones técnicas

| Fecha | Decisión | Motivo |
|-------|----------|--------|
| 2026-10-28 | Adoptar `uv` como gestor único de entornos y dependencias | Reproducibilidad; prohibido `pip`/`requirements.txt` |
| 2026-10-28 | Adoptar Ruff (lint + formato) y pre-commit | Calidad automatizada antes de cada commit |
| 2026-10-28 | Adoptar Conventional Commits | Historial legible y automatizable |
| 2026-10-28 | Adoptar licencia MIT y `CONSTITUTION.md` como fuente única de verdad | Claridad legal y operativa |
| 2026-10-28 | Arquitectura **Medallion** (Bronze/Silver/Gold en disco) | Separa la captura frágil del procesamiento reproducible |
| 2026-10-28 | Perfiles de sitio en TOML en vez de código | Agregar una empresa no requiere tocar el paquete |
| 2026-10-28 | `robots.txt` respetado por defecto con `urllib.robotparser` | Ética y legalidad; además respeta `Crawl-delay` |
| 2026-10-28 | Captura incremental por `ETag`/`Last-Modified` + `sha256` | Refrescar sin reescribir crudo ni gastar ancho de banda |
| 2026-10-28 | Manifest de procedencia en JSONL *append-only* | Auditoría simple, diffs legibles, sin dependencias |
| 2026-10-28 | Gold en Markdown con frontmatter YAML (no texto plano) | Los encabezados son fronteras de chunk; menos tokens que HTML; metadatos filtrables |
| 2026-10-28 | `tiktoken` (`cl100k_base`) para contar tokens, con fallback por caracteres | Métrica real de coste; el fallback permite operar offline |
| 2026-10-28 | Imágenes descartadas en Gold | Aportan ruido y tokens; siguen disponibles en Bronze |
| 2026-10-28 | Makefile portable (Python en vez de `grep`/`awk`/`rm`/`find`) | El template original fallaba en Windows (`make help` → error 255) |

## 10. Notas y tareas pendientes

- [x] Implementar las tres capas y la CLI.
- [x] Perfil de sitio para `hv.com.co`.
- [ ] Agregar pruebas de `bronze.capture` con `httpx.MockTransport` (sin red).
- [ ] Publicar la skill en `skills.sh` y validar con `npx skills add`.
- [ ] Chunking + embeddings en el módulo de RAG (fuera del alcance de Onyx).
- [ ] Soportar sitios SPA con navegador headless (evaluar `playwright`).
- [ ] Comando `onyx diff` para ver qué cambió entre dos capturas.

## 11. Configuración local (no trackear)

> Configuración específica de la máquina local. **NO incluir en commits.**

La identidad de este repositorio sale de la configuración global de git:

```ini
[user]
    name = diegoteuta
    email = diegofernandoteuta@gmail.com
```

No hay `includeIf` configurado para este proyecto. Si más adelante se quiere identidad
automática por carpeta, la guía está en el skill `jan-project-standard` →
`references/git-identity.md` (script `setup_git_identity.py`, respalda `~/.gitconfig`).
