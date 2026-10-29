---
name: onyx
description: "Convierte el sitio web publico de cualquier empresa en un corpus Markdown auditable y listo para RAG, con arquitectura Medallon en disco (Bronze = HTML crudo, Silver = texto limpio, Gold = Markdown con frontmatter YAML). Descubre URLs por sitemap con crawl acotado de respaldo, respeta robots.txt y Crawl-delay, registra procedencia (url, fecha, estado, sha256, etag) en un JSONL append-only y refresca de forma incremental sin reescribir lo que no cambio. Usala cuando haya que crear un corpus propio de una empresa, ingerir o raspar su sitio, convertir HTML en Markdown para embeddings o chunking, limpiar boilerplate (menus, cookies, footer, scripts), medir tokens de un corpus, refrescar contenido sin volver a descargar todo, o preparar insumos para un RAG. Use when turning a company website into a RAG corpus, scraping a site politely, building a Bronze/Silver/Gold pipeline, converting HTML to Markdown with YAML frontmatter, cleaning boilerplate, or refreshing a corpus incrementally."
license: MIT
compatibility: Requiere Python 3.13+ y uv. Sin navegador headless; no ejecuta JavaScript.
metadata:
  author: diegoteuta
  version: "1.0"
  homepage: https://github.com/diegoteuta/onyx
---

# Onyx

Onyx separa **captura** (frágil, lenta, depende del sitio) de **procesamiento**
(determinista, repetible). Tres capas en disco, cada una reconstruible desde la anterior.

| Capa | Carpeta | Qué contiene |
|------|---------|--------------|
| 🥉 Bronze | `data/raw/<site>/` | HTML tal cual + `capture.jsonl` (url, fecha, estado, sha256, etag). Inmutable. |
| 🥈 Silver | `data/processed/<site>/` | Texto sin menús, cookies, footer ni scripts. Deduplicado. |
| 🥇 Gold | `data/gold/<site>/` | Markdown + frontmatter YAML (fuente, título, sección, idioma, tokens). |

## Cuándo usar esta skill

- Hay que construir un corpus propio de una empresa.
- Hay que convertir HTML en Markdown limpio para chunking y embeddings.
- Hay que refrescar un corpus sin volver a descargar todo el sitio.
- Hay que auditar de dónde salió cada fragmento (procedencia y atribución).

## Cuándo NO usarla

- El sitio requiere login, es una intranet o tiene datos personales → **no se ingesta**.
- La página es una SPA que no renderiza sin JavaScript → Onyx no ejecuta JS.
- Ya existe una API oficial o un dataset autorizado → usá esa fuente.

## Requisitos

```bash
git clone git@github.com:diegoteuta/onyx.git
cd onyx
uv sync
```

Si el repositorio ya está abierto en el proyecto actual, saltear el bloque anterior.

## Flujo de trabajo

### 1. Descubrir sin descargar

```bash
uv run onyx discover --site <perfil> --limit 20
```

Muestra qué URLs se ingerirían. Sirve para validar `include_patterns` /
`exclude_patterns` **antes** de gastar ancho de banda.

### 2. Ingerir

```bash
uv run onyx ingest --site <perfil>
```

Muestra una barra de progreso por capa (`bronze`, `silver`, `gold`) en **stderr**; el
resumen final sale por stdout. En CI o en scripts, agregar `--quiet` para silenciar la
barra y quedarse solo con la línea parseable.

Corre Bronze → Silver → Gold y reporta:

```text
[hv] descubiertas=3 guardadas=3 omitidas=0 silver=3 gold=3 tokens=536
```

### 3. Refrescar de forma incremental

```bash
uv run onyx ingest --site <perfil> --refresh
```

Usa `ETag` / `Last-Modified` y compara `sha256`: si el contenido no cambió, no reescribe el
crudo. El manifest queda igual con una entrada nueva (`status: 304` o `note: sin cambios`).

### 4. Revisar el estado

```bash
uv run onyx report --site <perfil>
```

### 5. Recalcular sin volver a descargar

```bash
uv run onyx rebuild --site <perfil>
```

Uso típico: cambiaste `content_selectors` o `drop_selectors` y no querés esperar otra
captura completa. Recalcula Silver y Gold desde el Bronze y descarta las páginas que
quedaron sin contenido.

## Agregar una empresa nueva

Crear `sites/<nombre>.toml`. Es la **única** pieza específica del sitio; nada se hardcodea
en `src/`.

```toml
name = "acme"
base_url = "https://www.acme.com"
lang = "es"
rate_limit_seconds = 1.0
max_pages = 200
sitemaps = ["/sitemap.xml"]
sitemap_exclude = ["attachment-sitemap", "category-sitemap"]
exclude_patterns = ["/wp-content/", "/feed/", "/tag/"]

[extract]
content_selectors = ["main", "article"]
drop_selectors = ["nav", "header", "footer", "script", "style", ".cookie-notice"]
```

Cómo elegir los selectores:

1. Abrí una página representativa y buscá el contenedor que envuelve **solo** el contenido.
2. Poné ese selector primero en `content_selectors`; los genéricos (`main`, `article`)
   quedan como respaldo.
3. En `drop_selectors`, todo lo que se repite en todas las páginas: menú, footer, cookies,
   newsletter, botones de compartir.

## Errores frecuentes y cómo resolverlos

| Síntoma | Causa | Solución |
|---------|-------|----------|
| `0 URLs` en `discover` | Sitemap en otra ruta o `include_patterns` demasiado estrictos | Probar sin `include_patterns`; revisar `/sitemap_index.xml` y `/robots.txt` |
| Texto con menús y pies de página | Faltan selectores en `drop_selectors` | Inspeccionar el DOM y agregar los contenedores repetidos |
| Todo el texto en un solo bloque | El sitio usa un page builder (WPBakery, Elementor) con divs anidados | Elegir un contenedor más interno en `content_selectors` |
| `silver=0` con `guardadas>0` | Contenido renderizado por JavaScript | Fuera de alcance: se necesita navegador headless |
| Faltan fichas de producto | `max_pages` cortó la lista antes de llegar a su sitemap | Subir `max_pages` y revisar `sitemap_exclude`: un sitemap excluido puede tener el catálogo |
| Sigue apareciendo el menú o el footer | El selector de `drop_selectors` apunta a una clase y el bloque es un **id** (o al revés) | Verificar en el DOM: `soup.select("#footer-outer")` vs `soup.select(".footer-outer")`. Un drop equivocado no falla, no hace nada |
| `omitido: robots.txt` | `Disallow` en `robots.txt` | Respetarlo. No usar `--ignore-robots` contra terceros |
| `tokens` estimados | `tiktoken` no pudo descargar el encoding | Normal en modo offline; el fallback estima por caracteres |

## Reglas duras (no negociables)

1. **Solo contenido público.** Nada detrás de login, formularios ni áreas privadas.
2. **Cero datos personales.** Sin hojas de vida, contactos de personas ni envíos de formularios.
3. **`robots.txt` manda.** Se respeta por defecto, incluido `Crawl-delay`.
4. **Cortesía.** Rate limit por sitio y User-Agent identificable.
5. **Atribución.** Todo documento Gold lleva `source:` con la URL original.
6. **Términos del sitio.** Si prohíben la extracción, no se ingesta.

`--ignore-robots` existe únicamente para servidores propios o de prueba.

## Contrato de salida (Gold)

Un archivo `.md` por página, con frontmatter parseable:

```markdown
---
source: https://www.acme.com/productos/
site: acme
title: Productos
section: productos
lang: es
captured_at: '2026-10-29T01:16:13+00:00'
content_hash: beab246a...
tokens: 134
---

# Productos

## Presentaciones

- Bulto de 50 kg
```

- Los **encabezados** son fronteras naturales de chunk.
- Las **tablas y listas** se conservan.
- Las **imágenes** se descartan (siguen disponibles en Bronze).
- `content_hash` permite detectar cambios sin volver a leer el HTML.

## Verificar antes de dar por terminado

```bash
make check   # lint + formato + tipos + pruebas
uv run onyx report --site <perfil>
```

Checklist:

- [ ] El perfil existe en `sites/` y `discover` devuelve URLs razonables.
- [ ] `ingest` produce `silver > 0` y `gold > 0`.
- [ ] Un `.md` de muestra tiene frontmatter completo y texto legible.
- [ ] `grep -r "http" src/` no devuelve dominios de empresas (nada hardcodeado).
- [ ] `CONSTITUTION.md` actualizado si cambió el comportamiento.
