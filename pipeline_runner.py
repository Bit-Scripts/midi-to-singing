import threading
import os
import wave
import subprocess
import replicate
import urllib.request
from utility_functions import (
    format_message, validate_syllables, map_syllables_to_durations, create_midi_with_variations,
    add_stress_to_durations, match_durations_to_music, adjust_midi_with_syllables,
    adjust_audio_duration, remove_silence, get_audio_duration, add_note_variation
)

class PipelineRunner:
    def __init__(self, logger):
        self.logger = logger
        self.lock = threading.Lock()
        self.wave_files = []

    def log(self, message, status="INFO"):
        """Logger centralisé pour les messages."""
        self.logger(format_message(message, status))

    def write_text_to_file(self, text, filename="temp_lyrics.txt"):
        """Écrit une chaîne de caractères dans un fichier texte."""
        if isinstance(text, str):
            with open(filename, "w", encoding="utf-8") as file:
                file.write(text)
            self.log(f"Fichier texte créé : {filename}", "INFO")
        return filename

    def run_pipeline(self, midi_file, lyrics, duration, pitch, custom_rvc_model_url):
        """Exécute le pipeline complet pour un fichier MIDI et une ligne de paroles."""
        try:
            self.log(f"Début du traitement pour le fichier MIDI : {midi_file}", "INFO")
            
            # Étape 1 : Valider les syllabes des paroles
            syllables = validate_syllables(lyrics)
            num_syllables = sum(count for _, count in syllables)
            rythme = self.calculate_tempo(num_syllables, duration)

            # Étape 2 : Ajuster le fichier MIDI en fonction des syllabes
            adjusted_midi_file = f"adjusted_{os.path.basename(midi_file)}"
            self.log(f"Ajustement du MIDI : {midi_file}", "INFO")
            adjusted_durations = self.adjust_midi(syllables, midi_file, adjusted_midi_file)

            # Étape 2.1 : Appliquer des variations de hauteur
            adjusted_notes = add_note_variation(midi_file, adjusted_durations)

            # Étape 2.2 : Créer un nouveau fichier MIDI avec les variations appliquées
            adjusted_notes_midi_file = f"notes_adjusted_{os.path.basename(midi_file)}"
            create_midi_with_variations(adjusted_midi_file, adjusted_notes, adjusted_durations, adjusted_notes_midi_file)

            # Étape 3 : Créer un fichier texte pour les paroles
            lyrics_file = f"lyrics_{os.path.basename(midi_file).replace('.mid', '.txt')}"
            self.write_text_to_file(lyrics, lyrics_file)

            # Étape 4 : Conversion MIDI vers audio
            output_wave = f"voice_{os.path.basename(midi_file)}.wav"
            self.log("Conversion du MIDI en audio...", "INFO")
            self.convert_to_audio(adjusted_notes_midi_file, output_wave, lyrics_file, rythme)

            # Étape 5 : Nettoyage et ajustement de l'audio
            cleaned_wave = f"cleaned_{output_wave}"
            adjusted_wave = f"adjusted_{output_wave}"
            self.cleanup_audio(output_wave, cleaned_wave, adjusted_wave, duration)

            # Étape 6 : Transformation de l'audio avec Replicate
            final_audio = f"final_{adjusted_wave}"
            self.transform_audio(adjusted_wave, final_audio, pitch, custom_rvc_model_url)
            
            # Étape 7 : Ajuster la durée audio finale
            adjusted_final_audio = f"final_adjusted_{output_wave}"
            adjust_audio_duration(final_audio, adjusted_final_audio, duration)

            # Renvoi de l'audio final ajusté
            return adjusted_final_audio
        
        except Exception as e:
            self.log(f"Erreur lors du traitement de {midi_file} : {str(e)}", "ERREUR")
            raise

    def convert_to_audio(self, adjusted_midi_file, output_wave, lyrics_file, rythme):
        """Convertit un fichier MIDI ajusté en audio."""
        try:
            subprocess.run([
                "python", "-m", "midi2voice",
                "-l", lyrics_file,
                "-m", adjusted_midi_file,
                "-lang", "english",
                "-g", "male",
                "-i", "0",
                "-t", str(rythme),
            ], check=True)
            subprocess.run(["mv", "voice.wav", output_wave], check=True)
            self.log(f"Audio généré : {output_wave}", "INFO")
        except subprocess.CalledProcessError as e:
            self.log(f"Erreur lors de la conversion MIDI en audio : {e}", "ERREUR")
            raise
        finally:
            if os.path.exists(lyrics_file):
                os.remove(lyrics_file)  # Supprimer le fichier texte temporaire

    def cleanup_audio(self, output_wave, cleaned_wave, adjusted_wave, target_duration):
        """Nettoie et ajuste l'audio généré."""
        remove_silence(output_wave, cleaned_wave)
        cleaned_duration = get_audio_duration(cleaned_wave)
        self.log(f"Durée après suppression des silences : {cleaned_duration:.2f} secondes", "INFO")

        adjust_audio_duration(cleaned_wave, adjusted_wave, target_duration)
        final_duration = get_audio_duration(adjusted_wave)
        self.log(f"Durée finale après ajustement : {final_duration:.2f} secondes", "INFO")
        
        if final_duration <= 0:
            raise ValueError(f"Le fichier audio est vide après suppression des silences : {cleaned_wave}")

    def adjust_midi(self, syllables, midi_file, adjusted_midi_file):
        """
        Ajuste un fichier MIDI selon les syllabes, tout en conservant les hauteurs des notes.
        """
        durations = map_syllables_to_durations(len(syllables))
        stressed_durations = add_stress_to_durations(durations, [0, 2])
        adjusted_durations = match_durations_to_music(stressed_durations)
        
        # Appeler la fonction mise à jour pour ajuster le MIDI
        adjust_midi_with_syllables(midi_file, syllables, adjusted_midi_file)
        
        self.log(f"Durées ajustées pour le MIDI : {adjusted_durations}", "INFO")
        return adjusted_durations

    def calculate_tempo(self, num_syllables, target_duration):
        """Calcule le tempo en BPM."""
        number_of_beats = 4
        return int((number_of_beats * 60) / target_duration)

    def transform_audio(self, input_file, output_file, pitch_adjustment=0, custom_rvc_model_url=None):
        """Transforme l'audio final avec l'API Replicate."""
        try:
            if not custom_rvc_model_url:
                raise ValueError("URL du modèle RVC personnalisée non spécifiée.")

            self.log(f"Utilisation du modèle RVC personnalisé : {custom_rvc_model_url}", "INFO")

            output = replicate.run(
                "pseudoram/rvc-v2:d18e2e0a6a6d3af183cc09622cebba8555ec9a9e66983261fc64c8b1572b7dce",
                input={
                    "protect": 0.5,
                    "f0_method": "rmvpe",
                    "rvc_model": "CUSTOM",
                    "custom_rvc_model_download_url": custom_rvc_model_url,
                    "input_audio": open(input_file, "rb"),
                    "index_rate": 0.3,
                    "pitch_change": pitch_adjustment,
                    "rms_mix_rate": 0.25,
                    "filter_radius": 3,
                    "output_format": "wav",
                    "crepe_hop_length": 128,
                }
            )

            if isinstance(output, str):
                urllib.request.urlretrieve(output, output_file)
            elif hasattr(output, "url"):
                urllib.request.urlretrieve(output.url, output_file)
            else:
                raise TypeError(f"Type inattendu pour 'output': {type(output)}")

            self.log(f"Audio transformé avec succès : {output_file}", "RÉUSSI")
        except ValueError as ve:
            self.log(f"Erreur dans les paramètres : {ve}", "ERREUR")
            raise
        except Exception as e:
            self.log(f"Erreur lors de la transformation audio : {str(e)}", "ERREUR")
            raise