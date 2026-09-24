from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from data.fotmob_provider import FotMobProvider, LEAGUES


ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_DIR = ROOT / "data" / "snapshots"


def main() -> None:
    season = datetime.now(timezone.utc).year
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)

    provider = FotMobProvider()
    failures = []

    for league_key, meta in LEAGUES.items():
        print(f"Refreshing {league_key} / {season}...")
        try:
            frame = provider.league_players(league_key, season)
            if frame.empty:
                raise RuntimeError("empty player table")
            path = SNAPSHOT_DIR / f"{league_key}_{season}.csv"
            frame.to_csv(path, index=False)
            print(f"  wrote {len(frame)} players to {path}")
        except Exception as exc:
            failures.append(f"{league_key}: {exc}")
            print(f"  failed: {exc}")

    if failures:
        raise SystemExit("Snapshot refresh failed: " + " | ".join(failures))


if __name__ == "__main__":
    main()
