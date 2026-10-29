"""Interfaz de linea de comandos de Onyx."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from onyx.config import ConfigError, SiteProfile, find_profile, load_profile
from onyx.layout import Corpus
from onyx.pipeline import ingest, list_urls, rebuild, stats

DEFAULT_DATA_DIR = Path("data")
DEFAULT_PROFILE_DIR = Path("sites")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="onyx",
        description=(
            "De un sitio web corporativo a un corpus Markdown auditable (Bronze/Silver/Gold)."
        ),
    )
    parser.add_argument(
        "--data-dir", type=Path, default=DEFAULT_DATA_DIR, help="carpeta del corpus"
    )
    parser.add_argument(
        "--profiles", type=Path, default=DEFAULT_PROFILE_DIR, help="carpeta de perfiles TOML"
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    discover = subparsers.add_parser("discover", help="lista las URLs que se ingeririan")
    discover.add_argument("--site", required=True)
    discover.add_argument("--limit", type=int, default=None)

    run = subparsers.add_parser("ingest", help="ejecuta Bronze -> Silver -> Gold")
    run.add_argument("--site", required=True)
    run.add_argument("--limit", type=int, default=None, help="tope de paginas en esta corrida")
    run.add_argument("--refresh", action="store_true", help="captura incremental con ETag/hash")
    run.add_argument("--quiet", action="store_true", help="sin barra de progreso (util en CI)")
    run.add_argument(
        "--ignore-robots",
        action="store_true",
        help="ignora robots.txt (solo para pruebas locales; no usar contra terceros)",
    )

    report = subparsers.add_parser("report", help="estado del corpus")
    report.add_argument("--site", required=True)

    rebuild_cmd = subparsers.add_parser(
        "rebuild", help="recalcula Silver y Gold desde el Bronze ya capturado (sin red)"
    )
    rebuild_cmd.add_argument("--site", required=True)
    rebuild_cmd.add_argument("--quiet", action="store_true", help="sin barra de progreso")

    subparsers.add_parser("profiles", help="lista los perfiles de sitio disponibles")
    return parser


def _profile(name: str, profile_dir: Path) -> SiteProfile:
    return load_profile(find_profile(name, profile_dir))


def _corpus(args: argparse.Namespace) -> Corpus:
    return Corpus(root=args.data_dir, site=args.site)


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "profiles":
            profiles = sorted(path.stem for path in args.profiles.glob("*.toml"))
            print("\n".join(profiles) if profiles else "no hay perfiles en " + str(args.profiles))
            return 0

        profile = _profile(args.site, args.profiles)

        if args.command == "discover":
            urls = list_urls(profile, limit=args.limit)
            print(f"{len(urls)} URLs para {profile.name} ({profile.host})")
            for url in urls:
                print(f"  {url}")
            return 0

        if args.command == "ingest":
            result = ingest(
                profile,
                _corpus(args),
                limit=args.limit,
                refresh=args.refresh,
                ignore_robots=args.ignore_robots,
                progress=not args.quiet,
            )
            print(
                f"[{result.site}] descubiertas={result.discovered} guardadas={result.stored} "
                f"omitidas={result.skipped} "
                f"silver={result.silver.written}/{result.silver.total} "
                f"gold={result.gold.written}/{result.gold.total} "
                f"descartadas={result.silver.removed} tokens={result.tokens}"
            )
            return 0

        if args.command == "rebuild":
            rebuilt = rebuild(profile, _corpus(args), progress=not args.quiet)
            print(
                f"[{rebuilt.site}] rebuild "
                f"silver={rebuilt.silver.written}/{rebuilt.silver.total} "
                f"gold={rebuilt.gold.written}/{rebuilt.gold.total} "
                f"descartadas={rebuilt.silver.removed} tokens={rebuilt.tokens}"
            )
            return 0

        if args.command == "report":
            corpus_stats = stats(_corpus(args))
            print(
                f"[{args.site}] raw={corpus_stats.raw_files} capturas={corpus_stats.captures} "
                f"urls={corpus_stats.unique_urls} silver={corpus_stats.processed} "
                f"gold={corpus_stats.gold} tokens={corpus_stats.tokens}"
            )
            return 0

    except ConfigError as error:
        print(f"error de configuracion: {error}", file=sys.stderr)
        return 2

    parser.error(f"comando desconocido: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
