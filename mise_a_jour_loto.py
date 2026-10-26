import requests
import zipfile
import io
import os
from datetime import datetime

# --- LA LIGNE MAGIQUE ---
# Elle récupère le dossier exact où se trouve CE fichier .py
DOSSIER_SCRIPT = os.path.dirname(os.path.abspath(__file__))

# On construit les chemins complets
URL_FDJ = "https://media.fdj.fr/generated/game/loto/nouveau_loto.zip"
NOM_FICHIER_LOCAL = os.path.join(DOSSIER_SCRIPT, "loto_historique.csv")
FICHIER_LOG = os.path.join(DOSSIER_SCRIPT, "log_maj.txt")

def ecrire_log(message):
    """Écrit un message dans le fichier log avec l'heure."""
    with open(FICHIER_LOG, 'a', encoding='utf-8') as f:
        f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}\n")

def mettre_a_jour_csv():
    ecrire_log("Début de la mise à jour...")
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        response = requests.get(URL_FDJ, headers=headers, timeout=30)
        response.raise_for_status()
        
        with zipfile.ZipFile(io.BytesIO(response.content)) as z:
            nom_fichier_zip = z.namelist()[0]
            with z.open(nom_fichier_zip) as fichier_zip:
                contenu = fichier_zip.read()

        with open(NOM_FICHIER_LOCAL, 'wb') as f:
            f.write(contenu)
        
        ecrire_log("✅ Succès : Le fichier CSV a été mis à jour.")
        return True

    except Exception as e:
        ecrire_log(f"❌ Erreur : {e}")
        return False

if __name__ == "__main__":
    mettre_a_jour_csv()