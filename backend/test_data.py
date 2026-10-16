from pathlib import Path
from data_loader import DATASETS


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"


print("\n==============================")
print("TEST DES DATASETS")
print("==============================\n")

print(
    "Dossier data :",
    DATA_DIR
)

print(
    "\nEmploi du temps JSON :",
    bool(
        DATASETS[
            "emplois_du_temps"
        ]
    )
)

print(
    "Emploi du temps CSV :",
    len(
        DATASETS[
            "emplois_du_temps_csv"
        ]
    )
)

print(
    "Contacts :",
    bool(
        DATASETS[
            "contacts"
        ]
    )
)

print(
    "FAQ :",
    bool(
        DATASETS[
            "faq"
        ]
    )
)

print(
    "Procédures :",
    bool(
        DATASETS[
            "procedures"
        ]
    )
)

print(
    "\n=============================="
)

print(
    "FIN DU TEST"
)

print(
    "=============================="
)