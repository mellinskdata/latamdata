from dataclasses import dataclass

@dataclass(frozen=True)
class League:
    key: str
    name: str
    country: str
    espn_slug: str

LEAGUES = {
    "bra_a": League("bra_a", "Brasileirão Série A", "Brasil", "bra.1"),
    "bra_b": League("bra_b", "Brasileirão Série B", "Brasil", "bra.2"),
    "arg_a": League("arg_a", "Liga Profesional Argentina", "Argentina", "arg.1"),
}

DEFAULT_SEASON = 2026
APP_NAME = "LATAMDATA"
APP_TAGLINE = "Football intelligence for South America"
