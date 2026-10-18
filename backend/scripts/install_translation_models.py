"""Install Argos Translate language models for English <-> French.

Run from the backend directory with its virtual environment activated:
    python scripts/install_translation_models.py
"""

import sys

try:
    import argostranslate.package as argos_package
    import argostranslate.translate as argos_translate
except ImportError as exc:
    raise SystemExit(
        "Argos Translate n'est pas installé dans cet environnement. "
        "Lancez : python -m pip install argostranslate"
    ) from exc


def is_translation_installed(source: str, target: str) -> bool:
    languages = {
        language.code: language
        for language in argos_translate.get_installed_languages()
    }
    if source not in languages or target not in languages:
        return False
    try:
        return languages[source].get_translation(languages[target]) is not None
    except Exception:
        return False


def main() -> None:
    print("Mise à jour de l'index des modèles Argos…", flush=True)
    try:
        argos_package.update_package_index()
        available = argos_package.get_available_packages()
    except Exception as exc:
        raise SystemExit(
            f"Impossible de récupérer les modèles Argos : {exc}\n"
            "Vérifie ta connexion Internet puis relance cette commande."
        ) from exc

    for source, target in (("en", "fr"), ("fr", "en")):
        if is_translation_installed(source, target):
            print(f"Modèle {source} -> {target} déjà installé.", flush=True)
            continue

        package = next(
            (item for item in available
             if item.from_code == source and item.to_code == target),
            None,
        )
        if package is None:
            pairs = sorted({
                f"{item.from_code}->{item.to_code}"
                for item in available
                if (item.from_code, item.to_code) in {
                    ("en", "fr"), ("fr", "en")
                }
            })
            raise SystemExit(
                f"Aucun paquet Argos direct disponible pour {source}->{target}. "
                f"Paires anglais/français trouvées : {pairs or 'aucune'}."
            )

        print(f"Téléchargement du modèle {source} -> {target}…", flush=True)
        try:
            package_path = package.download()
            argos_package.install_from_path(package_path)
        except Exception as exc:
            raise SystemExit(
                f"Échec d'installation du modèle {source}->{target}: {exc}"
            ) from exc

        if not is_translation_installed(source, target):
            raise SystemExit(
                f"Installation terminée mais modèle {source}->{target} "
                "introuvable dans la liste des modèles installés."
            )
        print(f"Modèle {source} -> {target} installé.", flush=True)

    print("\nLes deux directions de traduction sont prêtes. Redémarre le backend.")


if __name__ == "__main__":
    main()
