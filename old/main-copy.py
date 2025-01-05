import os
import sys
import wave
import subprocess
import replicate
import threading
import urllib.request
from pydub import AudioSegment
from pydub.silence import detect_nonsilent
from mido import MidiFile, MidiTrack, Message
from tqdm import tqdm
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QTextEdit, QPushButton, QLabel, QFileDialog
)
from PyQt6.QtCore import Qt
from old.midi_syllable_mapping import (
    process_verse_to_midi, 
    format_message, 
    analyze_verse, 
    map_syllables_to_durations, 
    add_stress_to_durations,
    match_durations_to_music,
    adjust_midi_with_syllables,
    adjust_audio_duration,
    adjust_audio_duration_and_tempo
)

# Rediriger uniquement pendant l'import ou l'exécution qui génère les warnings
sys.stderr = open(os.devnull, 'w')
from PIL import Image  # Exemple si Pillow génère les warnings
sys.stderr = sys.__stderr__



def green_tqdm(iterable, desc="Progression"):
    """
    Barre de progression personnalisée en vert vif avec tqdm.
    
    :param iterable: L'élément itérable sur lequel appliquer la barre.
    :param desc: Description de la barre.
    :return: Barre de progression en vert vif.
    """
    green_color = "\033[92m"  # Code ANSI pour le vert vif
    reset_color = "\033[0m"
    return tqdm(
        iterable,
        desc=f"{green_color}{desc}{reset_color}",
        bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]"
    )

# Exemple d'affichage d'un message au début du pipeline
print(format_message("Démarrage du pipeline pour le traitement audio et MIDI.", "ÉTAPE"))

def clean_extra_note_off(midi_file, output_file):
    midi = MidiFile(midi_file)
    cleaned_midi = MidiFile(ticks_per_beat=midi.ticks_per_beat)

    for track in midi.tracks:
        new_track = MidiTrack()
        active_notes = set()

        for msg in track:
            if msg.type == 'note_on' and msg.velocity > 0:
                active_notes.add(msg.note)
            elif msg.type == 'note_off':
                if msg.note in active_notes:
                    active_notes.remove(msg.note)
                else:
                    continue  # Ignorer le "note_off" superflu
            new_track.append(msg)

        cleaned_midi.tracks.append(new_track)

    cleaned_midi.save(output_file)
    print(format_message(f"Fichier MIDI nettoyé exporté : {output_file}", "INFO"))

def clean_temporary_files(files):
    """
    Supprime une liste de fichiers temporaires avec une barre de progression verte.
    :param files: Liste des chemins de fichiers à supprimer.
    """
    for file in green_tqdm(files, desc="Nettoyage des fichiers temporaires"):
        if os.path.exists(file):
            os.remove(file)

def clean_all_temporary_files():
    temp_files = [f"adjusted_{n}.mid" for n in range(len(lignes))]
    temp_files += [f"voice_{n}.wav" for n in range(len(lignes))]
    temp_files += [f"voice_cleaned_{n}.wav" for n in range(len(lignes))]
    temp_files += [f"adjusted_voice_{n}.wav" for n in range(len(lignes))]
    temp_files += [f"adjusted_voice_{n}.tmp.wav" for n in range(len(lignes))]
    temp_files += ["voice.xml"]
    temp_files += ["voice_sounds.wav"]
    temp_files += ["ligne.txt"]
    temp_files += ["voice_sounds_file.wav"]
    temp_files += ["singing_voice.wav"]
    temp_files += ["singing_voice.temp.wav"]
    clean_temporary_files(temp_files)

def add_silence_to_midi(input_file, output_file, target_duration):
    midi = MidiFile(input_file)
    ticks_per_beat = midi.ticks_per_beat

    # Calculez la durée actuelle
    current_duration = sum(msg.time for msg in midi.tracks[0])
    tempo = 80  # Par défaut 120 BPM
    for msg in midi.tracks[0]:
        if msg.type == 'set_tempo':
            tempo = msg.tempo

    seconds_per_tick = (tempo / 1_000_000) / ticks_per_beat
    current_duration_seconds = current_duration * seconds_per_tick

    # Ajouter des silences si nécessaire
    silence_needed = target_duration - current_duration_seconds
    if silence_needed > 0:
        ticks_to_add = int(silence_needed / seconds_per_tick)
        midi.tracks[0].append(Message('note_off', time=ticks_to_add))  # Ajouter un silence

    midi.save(output_file)
    print(format_message(f"Silences ajoutés, fichier exporté : {output_file}", "INFO"))

def get_midi_duration_in_seconds(file_path):
    """
    Calcule la durée d'un fichier MIDI en secondes, en tenant compte des ticks par battement.

    :param file_path: Chemin du fichier MIDI.
    :return: Durée en secondes.
    """
    midi = MidiFile(file_path)
    ticks_per_beat = midi.ticks_per_beat
    tempo = 500000  # Par défaut, 500 000 microsecondes par battement (120 BPM)

    total_ticks = 0
    for msg in midi.tracks[0]:  # Supposons une seule piste principale
        if msg.type == 'set_tempo':
            tempo = msg.tempo  # Si le tempo est défini dans le fichier MIDI
        total_ticks += msg.time

    # Convertir ticks en secondes
    seconds_per_tick = (tempo / 1_000_000) / ticks_per_beat
    duration_in_seconds = total_ticks * seconds_per_tick
    return duration_in_seconds

# Valider que chaque ligne a 4 syllabes
def validate_syllables(ligne):
    return analyze_verse(ligne)

def get_audio_duration(file_path):
	with wave.open(file_path, "rb") as wav_file:
		frames = wav_file.getnframes()
		rate = wav_file.getframerate()
		duration = frames / float(rate)
	return duration

def remove_silence(input_file, output_file, silence_threshold=-40, chunk_size=10, padding_ms=250):
    """
    Supprime les silences avant et après les parties audibles dans un fichier WAV,
    avec ajout d'une seconde de silence avant et après le vers.

    :param input_file: Chemin du fichier audio d'entrée.
    :param output_file: Chemin du fichier audio de sortie.
    :param silence_threshold: Niveau en dBFS en dessous duquel le son est considéré comme du silence.
    :param chunk_size: Taille des segments analysés (en millisecondes).
    :param padding_ms: Durée du silence ajouté avant et après (en millisecondes).
    """
    # Charger l'audio
    audio = AudioSegment.from_file(input_file, format="wav")

    # Détecter les segments non silencieux
    nonsilent_ranges = detect_nonsilent(audio, min_silence_len=chunk_size, silence_thresh=silence_threshold)

    if nonsilent_ranges:
        # Découper l'audio pour ne garder que les parties non silencieuses
        start_trim = nonsilent_ranges[0][0]
        end_trim = nonsilent_ranges[-1][1]
        trimmed_audio = audio[start_trim:end_trim]

        # Ajouter une seconde de silence avant et après
        silence = AudioSegment.silent(duration=padding_ms)
        trimmed_audio_with_padding = silence + trimmed_audio + silence

        # Sauvegarder le fichier audio modifié
        trimmed_audio_with_padding.export(output_file, format="wav")
        print(format_message(f"Silences supprimés et ajoutés : {input_file} -> {output_file}", "INFO"))
    else:
        print(format_message(f"Aucun son détecté dans : {input_file}. Fichier inchangé.", "ERREUR"))

lock = threading.Lock()

# Ouvrir le fichier contenant les paroles
with open("SOMH.txt", "r", encoding="utf8") as file:
	lignes = file.readlines()

# Liste pour stocker les fichiers wav générés
wave_files = []

for n, ligne in enumerate(lignes):
    if not ligne.strip():
        continue  # Ignorer les lignes vides

    syllables = validate_syllables(ligne)
    number_syllables = sum(count for word, count in syllables)

    # Calcul dynamique du tempo pour respecter 5 temps en 3 secondes
    number_of_beats = 4  # Nombre de temps
    target_duration = 3.0  # Durée cible en secondes
    rythme = int((number_of_beats * 60) / target_duration)  # Calcul du BPM

    with lock:
        print(format_message(f"Processing line {n}: {ligne.strip()}", "ÉTAPE"))

        # Écrire la ligne dans un fichier texte temporaire
        with open('ligne.txt', 'w') as lignetxt:
            lignetxt.write(ligne)
        lignetxt.close()

        midi_file = f"SOMH-Mesure{n}.mid"
        adjusted_midi_file = f"adjusted_{n}.mid"
        target_duration = 3.0  # Durée cible en secondes pour une mesure 4/4 à 80 BPM

        # Calculer et afficher la durée du MIDI original
        original_duration = get_midi_duration_in_seconds(midi_file)
        print(format_message(f"Durée du MIDI original ({midi_file}) : {original_duration:.2f} secondes", "INFO"))

        # Étape 1 : Calcul initial des durées pour chaque syllabe
        durations = map_syllables_to_durations(number_syllables)
        print(format_message(f"[Ligne {n}] Durées calculées initiales (avant ajustements musicaux) : {durations}", "ÉTAPE"))

        # Étape 2 : Application des accents toniques (par exemple, sur la 1re et la 3e syllabes)
        stressed_syllables = [0, 2]  # Indices des syllabes accentuées
        stressed_durations = add_stress_to_durations(durations, stressed_syllables)
        print(format_message(f"[Ligne {n}] Durées après ajout des accents toniques : {stressed_durations}", "ÉTAPE"))

        # Étape 3 : Ajustement des durées pour qu'elles correspondent aux valeurs musicales standard
        adjusted_durations = match_durations_to_music(stressed_durations)
        print(format_message(f"[Ligne {n}] Durées finales ajustées aux contraintes musicales (4 temps par mesure) : {adjusted_durations}", "ÉTAPE"))

        # Étape 4 : Ajuster le MIDI avec les durées calculées
        # adjust_midi(midi_file, adjusted_durations, adjusted_midi_file)
        adjust_midi_with_syllables(midi_file, syllables, adjusted_midi_file)
        print(format_message(f"Fichier MIDI ajusté généré : {adjusted_midi_file}", "ÉTAPE"))

        # Vérifier la durée du fichier MIDI ajusté
        adjusted_duration = get_midi_duration_in_seconds(adjusted_midi_file)
        print(format_message(f"Durée du MIDI traité ({adjusted_midi_file}) : {adjusted_duration:.2f} secondes", "INFO"))

        # Étape 5 : Convertir le MIDI ajusté en audio avec midi2voice
        output_wave = f"voice_{n}.wav"
        cleaned_wave = f"voice_cleaned_{n}.wav"
        subprocess.run([
            "python", "-m", "midi2voice",
            "-l", "ligne.txt",
            "-m", adjusted_midi_file,
            "-lang", "english",
            "-g", "male",
            "-i", "0",
            "-t", f"{rythme}",
        ], check=True)

        print(format_message(f"fichier voice_{n}.wav créé", "INFO"))

        # Renommer le fichier généré par midi2voice
        subprocess.run(["mv", "voice.wav", output_wave], check=True)

        # Étape 6 : Supprimer les silences dans l'audio
        remove_silence(output_wave, cleaned_wave)

        # Vérifier la durée après suppression des silences
        cleaned_duration = get_audio_duration(cleaned_wave)
        print(format_message(f"Durée après suppression des silences : {cleaned_duration:.2f} secondes", "INFO"))

        # Étape 7 : Ajuster la vitesse pour correspondre à la durée cible
        adjusted_wave = f"adjusted_voice_{n}.wav"
        adjust_audio_duration(cleaned_wave, adjusted_wave, target_duration)

        # Vérifier la durée après ajustement
        final_duration = get_audio_duration(adjusted_wave)
        print(format_message(f"Durée finale après ajustement : {final_duration:.2f} secondes", "INFO"))

        # Ajouter le fichier ajusté à la liste des fichiers WAV
        wave_files.append(adjusted_wave)

file.close()

# Concaténer tous les fichiers WAV générés
outfile = "voice_sounds.wav"
with wave.open(outfile, "wb") as wav_out:
	for i, wave_file in enumerate(wave_files):
		with wave.open(wave_file, "rb") as wav_in:
			if i == 0:
				# Copier les paramètres du premier fichier
				wav_out.setparams(wav_in.getparams())
			wav_out.writeframes(wav_in.readframes(wav_in.getnframes()))

print(format_message(f"Les fichiers WAV ont été concaténés dans : {outfile}", "RÉUSSI"))

# Appelle l'API Replicate pour transformer l'audio généré
output = replicate.run(
	"pseudoram/rvc-v2:d18e2e0a6a6d3af183cc09622cebba8555ec9a9e66983261fc64c8b1572b7dce",
	input={
		"protect": 0.5,
		"f0_method": "rmvpe",
		"rvc_model": "CUSTOM",
		"custom_rvc_model_download_url": "https://replicate.delivery/xezq/Kmoz4AGJAZrGKtla5kn2yh6eqEArVr9u7WcHHiqykO1VG9eTA/PaulWOISARDTheBG.zip",
		"input_audio": open(outfile, "rb"),
		"index_rate": 0.3,
		"pitch_change": 0,
		"rms_mix_rate": 0.25,
		"filter_radius": 3,
		"output_format": "wav",
		"crepe_hop_length": 128
	}
)

# Téléchargement du fichier de sortie
if isinstance(output, str):
    urllib.request.urlretrieve(output, "singing_voice.wav")
elif hasattr(output, 'url'):
    urllib.request.urlretrieve(output.url, "singing_voice.wav")
else:
    raise TypeError(f"Type inattendu pour 'output': {type(output)}")

# Ajustement de la durée à 12 secondes et Réglage du BPM de 73 à 80
print(format_message("Allongement de la durée à 12 secondes...", "INFO"))
print(format_message("Réglage du BPM de 73 à 80...", "INFO"))
adjust_audio_duration_and_tempo("singing_voice.wav", "output_file.wav", target_duration=12, old_bpm=73, new_bpm=80)

# Nettoyage des fichiers temporaires
print(format_message("Suppression des fichiers temporaires...", "INFO"))
clean_all_temporary_files()

# Annonce de la fin du pipeline
print(format_message("Audio transformé disponible ici : output_file.wav", "RÉUSSI"))

# Restaurer les erreurs standard
sys.stderr = sys.__stderr__