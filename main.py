# main.py
import sys
import argparse
from PyQt6.QtWidgets import QApplication
from main_window import MainWindow
from pipeline_runner import PipelineRunner
from utility_functions import console_logger
from cli import run_cli

def run_gui():
    """Lance l'interface graphique."""
    app = QApplication(sys.argv)
    logger = console_logger
    main_window = MainWindow(logger, PipelineRunner(logger))
    main_window.show()
    sys.exit(app.exec())

def show_help():
    """Affiche l'aide pour l'utilisation du script."""
    help_text = """
    Utilisation :
        python main.py [OPTION]

    Options disponibles :
        -h, --help        Affiche cette aide
        --gui             Lance l'interface graphique
        --cli             Exécute le pipeline en mode terminal
    
    Exemples :
        python main.py --gui   Lance l'application en mode graphique
        python main.py --cli   Lance le pipeline dans le terminal
    """
    print(help_text)

def main():
    # Configuration de l'analyseur d'arguments
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('-h', '--help', action='store_true', help="Afficher l'aide")
    parser.add_argument('--gui', action='store_true', help="Lancer l'interface graphique")
    parser.add_argument('--cli', action='store_true', help="Lancer le pipeline en mode terminal")
    # Arguments supplémentaires pour le CLI
    parser.add_argument('-m', '--midi-files', nargs='+', help="Liste des fichiers MIDI")
    parser.add_argument('-l', '--lyrics-file', help="Fichier contenant les paroles")
    parser.add_argument('-o', '--output-file', default="voice_sounds.wav", help="Fichier de sortie audio final")
    parser.add_argument('-t', '--target-duration', type=float, default=3.0, help="Durée cible par ligne (en secondes)")
    parser.add_argument('-k', '--replicate-token', help="Clé API Replicate")
    parser.add_argument('-v', '--rvc-voice', choices=["CUSTOM", "Obama", "Trump", "Sandy", "Rogan"], default="CUSTOM", help="Voix RVC à utiliser")
    parser.add_argument('-c', '--custom-rvc-url', help="URL ou chemin du modèle RVC (si 'CUSTOM' est choisi)")
    args = parser.parse_args()

    # Gestion des arguments
    if args.help:
        show_help()
    elif args.gui:
        run_gui()
    elif args.cli:
        # Passer les arguments au CLI
        run_cli(args)
    else:
        # Si aucun argument n'est fourni, afficher l'aide par défaut
        show_help()

if __name__ == "__main__":
    main()
