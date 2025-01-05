# cli.py
import argparse
import os
from pipeline_runner import PipelineRunner
from utility_functions import concatenate_audio, clean_all_temporary_files

def validate_inputs(midi_files, lyrics_file):
    """
    Valide que le nombre de fichiers MIDI correspond au nombre de lignes dans le fichier de paroles.
    :param midi_files: Liste des fichiers MIDI.
    :param lyrics_file: Fichier contenant les paroles.
    :raises: ValueError si la validation échoue.
    """
    if not os.path.exists(lyrics_file):
        raise ValueError(f"Le fichier des paroles '{lyrics_file}' n'existe pas.")
    
    with open(lyrics_file, "r", encoding="utf-8") as f:
        lyrics_lines = f.readlines()

    if len(midi_files) != len(lyrics_lines):
        raise ValueError(
            f"Le nombre de fichiers MIDI ({len(midi_files)}) doit correspondre "
            f"au nombre de lignes dans le fichier de paroles ({len(lyrics_lines)})."
        )

def run_cli(args):
    """
    Exécute le pipeline en mode terminal.
    :param args: Arguments passés depuis main.py
    """
    # Logger simple
    logger = print

    # Valider les entrées
    try:
        validate_inputs(args.midi_files, args.lyrics_file)
    except ValueError as e:
        logger(f"Erreur de validation des entrées : {e}")
        exit(1)

    # Vérifier la clé Replicate
    replicate_token = args.replicate_token or os.getenv("REPLICATE_API_TOKEN")
    if not replicate_token:
        logger("Erreur : Aucune clé REPLICATE_API_TOKEN fournie ou exportée dans l'environnement.")
        exit(1)

    # Vérifier le modèle RVC personnalisé si sélectionné
    if args.rvc_voice == "CUSTOM" and not args.custom_rvc_url:
        logger("Erreur : Le modèle RVC personnalisé est requis lorsque 'CUSTOM' est sélectionné.")
        exit(1)

    # Exécuter le pipeline
    runner = PipelineRunner(logger)
    try:
        all_wave_files = []
        with open(args.lyrics_file, "r", encoding="utf-8") as f:
            lyrics_lines = [line.strip() for line in f.readlines()]

        for midi_file, lyrics in zip(args.midi_files, lyrics_lines):
            final_wave = runner.run_pipeline(
                midi_file=midi_file,
                lyrics=lyrics,
                duration=args.target_duration,
                pitch=0,  # Pitch par défaut
                custom_rvc_model_url=args.custom_rvc_url if args.rvc_voice == "CUSTOM" else None
            )
            all_wave_files.append(final_wave)

        # Concaténer les fichiers WAV
        concatenate_audio(args.output_file, all_wave_files)
        
        # Nettoyage des fichiers temporaires
        clean_all_temporary_files(len(all_wave_files))
        
        logger(f"Pipeline terminé avec succès. Fichier final : {args.output_file}")

    except Exception as e:
        logger(f"Erreur lors de l'exécution du pipeline : {e}")
        exit(1)

if __name__ == "__main__":
    run_cli()
