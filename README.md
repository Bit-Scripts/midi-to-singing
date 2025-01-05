# MIDI to Singing Pipeline

<div align="center">
  <img src="Logo.webp" alt="Project Logo" width="200">
</div>

`MIDI to Singing Pipeline` est un projet Python permettant de transformer des fichiers MIDI et des paroles en fichiers audio chantés. Il utilise une combinaison d'outils comme **RVC v2**, des scripts de traitement MIDI et une interface graphique PyQt6 pour offrir une solution complète.

---

## Fonctionnalités

- **CLI et GUI** : Choisissez entre une interface graphique ou une interface en ligne de commande.
- **Prise en charge des voix RVC v2** : Modèles personnalisés ou préexistants.
- **Ajustement des durées et des hauteurs** : Conversion précise des syllabes et des rythmes MIDI en audio.
- **Concaténation audio** : Génère un fichier audio final combinant tous les morceaux.

---

## Prérequis

---

### Environnement Python

1. Python 3.8 ou supérieur.
2. Créez un environnement virtuel et installez les dépendances :

   ```bash
   python -m venv myenv
   source myenv/bin/activate  # Sous Windows : myenv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Exécutez les tests pour vérifier l'installation :

   ```bash
   python main.py --help
   ```
## Utilisation

---

### Interface graphique (GUI)
Pour lancer l'application avec une interface graphique :

   ```bash
   python main.py --gui
   ```

---

### Ligne de commande (CLI)
Pour lancer le pipeline directement dans le terminal :

```bash
python main.py --cli -m SOMH-Mesure0.mid SOMH-Mesure1.mid SOMH-Mesure2.mid SOMH-Mesure3.mid \
-l SOMH.txt -o voice_sounds.wav -t 3.0 -v CUSTOM \
-c https://replicate.delivery/xezq/Kmoz4AGJAZrGKtla5kn2yh6eqEArVr9u7WcHHiqykO1VG9eTA/PaulWOISARDTheBG.zip
```

---

### Paramètres de la CLI
- -m, --midi-files : Liste des fichiers MIDI (un fichier par ligne de paroles).
- -l, --lyrics-file : Fichier contenant les paroles (une ligne par fichier MIDI).
- -o, --output-file : Fichier de sortie audio final (par défaut : voice_sounds.wav).
- -t, --target-duration : Durée cible par ligne en secondes (par défaut : 3.0).
- -k, --replicate-token : Clé API REPLICATE_API_TOKEN (par défaut, lue dans l'environnement).
- -v, --rvc-voice : Voix RVC à utiliser (CUSTOM, Obama, Trump, etc.).
- -c, --custom-rvc-url : URL ou chemin du modèle RVC v2 (requis si CUSTOM est sélectionné).

---

## Organisation des fichiers
- `main.py` : Point d'entrée principal.
- `cli.py` : Gestion de la CLI.
- `main_window.py` : Interface graphique PyQt6.
- `pipeline_runner.py` : Gestion du pipeline (traitement MIDI, conversion audio, etc.).
- `utility_functions.py` : Fonctions utilitaires partagées.
- `requirements.txt` : Dépendances nécessaires.

---

## Requirements

- **Python:** Version 3.x (recommandé >= 3.8)
- **MuseScore:** Logiciel utilisé pour convertir les fichiers MIDI en MusicXML. Téléchargez-le depuis MuseScore.
- **Replicate API:** Utilisez Replicate pour transformer les fichiers audio.

---

### Installation des dépendances

Installez les dépendances via pip :

```bash
pip install -r requirements.txt
```

Ajoutez également la bibliothèque midi2voice directement depuis GitHub :

```bash
pip install git+git://github.com/mathigatti/midi2voice.git
```

---

### Configurer la clé API de Replicate

1. Créez un compte sur [Replicate](https://replicate.com/).
2. Copiez votre REPLICATE_API_TOKEN depuis votre tableau de bord.
3. Définissez la clé d'environnement avant d'utiliser l'application :

```bash
export REPLICATE_API_TOKEN=<votre_token>
```

---

## Contribuer

1. Clonez le dépôt :
```bash
git clone https://github.com/Bit-Scripts/midi-to-singing
cd midi-to-singing
```

2. Créez une branche pour vos modifications :
```bash
git checkout -b feature/ma-nouvelle-feature
```

3. Faites une pull request pour proposer vos modifications.

---

## Licence
Ce projet est distribué sous la licence GPL v3. Voir LICENSE.md pour plus de détails.

---

## Ressources
[RVC v2 Repository](https://github.com/RVC-repo)  
[Documentation PyQt6](https://doc.qt.io/qtforpython-6/)   
[GPL v3 Markdown File](./LICENSE.md)  

---

### Citations

- Auteur de **`midi2voice`** :  
  Gatti, M. (2020). mathigatti/midi2voice v1.0.0 (v1.0.0) [Computer software]. Zenodo.  
  DOI : [10.5281/ZENODO.3969003](https://doi.org/10.5281/ZENODO.3969003)