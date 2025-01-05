import syllapy
from mido import MidiFile, MidiTrack, Message
import cv2
import numpy as np
import soundfile as sf
import librosa

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
    Ajuste un fichier MIDI pour respecter 4 temps en 3 secondes, en fonction des syllabes.

    :param midi_file: Chemin du fichier MIDI original.
    :param syllables: Liste des syllabes.
    :param output_file: Chemin du fichier MIDI ajusté à générer.
    """
    midi = MidiFile(midi_file)
    ticks_per_beat = midi.ticks_per_beat

    # Calculer les durées ajustées pour les syllabes
    adjusted_durations = adjust_syllables_to_midi(syllables)
    print(format_message(f"Durées ajustées pour les syllabes : {adjusted_durations}", "INFO"))

    # Créer une nouvelle piste MIDI avec les durées ajustées
    new_midi = MidiFile(ticks_per_beat=ticks_per_beat)
    new_track = MidiTrack()
    current_ticks = 0

    for duration in adjusted_durations:
        ticks = int(duration * ticks_per_beat)
        new_track.append(Message('note_on', note=60, velocity=64, time=current_ticks))
        new_track.append(Message('note_off', note=60, velocity=64, time=ticks))
        current_ticks = 0  # Pour la prochaine note

    new_midi.tracks.append(new_track)
    new_midi.save(output_file)
    print(format_message(f"Fichier MIDI ajusté généré : {output_file}", "RÉUSSI"))

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

def adjust_audio_duration_and_tempo(input_file, output_file, target_duration, old_bpm, new_bpm):
    # Charger l'audio
    y, sr = librosa.load(input_file, sr=None)

    # Ajuster la durée pour atteindre la durée cible
    current_duration = librosa.get_duration(y=y, sr=sr)
    stretch_ratio = target_duration / current_duration
    y_stretched = librosa.effects.time_stretch(y, rate=stretch_ratio)

    # Ajuster le tempo
    tempo_ratio = new_bpm / old_bpm
    y_final = librosa.effects.time_stretch(y_stretched, rate=tempo_ratio)

    # Sauvegarder le fichier ajusté
    sf.write(output_file, y_final, sr)
    print(format_message(f"Audio ajusté exporté vers : {output_file}", "INFO"))

# Exemple d'utilisation
def main():
    verses = [
        "Hello how are you",
        "I am fine thank you",
    ]
    midi_template = "input_template.mid"  # Fichier MIDI modèle

    for i, verse in enumerate(verses):
        output_midi = f"adjusted_verse_{i}.mid"
        process_verse_to_midi(verse, midi_template, output_midi)


if __name__ == "__main__":
    main()
