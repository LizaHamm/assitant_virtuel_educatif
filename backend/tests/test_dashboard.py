"""Test rapide du dashboard ESIC.

1) Démarrer FastAPI : python -m uvicorn app.main:app --reload
2) Dans un second terminal : python test_dashboard.py
"""

import json
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

BASE_URL = "http://127.0.0.1:8000"

ENDPOINTS = [
    "/api/dashboard/overview",
    "/api/dashboard/top-questions?limite=10",
    "/api/dashboard/categories",
    "/api/dashboard/intents",
    "/api/dashboard/evolution?jours=14",
    "/api/dashboard/hourly?heures=24",
    "/api/dashboard/peak-hours",
    "/api/dashboard/tendances",
    "/api/dashboard/emerging-topics?limite=8",
    "/api/dashboard/unresolved?limite=10",
    "/api/dashboard/feedback-summary",
]


def main():
    failures = 0
    print("=== TEST DASHBOARD ESIC ===\n")

    for endpoint in ENDPOINTS:
        try:
            with urlopen(BASE_URL + endpoint, timeout=30) as response:
                payload = json.loads(response.read().decode("utf-8"))
                ok = response.status == 200 and isinstance(payload, dict)
                print(f"{'OK' if ok else 'ERREUR'}  {endpoint}")
                if not ok:
                    failures += 1
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            failures += 1
            print(f"ERREUR  {endpoint} -> {exc}")

    print()
    if failures:
        print(f"RESULTAT : {failures} route(s) en erreur.")
        raise SystemExit(1)

    print("RESULTAT : toutes les routes dashboard répondent correctement.")


if __name__ == "__main__":
    main()
