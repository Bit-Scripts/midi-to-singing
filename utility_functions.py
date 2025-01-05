# utility_functions
import os
from tqdm import tqdm
from mido import MidiFile, MidiTrack
from pydub import AudioSegment
from pydub.silence import detect_nonsilent
import syllapy
from mido import MidiFile, MidiTrack, Message
import cv2
import numpy as np
import soundfile as sf
import librosa
import logging
import wave

def console_logger(message):
    """
    Une fonction simple pour afficher les messages dans la console avec un formatage basique.
    """
    print(message)

# OU, si vous voulez un logger plus élaboré :
def setup_logger():
    """
    Configure un logger pour afficher des messages formatés.
    """
    logger = logging.getLogger("console_logger")
    logger.setLevel(logging.INFO)
    
    # Ajout d'un gestionnaire pour la console
    handler = logging.StreamHandler()
    handler.setLevel(logging.INFO)
    
    # Formatage des messages
    formatter = logging.Formatter("[%(levelname)s] %(message)s")
    handler.setFormatter(formatter)
    
def format_message(message, status="INFO"):
    """Formate un message de log."""
    return f"[{status}] {message}"

def print_format_message(message, status="INFO"):
    """Affiche un message formaté dans la console."""
    print(format_message(message, status))

def green_tqdm(iterable, desc="Progression"):
    """
    Barre de progression personnalisée avec tqdm.
    
    :param iterable: Élément itérable sur lequel appliquer la barre.
    :param desc: Description de la barre.
    :return: Barre de progression.
    """
    green_color = "\033[92m"  # Code ANSI pour le vert vif
    reset_color = "\033[0m"
    return tqdm(
        iterable,
        desc=f"{green_color}{desc}{reset_color}",
        bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]"
    )

def clean_temporary_files(files):
    """
    Supprime une liste de fichiers temporaires avec une barre de progression.
    
    :param files: Liste des chemins de fichiers à supprimer.
    """
    deleted_count = 0
    existing_files_count = len(files)  # Compte initial des fichiers
    for file in green_tqdm(files, desc="Nettoyage des fichiers temporaires"):
        if os.path.exists(file):
            try:
                os.remove(file)
                deleted_count += 1
            except Exception as e:
                print(f"Erreur lors de la suppression de {file} : {e}")
        else:
            existing_files_count -= 1  # Réduction du nombre de fichiers valides
    
    print(f"{deleted_count}/{existing_files_count} fichiers supprimés.")

def clean_all_temporary_files(num_lines, extra_files=None):
    """
    Supprime tous les fichiers temporaires liés au traitement des lignes.
    
    :param num_lines: Nombre de lignes à traiter, utilisé pour générer les noms de fichiers temporaires.
    """
    if not isinstance(num_lines, int) or num_lines < 0:
        raise ValueError("Le paramètre num_lines doit être un entier positif.")
    
    temp_files = [f"adjusted_{n}.mid" for n in range(num_lines)]
    temp_files += [f"adjusted_SOMH-Mesure{n}.mid" for n in range(num_lines)]
    temp_files += [f"notes_adjusted_SOMH-Mesure{n}.mid" for n in range(num_lines)]
    temp_files += [f"adjusted_adjusted_SOMH-Mesure{n}.mid" for n in range(num_lines)]
    temp_files += [f"voice_{n}.wav" for n in range(num_lines)]
    temp_files += [f"voice_cleaned_{n}.wav" for n in range(num_lines)]
    temp_files += [f"adjusted_voice_{n}.wav" for n in range(num_lines)]
    temp_files += [f"adjusted_voice_{n}.tmp.wav" for n in range(num_lines)]
    temp_files += [f"ligne_{n}.txt" for n in range(num_lines)]
    temp_files += [f"cleaned_voice_SOMH-Mesure{n}.mid.wav" for n in range(num_lines)]
    temp_files += [f"voice_SOMH-Mesure{n}.mid.wav" for n in range(num_lines)]
    temp_files += [f"adjusted_voice_SOMH-Mesure{n}.mid.wav" for n in range(num_lines)]
    temp_files += [f"adjusted_voice_adjusted_SOMH-Mesure{n}.mid.wav" for n in range(num_lines)]
    temp_files += [f"final_adjusted_voice_adjusted_SOMH-Mesure{n}.mid.wav" for n in range(num_lines)]
    temp_files += [f"final_adjusted_voice_SOMH-Mesure{n}.mid.wav" for n in range(num_lines)]
    temp_files += [f"voice_adjusted_SOMH-Mesure{n}.mid.wav" for n in range(num_lines)]
    temp_files += [f"final_adjusted_voice_SOMH-Mesure{n}.mid_uniform.wav" for n in range(num_lines)]
    temp_files += [f"adjusted_voice_SOMH-Mesure{n}.mid_uniform.wav" for n in range(num_lines)]
    temp_files += ["voice.xml", "ligne.txt", "voice_sounds_file.wav", "singing_voice.wav", "singing_voice.temp.wav"]

    if extra_files:
        temp_files += extra_files

    clean_temporary_files(temp_files)

def add_silence_to_midi(input_file, output_file, target_duration):
    """
    Ajoute des silences à un fichier MIDI pour atteindre une durée cible.
    
    :param input_file: Chemin du fichier MIDI d'entrée.
    :param output_file: Chemin du fichier MIDI de sortie.
    :param target_duration: Durée cible en secondes.
    """
    midi = MidiFile(input_file)
    ticks_per_beat = midi.ticks_per_beat

    current_duration = sum(msg.time for msg in midi.tracks[0])
    tempo = 80  # Par défaut, 120 BPM
    for msg in midi.tracks[0]:
        if msg.type == 'set_tempo':
            tempo = msg.tempo

    seconds_per_tick = (tempo / 1_000_000) / ticks_per_beat
    current_duration_seconds = current_duration * seconds_per_tick

    silence_needed = target_duration - current_duration_seconds
    if silence_needed > 0:
        ticks_to_add = int(silence_needed / seconds_per_tick)
        midi.tracks[0].append(MidiTrack([{'type': 'note_off', 'time': ticks_to_add}]))
    
    midi.save(output_file)
    print_format_message(f"Silences ajoutés, fichier exporté : {output_file}", "INFO")

def validate_syllables(verse):
    """
    Valide le nombre de syllabes dans un vers.
    
    :param verse: Texte du vers.
    :return: Analyse des syllabes (fictive pour le moment).
    """
    # Simulation d'une analyse (peut être remplacé par une vraie analyse)
    return [("word", len(word)) for word in verse.split()]

def get_audio_duration(file_path):
    """
    Calcule la durée d'un fichier audio en secondes.

    :param file_path: Chemin du fichier audio.
    :return: Durée en secondes.
    """
    audio = AudioSegment.from_file(file_path, format="wav")
    return len(audio) / 1000.0  # La durée est en millisecondes, donc division par 1000

def remove_silence(input_file, output_file, silence_threshold=-40, chunk_size=10, padding_ms=250):
    """
    Supprime les silences dans un fichier audio.
    
    :param input_file: Chemin du fichier audio d'entrée.
    :param output_file: Chemin du fichier audio de sortie.
    :param silence_threshold: Seuil de silence en dBFS.
    :param chunk_size: Taille des segments analysés en millisecondes.
    :param padding_ms: Durée du silence ajouté avant et après (en millisecondes).
    """
    audio = AudioSegment.from_file(input_file, format="wav")
    nonsilent_ranges = detect_nonsilent(audio, min_silence_len=chunk_size, silence_thresh=silence_threshold)

    if nonsilent_ranges:
        start, end = nonsilent_ranges[0][0], nonsilent_ranges[-1][1]
        trimmed_audio = audio[start:end]
        silence = AudioSegment.silent(duration=padding_ms)
        trimmed_audio_with_padding = silence + trimmed_audio + silence
        trimmed_audio_with_padding.export(output_file, format="wav")
        print_format_message(f"Silences supprimés : {input_file} -> {output_file}", "INFO")
    else:
        print_format_message(f"Aucun son détecté dans : {input_file}. Fichier inchangé.", "ERREUR")
        
def format_message(message, status="INFO"):
    """
    Formate un message avec une couleur et un statut spécifique.
    :param message: Le message à afficher.
    :param status: Statut du message ("INFO", "RÉUSSI", "ERREUR", "ÉTAPE").
    :return: Chaîne de caractères formatée.
    """
    colors = {
        "INFO": "\033[1;34m",    # Bleu
        "RÉUSSI": "\033[1;32m",  # Vert
        "ERREUR": "\033[1;31m",  # Rouge
        "ÉTAPE": "\033[1;33m"    # Jaune
    }
    reset = "\033[0m"
    color = colors.get(status, "\033[1;37m")  # Par défaut, blanc
    return f"{color}[{status}] {message}{reset}"

def adjust_audio_bpm(input_file, output_file, old_bpm, new_bpm):
    """
    Ajuste le tempo d'un fichier audio avec librosa sans changer le pitch.
    
    :param input_file: Chemin du fichier audio d'entrée.
    :param output_file: Chemin du fichier audio de sortie.
    :param old_bpm: BPM actuel.
    :param new_bpm: BPM cible.
    """
    # Charger l'audio
    y, sr = librosa.load(input_file, sr=None)

    # Calculer le facteur de vitesse
    speed_factor = new_bpm / old_bpm

    # Ajuster le tempo
    y_stretched = librosa.effects.time_stretch(y, speed_factor)

    # Sauvegarder le fichier
    sf.write(output_file, y_stretched, sr)
    print(format_message(f"Audio ajusté exporté vers : {output_file}", "INFO"))

def adjust_syllables_to_midi(syllables, beats_per_measure=4, total_duration=3.0):
    """
    Ajuste les durées des syllabes pour qu'elles correspondent à une mesure de 4 temps
    répartie sur une durée totale de 3 secondes.

    :param syllables: Liste des syllabes.
    :param beats_per_measure: Nombre de temps par mesure (par défaut 4).
    :param total_duration: Durée totale de la mesure en secondes (par défaut 3).
    :return: Liste des durées ajustées en temps MIDI.
    """
    num_syllables = len(syllables)
    time_per_beat = total_duration / beats_per_measure  # Durée d'un temps en secondes
    durations = [time_per_beat / num_syllables] * num_syllables  # Répartition égale
    
    # Ajuster pour respecter les contraintes musicales (durées classiques)
    music_temps = [4.0, 3.0, 2.0, 1.5, 1.0, 0.5, 0.33, 0.25]  # Durées possibles
    adjusted_durations = []

    for duration in durations:
        closest_duration = min(music_temps, key=lambda x: abs(x - duration))
        adjusted_durations.append(closest_duration)

    # Réajuster la somme pour être exactement égale à 4 temps
    scaling_factor = beats_per_measure / sum(adjusted_durations)
    adjusted_durations = [d * scaling_factor for d in adjusted_durations]

    return adjusted_durations

def adjust_midi_with_syllables(midi_file, syllables, output_file):
    """
    Ajuste un fichier MIDI pour répartir les syllabes avec des hauteurs de notes variées.

    :param midi_file: Chemin du fichier MIDI original.
    :param syllables: Liste des syllabes (utilisée pour ajuster les durées).
    :param output_file: Chemin du fichier MIDI ajusté à générer.
    """
    midi = MidiFile(midi_file)
    ticks_per_beat = midi.ticks_per_beat

    # Extraire les hauteurs des notes existantes
    original_notes = [msg.note for msg in midi.tracks[0] if msg.type == 'note_on' and msg.velocity > 0]
    if not original_notes:
        raise ValueError("Aucune note valide trouvée dans le fichier MIDI original.")

    # Calculer les durées ajustées pour les syllabes
    adjusted_durations = map_syllables_to_durations(len(syllables))

    # Créer une nouvelle piste MIDI
    new_midi = MidiFile(ticks_per_beat=ticks_per_beat)
    new_track = MidiTrack()
    new_midi.tracks.append(new_track)

    # Répartir les notes et durées
    for i, duration in enumerate(adjusted_durations):
        ticks = int(duration * ticks_per_beat)
        note = original_notes[i % len(original_notes)]  # Réutiliser les hauteurs existantes
        new_track.append(Message('note_on', note=note, velocity=64, time=0))
        new_track.append(Message('note_off', note=note, velocity=64, time=ticks))

    # Sauvegarder le nouveau fichier MIDI
    new_midi.save(output_file)
    print(f"[RÉUSSI] Fichier MIDI ajusté généré : {output_file}")

def add_note_variation(midi_file, adjusted_durations):
    """
    Ajoute des variations de hauteur aux notes du fichier MIDI en fonction des durées ajustées.

    :param midi_file: Chemin du fichier MIDI d'entrée.
    :param adjusted_durations: Liste des durées ajustées (en secondes ou ticks MIDI).
    :return: Liste des hauteurs ajustées des notes.
    """
    midi = MidiFile(midi_file)
    
    # Extraire les hauteurs des notes originales
    original_notes = [msg.note for msg in midi.tracks[0] if msg.type == 'note_on' and msg.velocity > 0]
    if not original_notes:
        raise ValueError("Aucune note valide trouvée dans le fichier MIDI original.")

    # Générer des variations sur les hauteurs
    adjusted_notes = []
    for i, duration in enumerate(adjusted_durations):
        # Choisir une note parmi les originales (par exemple, en boucle)
        original_note = original_notes[i % len(original_notes)]
        
        # Ajouter une variation (exemple : monter ou descendre d'un intervalle)
        variation = i % 5 - 2  # Cycle de -2 à +2 pour simuler des variations
        adjusted_note = max(0, min(127, original_note + variation))  # Clamper entre 0 et 127
        adjusted_notes.append(adjusted_note)

    return adjusted_notes

def create_midi_with_variations(input_midi_file, adjusted_notes, adjusted_durations, output_midi_file):
    """
    Crée un fichier MIDI avec des hauteurs ajustées et des durées spécifiques.

    :param input_midi_file: Chemin du fichier MIDI d'entrée.
    :param adjusted_notes: Liste des hauteurs ajustées des notes.
    :param adjusted_durations: Liste des durées des notes (en ticks MIDI).
    :param output_midi_file: Chemin du fichier MIDI de sortie.
    """
    if len(adjusted_notes) != len(adjusted_durations):
        raise ValueError("La longueur des notes ajustées ne correspond pas aux durées ajustées.")

    midi = MidiFile(input_midi_file)
    ticks_per_beat = midi.ticks_per_beat

    new_midi = MidiFile(ticks_per_beat=ticks_per_beat)
    new_track = MidiTrack()
    new_midi.tracks.append(new_track)

    for note, duration in zip(adjusted_notes, adjusted_durations):
        ticks = int(duration * ticks_per_beat)  # Conversion en ticks MIDI si nécessaire
        new_track.append(Message('note_on', note=note, velocity=64, time=0))
        new_track.append(Message('note_off', note=note, velocity=64, time=ticks))

    new_midi.save(output_midi_file)
    print(f"[RÉUSSI] Fichier MIDI avec variations généré : {output_midi_file}")

def match_durations_to_music(durations, beats_per_measure=4):
    """
    Ajuste les durées calculées pour qu'elles correspondent aux durées musicales classiques,
    tout en respectant le total de 4 temps par mesure.

    :param durations: Liste des durées calculées.
    :param beats_per_measure: Nombre de temps par mesure (par défaut 4).
    :return: Liste des durées musicales ajustées.
    """
    # Liste des durées musicales possibles (en fractions de 4 temps)
    music_temps = [6.0, 4.0, 3.0, 2.0, 1.5, 1.0, 0.5, 0.33, 0.25, 0.125, 0.0625]

    adjusted_durations = []

    for duration in durations:
        # Trouver la durée musicale la plus proche ou légèrement supérieure
        closest_duration = min(music_temps, key=lambda x: (x >= duration, abs(x - duration)))
        adjusted_durations.append(closest_duration)

    # Ajuster pour que la somme soit exactement égale à la mesure (4 temps)
    total_duration = sum(adjusted_durations)
    if total_duration != beats_per_measure:
        # Ajuster la dernière durée pour compenser la différence
        adjusted_durations[-1] += beats_per_measure - total_duration

    return adjusted_durations

def analyze_verse(verse):
    """
    Analyse un vers pour détecter les syllabes et les regrouper par mot.
    :param verse: Texte du vers.
    :return: Liste de tuples (mot, nombre de syllabes).
    """
    return [(word, syllapy.count(word)) for word in verse.split()]


def map_syllables_to_durations(syllable_count, beats_per_measure=4):
    """
    Mappe les syllabes dans une mesure 4/4 sur des durées musicales ajustées.
    :param syllable_count: Nombre total de syllabes dans le vers.
    :param beats_per_measure: Nombre de temps dans la mesure.
    :return: Liste des durées ajustées.
    """
    base_duration = beats_per_measure / syllable_count
    return [base_duration] * syllable_count


def adjust_durations(durations, beats_per_measure=4):
    """
    Ajuste les durées pour qu'elles respectent les durées musicales classiques
    et correspondent exactement à une mesure donnée.
    :param durations: Liste des durées calculées.
    :param beats_per_measure: Nombre de temps par mesure.
    :return: Liste des durées musicales ajustées.
    """
    music_temps = [6.0, 4.0, 3.0, 2.0, 1.5, 1.0, 0.5, 0.33, 0.25, 0.125]
    adjusted_durations = []

    for duration in durations:
        closest_duration = min(music_temps, key=lambda x: (x >= duration, abs(x - duration)))
        adjusted_durations.append(closest_duration)

    # Ajuster la somme pour correspondre exactement à 4 temps
    total_duration = sum(adjusted_durations)
    if total_duration != beats_per_measure:
        adjusted_durations[-1] += beats_per_measure - total_duration

    return adjusted_durations

def adjust_midi(midi_file, durations, output_file):
    """
    Ajuste un fichier MIDI pour correspondre aux durées données,
    tout en supprimant les silences (note_off et notes avec velocity 0).

    :param midi_file: Chemin du fichier MIDI d'entrée.
    :param durations: Liste des durées ajustées.
    :param output_file: Chemin du fichier MIDI ajusté à générer.
    """
    midi = MidiFile(midi_file)
    ticks_per_beat = midi.ticks_per_beat
    new_track = MidiTrack()
    current_time = 0

    # Suppression des silences (note_off et notes avec velocity 0)
    for msg in midi.tracks[0]:
        if msg.type == 'note_on' and msg.velocity > 0:
            # Seuls les messages note_on avec une vélocité > 0 sont conservés
            new_track.append(msg)

    # Ajustement des durées pour correspondre à 4 temps
    for duration in durations:
        ticks = int(duration * ticks_per_beat)
        new_track.append(Message('note_on', note=60, velocity=64, time=current_time))
        new_track.append(Message('note_off', note=60, velocity=64, time=ticks))
        current_time = 0  # Réinitialiser le temps pour la prochaine note

    # Remplacement de la piste originale par la piste ajustée
    midi.tracks[0] = new_track
    midi.save(output_file)
    print(format_message(f"Fichier MIDI ajusté généré : {output_file}", "RÉUSSI"))

def process_verse_to_midi(verse, midi_template, output_midi):
    """
    Traite un vers pour générer un fichier MIDI synchronisé avec ses syllabes.
    :param verse: Texte du vers à traiter.
    :param midi_template: Modèle de fichier MIDI à utiliser.
    :param output_midi: Nom du fichier MIDI ajusté à générer.
    """
    # Analyse des syllabes et calcul des durées
    syllables = analyze_verse(verse)
    syllable_count = sum(count for _, count in syllables)
    durations = map_syllables_to_durations(syllable_count)
    adjusted_durations = adjust_durations(durations)

    # Ajuster le fichier MIDI
    adjust_midi(midi_template, adjusted_durations, output_midi)

def add_stress_to_durations(durations, stressed_syllables):
    """
    Ajoute un accent tonique aux durées musicales.
    :param durations: Liste des durées musicales.
    :param stressed_syllables: Indices des syllabes accentuées.
    :return: Liste des durées ajustées.
    """
    stressed_durations = []
    for i, duration in enumerate(durations):
        if i in stressed_syllables:
            stressed_durations.append(duration + 0.5)  # Accentuer la durée
        else:
            stressed_durations.append(duration)
    return stressed_durations

def adjust_audio_duration(input_file, output_file, target_duration):
    """
    Ajuste la durée d'un fichier audio à l'aide d'OpenCV en redimensionnant les données audio.

    :param input_file: Chemin du fichier audio d'entrée.
    :param output_file: Chemin du fichier audio de sortie.
    :param target_duration: Durée cible en secondes.
    """
    # Charger l'audio avec soundfile
    data, sample_rate = sf.read(input_file)
    current_duration = len(data) / sample_rate

    # Calcul du ratio de redimensionnement
    resize_ratio = target_duration / current_duration
    new_length = int(len(data) * resize_ratio)

    # Si stéréo, traiter les deux canaux
    if len(data.shape) > 1:  # Stéréo
        resized_data = np.zeros((new_length, data.shape[1]))
        for channel in range(data.shape[1]):
            resized_data[:, channel] = cv2.resize(
                data[:, channel], (1, new_length), interpolation=cv2.INTER_LINEAR
            ).flatten()
    else:  # Mono
        resized_data = cv2.resize(
            data, (1, new_length), interpolation=cv2.INTER_LINEAR
        ).flatten()

    # Exporter l'audio ajusté
    sf.write(output_file, resized_data, sample_rate)
    print(format_message(f"Audio ajusté exporté vers : {output_file}", "RÉUSSI"))

def convert_to_uniform_format(input_file, output_file, channels=2, sample_rate=44100):
    """
    Convertit un fichier audio au format uniforme (stéréo, 44,1 kHz).

    :param input_file: Chemin du fichier d'entrée.
    :param output_file: Chemin du fichier de sortie.
    :param channels: Nombre de canaux (1=mono, 2=stéréo).
    :param sample_rate: Taux d'échantillonnage cible.
    """
    audio = AudioSegment.from_file(input_file)
    audio = audio.set_frame_rate(sample_rate).set_channels(channels)
    audio.export(output_file, format="wav")

def concatenate_audio(output_file, all_wave_files):
    """
    Concatène plusieurs fichiers WAV dans un seul fichier de sortie.

    :param output_file: Chemin du fichier de sortie.
    :param all_wave_files: Liste des fichiers WAV à concaténer.
    """
    try:
        with wave.open(output_file, "wb") as wav_out:
            for i, wave_file in enumerate(all_wave_files):
                with wave.open(wave_file, "rb") as wav_in:
                    if i == 0:
                        # Copier les paramètres du premier fichier
                        wav_out.setparams(wav_in.getparams())
                    else:
                        # Vérifiez que les paramètres sont cohérents
                        if wav_in.getnchannels() != wav_out.getnchannels() or \
                           wav_in.getsampwidth() != wav_out.getsampwidth() or \
                           wav_in.getframerate() != wav_out.getframerate():
                            raise ValueError(
                                f"Les propriétés audio du fichier {wave_file} ne correspondent pas : "
                                f"canaux={wav_in.getnchannels()}, largeur={wav_in.getsampwidth()}, "
                                f"fréquence={wav_in.getframerate()}"
                            )
                    # Ajout des données audio
                    wav_out.writeframes(wav_in.readframes(wav_in.getnframes()))
        print(f"\033[1m\033[92m[RÉUSSI] Audio final concaténé : {output_file}\033[0m")
    except Exception as e:
        raise ValueError(f"Erreur lors de la concaténation des fichiers audio : {e}")


