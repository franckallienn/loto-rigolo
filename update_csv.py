import requests
import zipfile
import io
import os

# URL de la FDJ
URL_FDJ = "https://media.fdj.fr/generated/game/loto/nouveau_loto.zip"
# Le fichier CSV est à la racine du dépôt
NOM_FICHIER_LOCAL = "loto_historique.csv"

def mettre_a_jour():
    print("Début de la mise à jour...")
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
        
        print("✅ Succès : Le fichier CSV a été mis à jour.")
        return True
    except Exception as e:
        print(f"❌ Erreur : {e}")
        return False

if __name__ == "__main__":
    mettre_a_jour()
