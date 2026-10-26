from flask import Flask, render_template, request, redirect, url_for
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io
import base64
from itertools import combinations
from collections import Counter
import random
import os
import requests
import zipfile
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

app = Flask(__name__)

# --- LA LIGNE MAGIQUE POUR RENDER (Cache Matplotlib) ---
os.environ['MPLCONFIGDIR'] = '/tmp'

# --- Chemins absolus ---
DOSSIER_APP = os.path.dirname(os.path.abspath(__file__))
NOM_FICHIER_LOCAL = os.path.join(DOSSIER_APP, "loto_historique.csv")
FICHIER_COMPTEUR = os.path.join(DOSSIER_APP, "compteur.txt")

# URL officielle de la FDJ
URL_FDJ = "https://media.fdj.fr/generated/game/loto/nouveau_loto.zip"

# Fuseau horaire de Paris (gère automatiquement l'heure d'été / d'hiver)
FUSEAU_PARIS = ZoneInfo("Europe/Paris")


def formater_date_maj():
    """Renvoie la date de dernière modif du CSV, convertie en heure française."""
    if not os.path.exists(NOM_FICHIER_LOCAL):
        return "Inconnue"
    timestamp = os.path.getmtime(NOM_FICHIER_LOCAL)
    dt_utc = datetime.fromtimestamp(timestamp, tz=timezone.utc)
    dt_paris = dt_utc.astimezone(FUSEAU_PARIS)
    return dt_paris.strftime('%d/%m/%Y à %H:%M')


def incrementer_compteur():
    """Lit le compteur, l'incrémente et le sauvegarde."""
    try:
        if os.path.exists(FICHIER_COMPTEUR):
            with open(FICHIER_COMPTEUR, "r") as f:
                visites = int(f.read().strip())
        else:
            visites = 0

        visites += 1

        with open(FICHIER_COMPTEUR, "w") as f:
            f.write(str(visites))

        return visites
    except Exception as e:
        print(f"Erreur compteur : {e}")
        return 0


def telecharger_donnees_fdj():
    """Télécharge le ZIP de la FDJ et extrait le fichier CSV en local."""
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
        return True
    except Exception as e:
        print(f"Erreur lors du téléchargement FDJ : {e}")
        return False


def analyser_donnees():
    """Lit le CSV, calcule les stats et génère le graphique."""
    try:
        df = pd.read_csv(NOM_FICHIER_LOCAL, delimiter=';', header=0, encoding='iso-8859-1')

        colonnes_boules = ['boule_1', 'boule_2', 'boule_3', 'boule_4', 'boule_5']
        df_boules = df[colonnes_boules].apply(pd.to_numeric, errors='coerce').dropna()
        df_chance = df['numero_chance'].apply(pd.to_numeric, errors='coerce').dropna()

        # --- STATS PAR BOULE ---
        numeros = df_boules.values.flatten()
        compteur_boules = pd.Series(numeros).value_counts()
        compteur_boules = pd.Series(index=range(1, 50), data=compteur_boules.reindex(range(1, 50), fill_value=0))

        top_10 = compteur_boules.sort_values(ascending=False).head(10).to_dict()
        bottom_10 = compteur_boules.sort_values().head(10).to_dict()

        # --- STATS NUMÉROS CHANCE ---
        compteur_chance = df_chance.value_counts()
        compteur_chance = pd.Series(index=range(1, 11), data=compteur_chance.reindex(range(1, 11), fill_value=0))
        top_chance = compteur_chance.sort_values(ascending=False).head(10).to_dict()
        bottom_chance = compteur_chance.sort_values().head(10).to_dict()

        # --- DUOS ---
        compteur_paires = Counter()
        for _, row in df_boules.iterrows():
            boules_triees = sorted(row.tolist())
            for paire in combinations(boules_triees, 2):
                compteur_paires[paire] += 1
        top_paires = compteur_paires.most_common(10)

        # --- GRAPHIQUE (Fond transparent) ---
        COULEUR_TEXTE = '#f0f0f0'
        COULEUR_GRILLE = '#444444'
        COULEUR_BARRE = '#5eb5ff'
        COULEUR_MOYENNE = '#ff5e5e'

        fig, ax = plt.subplots(figsize=(12, 5))
        fig.patch.set_alpha(0.0)
        ax.patch.set_alpha(0.0)

        ax.bar(compteur_boules.index, compteur_boules.values, color=COULEUR_BARRE, edgecolor='none')
        moyenne_freq = compteur_boules.mean()
        ax.axhline(y=moyenne_freq, color=COULEUR_MOYENNE, linestyle='--', linewidth=2, label=f"Moyenne: {moyenne_freq:.2f}")

        ax.set_title('Fréquence des numéros tirés (Loto)', fontsize=14, color=COULEUR_TEXTE, pad=15)
        ax.set_xlabel('Numéro', color=COULEUR_TEXTE)
        ax.set_ylabel('Nombre de sorties', color=COULEUR_TEXTE)
        ax.tick_params(colors=COULEUR_TEXTE)
        ax.set_xticks(range(1, 50))
        ax.grid(True, color=COULEUR_GRILLE, alpha=0.5)

        legende = ax.legend()
        legende.get_frame().set_facecolor('none')
        legende.get_frame().set_edgecolor(COULEUR_GRILLE)
        for text in legende.get_texts():
            text.set_color(COULEUR_TEXTE)

        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['bottom'].set_color(COULEUR_GRILLE)
        ax.spines['left'].set_color(COULEUR_GRILLE)

        buf = io.BytesIO()
        fig.savefig(buf, format='png', bbox_inches='tight', transparent=True)
        buf.seek(0)
        image_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')
        plt.close(fig)

        return top_10, bottom_10, top_paires, image_base64, compteur_boules, top_chance, bottom_chance

    except Exception as e:
        print(f"Erreur analyse : {e}")
        return {}, {}, [], None, None, {}, {}


def calculer_ecarts():
    """Calcule le nombre de tirages depuis la dernière sortie de chaque numéro."""
    try:
        df = pd.read_csv(NOM_FICHIER_LOCAL, delimiter=';', header=0, encoding='iso-8859-1')
        colonnes_boules = ['boule_1', 'boule_2', 'boule_3', 'boule_4', 'boule_5']
        df_boules = df[colonnes_boules].apply(pd.to_numeric, errors='coerce').dropna()

        total_tirages = len(df_boules)
        ecarts = {i: total_tirages for i in range(1, 50)}

        for i, row in enumerate(df_boules.values[::-1]):
            for num in row:
                num = int(num)
                if ecarts[num] == total_tirages:
                    ecarts[num] = i

        return ecarts
    except Exception as e:
        print(f"Erreur calcul écarts : {e}")
        return {}


def calculer_trios():
    """Calcule le Top 10 des combinaisons de 3 numéros sortis ensemble."""
    try:
        df = pd.read_csv(NOM_FICHIER_LOCAL, delimiter=';', header=0, encoding='iso-8859-1')
        colonnes_boules = ['boule_1', 'boule_2', 'boule_3', 'boule_4', 'boule_5']
        df_boules = df[colonnes_boules].apply(pd.to_numeric, errors='coerce').dropna()

        compteur_trios = Counter()
        for _, row in df_boules.iterrows():
            boules_triees = sorted(row.tolist())
            for trio in combinations(boules_triees, 3):
                compteur_trios[trio] += 1

        return compteur_trios.most_common(10)
    except Exception as e:
        print(f"Erreur calcul trios : {e}")
        return []


def generer_grilles(compteur_boules, top_chance, bottom_chance):
    """Génère 3 grilles basées intelligemment sur les statistiques."""
    hot_pool = list(compteur_boules.sort_values(ascending=False).head(15).index)
    cold_pool = list(compteur_boules.sort_values().head(15).index)

    moyenne = compteur_boules.mean()
    equilibre_pool = list((compteur_boules - moyenne).abs().sort_values().head(15).index)

    chance_chauds = list(top_chance.keys())
    chance_froids = list(bottom_chance.keys())

    return {
        'chaude': {
            'boules': sorted(random.sample(hot_pool, 5)),
            'chance': random.choice(chance_chauds[:3]) if chance_chauds else random.randint(1, 10)
        },
        'froide': {
            'boules': sorted(random.sample(cold_pool, 5)),
            'chance': random.choice(chance_froids[:3]) if chance_froids else random.randint(1, 10)
        },
        'equilibree': {
            'boules': sorted(random.sample(equilibre_pool, 5)),
            'chance': random.choice(chance_chauds[4:7]) if len(chance_chauds) >= 7 else random.randint(1, 10)
        }
    }


def simuler_gains_historiques(mes_boules, ma_chance):
    """Calcule les gains cumulés d'une grille sur tout l'historique."""
    try:
        df = pd.read_csv(NOM_FICHIER_LOCAL, delimiter=';', header=0, encoding='iso-8859-1')
        total_gains = 0
        nb_tirages = 0
        tab_rangs = {5: 0, 4: 0, 3: 0, 2: 0, 1: 0, "chance": 0}

        for _, row in df.iterrows():
            try:
                tirage = [int(row['boule_1']), int(row['boule_2']), int(row['boule_3']), int(row['boule_4']), int(row['boule_5'])]
                chance_tirage = int(row['numero_chance'])
                nb_tirages += 1

                bonnes_boules = len(set(mes_boules) & set(tirage))
                bonne_chance = (ma_chance == chance_tirage)

                if bonnes_boules == 5 and bonne_chance:
                    total_gains += 2000000
                    tab_rangs[5] += 1
                elif bonnes_boules == 5:
                    total_gains += 100000
                    tab_rangs[5] += 1
                elif bonnes_boules == 4:
                    total_gains += 1000
                    tab_rangs[4] += 1
                elif bonnes_boules == 3:
                    total_gains += 20
                    tab_rangs[3] += 1
                elif bonnes_boules == 2:
                    total_gains += 5
                    tab_rangs[2] += 1
                elif bonnes_boules == 1 and bonne_chance:
                    total_gains += 2.2
                    tab_rangs[1] += 1
                elif bonne_chance:
                    total_gains += 2.2
                    tab_rangs["chance"] += 1
            except:
                continue

        return {
            'total': round(total_gains, 2),
            'tirages_visites': nb_tirages,
            'details': tab_rangs,
            'grille_testee': {'boules': sorted(mes_boules), 'chance': ma_chance}
        }
    except:
        return None


@app.route('/', methods=['GET', 'POST'])
def accueil():
    # Appel du compteur
    visites = incrementer_compteur()

    top_10, bottom_10, top_paires, graphique, compteur_boules, top_chance, bottom_chance = analyser_donnees()

    # Date de mise à jour convertie en heure française
    date_maj = formater_date_maj()

    grilles = None
    if request.args.get('generer') == '1' and compteur_boules is not None:
        grilles = generer_grilles(compteur_boules, top_chance, bottom_chance)

    resultat_simulation = None
    erreur_simulation = None
    if request.method == 'POST':
        try:
            b1 = int(request.form.get('b1', 0))
            b2 = int(request.form.get('b2', 0))
            b3 = int(request.form.get('b3', 0))
            b4 = int(request.form.get('b4', 0))
            b5 = int(request.form.get('b5', 0))
            ch = int(request.form.get('ch', 0))

            boules_user = [b1, b2, b3, b4, b5]

            if not all(1 <= x <= 49 for x in boules_user):
                erreur_simulation = "Les 5 boules doivent être comprises entre 1 et 49."
            elif not 1 <= ch <= 10:
                erreur_simulation = "Le numéro Chance doit être compris entre 1 et 10."
            elif len(set(boules_user)) != 5:
                erreur_simulation = "Les 5 boules doivent être toutes différentes !"
            else:
                resultat_simulation = simuler_gains_historiques(boules_user, ch)

        except (ValueError, TypeError):
            erreur_simulation = "Veuillez entrer des nombres valides."
        except Exception as e:
            print(f"Erreur formulaire simulation : {e}")

    return render_template('index.html',
                           top_10=top_10,
                           bottom_10=bottom_10,
                           top_paires=top_paires,
                           graphique=graphique,
                           grilles=grilles,
                           date_maj=date_maj,
                           top_chance=top_chance,
                           bottom_chance=bottom_chance,
                           simulation=resultat_simulation,
                           erreur_simulation=erreur_simulation,
                           visites=visites)


@app.route('/analyses')
def analyses():
    date_maj = formater_date_maj()

    ecarts = calculer_ecarts()
    ecarts_tries = dict(sorted(ecarts.items()))

    top_trios = calculer_trios()

    return render_template('analyses.html', date_maj=date_maj, ecarts=ecarts_tries, top_trios=top_trios)


@app.route('/maj')
def maj_donnees():
    telecharger_donnees_fdj()
    return redirect(url_for('accueil'))


if __name__ == '__main__':
    app.run(debug=True)
