"""Recette de charge/performance ESIC Assistant.

Depuis backend, backend FastAPI déjà démarré :

    python tests/test_performance.py
        -> test d'acceptation MVP avec 20 utilisateurs simultanés

    python tests/test_performance.py --full
        -> test fonctionnel demandé avec 100 utilisateurs simultanés

Le script crée une conversation différente par utilisateur pour ne pas déclencher
artificiellement le rate limiting par session.
"""

import argparse
import concurrent.futures
import json
import math
import statistics
import time
import urllib.error
import urllib.request


API_URL = "http://127.0.0.1:8000"
REQUEST_TIMEOUT = 90


def request_json(method, path, payload=None, timeout=REQUEST_TIMEOUT):
    body = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(
        f"{API_URL}{path}",
        data=body,
        headers=headers,
        method=method,
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
            elapsed = time.perf_counter() - started
            return response.status, (json.loads(raw) if raw else {}), elapsed
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        elapsed = time.perf_counter() - started
        try:
            data = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            data = {"raw": raw}
        return exc.code, data, elapsed
    except Exception as exc:
        return 0, {"error": repr(exc)}, time.perf_counter() - started


def percentile(values, p):
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, math.ceil((p / 100) * len(ordered)) - 1))
    return ordered[index]


def create_conversation():
    status, data, _ = request_json("POST", "/api/conversations")
    if status != 200 or not data.get("id"):
        raise RuntimeError(f"Création conversation impossible : HTTP {status} {data}")
    return data["id"]


def one_chat(conversation_id, index):
    questions = [
        "Quels sont les horaires de la bibliothèque ?",
        "Comment contacter la scolarité ?",
        "Quand ont lieu les rattrapages ?",
        "Comment emprunter un livre à la bibliothèque ?",
        "Comment me connecter au Wi-Fi du campus ?",
    ]
    question = questions[index % len(questions)]
    status, data, elapsed = request_json(
        "POST",
        "/api/chat",
        {
            "message": question,
            "conversation_id": conversation_id,
            "language": "fr",
        },
    )
    return {
        "index": index,
        "status": status,
        "elapsed": elapsed,
        "has_answer": bool(data.get("answer")) if isinstance(data, dict) else False,
        "detail": data,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--full",
        action="store_true",
        help="Lance 100 utilisateurs simultanés au lieu de 20.",
    )
    args = parser.parse_args()
    users = 100 if args.full else 20

    print("=" * 76)
    print(f"ESIC ASSISTANT — TEST PERFORMANCE — {users} UTILISATEURS SIMULTANES")
    print("=" * 76)

    status, data, health_time = request_json("GET", "/health")
    if status != 200:
        print(f"[ECHEC] Backend indisponible : HTTP {status} {data}")
        return 1
    print(f"[OK] /health en {health_time * 1000:.1f} ms")

    # Warm-up : charge spaCy / modèles NLP / Sentence-BERT / index FAISS avant
    # la mesure, afin de mesurer le service en régime normal et non le démarrage.
    print("Warm-up du pipeline IA...")
    warm_id = create_conversation()
    warm = one_chat(warm_id, 0)
    if warm["status"] != 200:
        print(f"[ECHEC] Warm-up : HTTP {warm['status']} {warm['detail']}")
        return 1
    print(f"[OK] Warm-up terminé en {warm['elapsed']:.3f} s")

    print(f"Création de {users} conversations indépendantes...")
    conversation_ids = []
    for index in range(users):
        try:
            conversation_ids.append(create_conversation())
        except Exception as exc:
            print(f"[ECHEC] Conversation {index + 1}/{users} : {exc}")
            return 1
    print(f"[OK] {len(conversation_ids)} conversations prêtes")

    print(f"Envoi simultané de {users} questions...")
    wall_started = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=users) as executor:
        futures = [
            executor.submit(one_chat, conversation_id, index)
            for index, conversation_id in enumerate(conversation_ids)
        ]
        results = [future.result() for future in concurrent.futures.as_completed(futures)]
    wall_elapsed = time.perf_counter() - wall_started

    successes = [r for r in results if r["status"] == 200 and r["has_answer"]]
    failures = [r for r in results if r not in successes]
    times = [r["elapsed"] for r in successes]

    print("\n--- RESULTATS ---")
    print(f"Réponses HTTP 200 avec réponse : {len(successes)}/{users}")
    print(f"Taux de succès                 : {(len(successes) / users) * 100:.1f}%")
    print(f"Durée murale du lot            : {wall_elapsed:.3f} s")
    print(f"Débit global                   : {len(successes) / wall_elapsed:.2f} réponses/s" if wall_elapsed else "Débit global : n/a")

    if times:
        print(f"Latence moyenne                : {statistics.mean(times):.3f} s")
        print(f"Latence médiane                : {statistics.median(times):.3f} s")
        print(f"Latence p95                    : {percentile(times, 95):.3f} s")
        print(f"Latence max                    : {max(times):.3f} s")
        print(f"Réponses <= 2 s                : {sum(t <= 2 for t in times)}/{len(times)}")
        print(f"Réponses <= 3 s                : {sum(t <= 3 for t in times)}/{len(times)}")

    if failures:
        print("\nPremiers échecs :")
        for failure in failures[:10]:
            print(
                f"- utilisateur {failure['index']}: HTTP {failure['status']} "
                f"en {failure['elapsed']:.3f}s — {failure['detail']}"
            )

    success_rate = len(successes) / users if users else 0
    p95 = percentile(times, 95) if times else float("inf")

    # Critère de recette : aucune erreur et, pour le test MVP à 20 utilisateurs,
    # p95 <= 3 s (le cahier indique <2 s dans les critères d'acceptation et
    # précise aussi que 2-3 s est acceptable en temps réel).
    availability_ok = success_rate == 1.0
    latency_ok = p95 <= 3.0

    print("\n--- VERDICT ---")
    print(f"Disponibilité sous charge : {'OK' if availability_ok else 'ECHEC'}")
    print(f"p95 <= 3 s               : {'OK' if latency_ok else 'A OPTIMISER'}")

    if args.full:
        print("Test fonctionnel 100 utilisateurs : " + ("OK" if availability_ok else "ECHEC"))
        # Pour le test 100 utilisateurs, on ne fait échouer le script que sur
        # les erreurs HTTP : la latence est rapportée séparément pour diagnostic.
        return 0 if availability_ok else 1

    print("Test d'acceptation 20 utilisateurs : " + ("OK" if availability_ok and latency_ok else "A CORRIGER"))
    return 0 if availability_ok and latency_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
