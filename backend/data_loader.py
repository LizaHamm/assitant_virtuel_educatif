from __future__ import annotations

from pathlib import Path
import csv
import json


# ============================================================
# CHEMINS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"


# ============================================================
# LECTURE JSON
# ============================================================

def lire_json(nom_fichier: str):
    chemin = DATA_DIR / nom_fichier

    if not chemin.exists():
        print(f"[DATA] JSON introuvable : {nom_fichier}")
        return {}

    try:
        with open(
            chemin,
            "r",
            encoding="utf-8"
        ) as fichier:
            return json.load(fichier)

    except Exception as e:
        print(
            f"[DATA] Erreur JSON "
            f"{nom_fichier} : {e}"
        )
        return {}


# ============================================================
# LECTURE TEXTE
# ============================================================

def lire_texte(nom_fichier: str):
    chemin = DATA_DIR / nom_fichier

    if not chemin.exists():
        print(
            f"[DATA] Texte introuvable : "
            f"{nom_fichier}"
        )
        return ""

    try:
        return chemin.read_text(
            encoding="utf-8"
        )

    except UnicodeDecodeError:

        try:
            return chemin.read_text(
                encoding="cp1252"
            )
        except Exception as e:
            print(
                f"[DATA] Erreur texte "
                f"{nom_fichier} : {e}"
            )
            return ""

    except Exception as e:
        print(
            f"[DATA] Erreur texte "
            f"{nom_fichier} : {e}"
        )
        return ""


# ============================================================
# NORMALISATION DES EN-TÊTES
# ============================================================

def normaliser_entete(value: str) -> str:
    value = str(value or "").strip().lower()

    replacements = {
        "é": "e",
        "è": "e",
        "ê": "e",
        "ë": "e",
        "à": "a",
        "â": "a",
        "ä": "a",
        "î": "i",
        "ï": "i",
        "ô": "o",
        "ö": "o",
        "ù": "u",
        "û": "u",
        "ü": "u",
        "ç": "c",
        "œ": "oe",
    }

    for old, new in replacements.items():
        value = value.replace(old, new)

    value = value.replace(
        " ",
        "_"
    )

    value = value.replace(
        "-",
        "_"
    )

    return value


# ============================================================
# LECTURE CSV ROBUSTE
# ============================================================

def lire_csv(nom_fichier: str):
    chemin = DATA_DIR / nom_fichier

    if not chemin.exists():
        print(
            f"[DATA] CSV introuvable : "
            f"{nom_fichier}"
        )
        return []

    # --------------------------------------------------------
    # Lecture binaire puis décodage
    # --------------------------------------------------------

    try:
        contenu = chemin.read_bytes()

    except Exception as e:
        print(
            f"[DATA] Impossible de lire "
            f"{nom_fichier} : {e}"
        )
        return []

    texte = None

    for encodage in [
        "utf-8-sig",
        "utf-8",
        "cp1252",
        "latin1",
    ]:

        try:
            texte = contenu.decode(
                encodage
            )
            break

        except UnicodeDecodeError:
            continue

    if texte is None:
        print(
            f"[DATA] Encodage inconnu : "
            f"{nom_fichier}"
        )
        return []

    lignes = [
        ligne
        for ligne in texte.splitlines()
        if ligne.strip()
    ]

    if not lignes:
        print(
            f"[DATA] CSV vide : "
            f"{nom_fichier}"
        )
        return []

    # --------------------------------------------------------
    # Détection du séparateur
    # --------------------------------------------------------

    dialecte = None

    try:
        dialecte = csv.Sniffer().sniff(
            "\n".join(lignes[:10]),
            delimiters=";,|\t,"
        )

    except csv.Error:
        pass

    if dialecte is None:

        separateur = ";"

        for candidat in [
            ",",
            ";",
            "\t",
            "|",
        ]:

            if candidat in lignes[0]:
                separateur = candidat
                break

    else:
        separateur = dialecte.delimiter

    # --------------------------------------------------------
    # Lecture
    # --------------------------------------------------------

    lecteur = csv.reader(
        lignes,
        delimiter=separateur
    )

    rows = list(lecteur)

    if not rows:
        return []

    # --------------------------------------------------------
    # Recherche de l'en-tête
    # --------------------------------------------------------

    header_index = None

    for index, row in enumerate(
        rows[:20]
    ):

        normalises = [
            normaliser_entete(cell)
            for cell in row
        ]

        header_text = " ".join(
            normalises
        )

        if (
            "formation" in header_text
            or "groupe" in header_text
            or "matiere" in header_text
            or "cours" in header_text
        ):
            header_index = index
            break

    # --------------------------------------------------------
    # Aucun vrai header détecté
    # --------------------------------------------------------

    if header_index is None:

        print(
            f"[DATA] En-tête CSV non "
            f"identifié : {nom_fichier}"
        )

        # On tente quand même une lecture
        # avec la première ligne comme header.

        header_index = 0

    # --------------------------------------------------------
    # Création des colonnes
    # --------------------------------------------------------

    headers = [
        normaliser_entete(
            header
        )
        for header in rows[header_index]
    ]

    # Si des colonnes sont vides
    # on leur donne un nom unique.

    for index, header in enumerate(headers):

        if not header:
            headers[index] = f"colonne_{index + 1}"

    # --------------------------------------------------------
    # Conversion en dictionnaires
    # --------------------------------------------------------

    results = []

    for row in rows[
        header_index + 1:
    ]:

        if not row:
            continue

        item = {}

        for index, header in enumerate(
            headers
        ):

            if index < len(row):
                item[header] = row[index].strip()

            else:
                item[header] = ""

        # Ignorer les lignes complètement vides
        if not any(item.values()):
            continue

        results.append(item)

    print(
        f"[DATA] CSV chargé : "
        f"{nom_fichier} "
        f"({len(results)} lignes)"
    )

    return results


# ============================================================
# CHARGEMENT DES DATASETS
# ============================================================

def charger_datasets():

    print(
        "[DATA] Chargement des datasets..."
    )

    datasets = {

        # -----------------------------------------------
        # EMPLOI DU TEMPS
        # -----------------------------------------------

        "emplois_du_temps": lire_json(
            "emploi_du_temps.json"
        ),

        "emplois_du_temps_csv": lire_csv(
            "emploi_du_temps_exclusivité.csv"
        ),

        # -----------------------------------------------
        # CONTACTS
        # -----------------------------------------------

        "contacts": lire_json(
            "annuaire_contacts.json"
        ),

        # -----------------------------------------------
        # FAQ
        # -----------------------------------------------

        "faq": lire_json(
            "faq_complete.json"
        ),

        # -----------------------------------------------
        # PROCEDURES
        # -----------------------------------------------

        "procedures": lire_json(
            "procedures_esic.json"
        ),
    }

    # -----------------------------------------------
    # Autres fichiers texte présents
    # -----------------------------------------------

    datasets["texte_projet"] = lire_texte(
        "donnees_utiles_projet.pdf"
    )

    print(
        "[DATA] Chargement terminé."
    )

    return datasets


# ============================================================
# CHARGEMENT GLOBAL
# ============================================================

DATASETS = charger_datasets()