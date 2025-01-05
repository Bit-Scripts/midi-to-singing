# main_window.py
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView, QComboBox,
    QSpinBox, QFileDialog
)
from PyQt6.QtCore import Qt
from utility_functions import clean_all_temporary_files, format_message, concatenate_audio, convert_to_uniform_format
import os

class MainWindow(QMainWindow):
    def __init__(self, logger=None, pipeline_runner=None):
        super().__init__()
        self.logger = logger
        self.pipeline_runner = pipeline_runner
        self.setWindowTitle("Pipeline Audio - UI")
        self.resize(800, 600)

        # Layout principal
        self.layout = QVBoxLayout()

        # Ajouter les composants UI
        self.setup_global_params()
        self.setup_table()
        self.setup_buttons()

        # Configurer le widget central
        central_widget = QWidget()
        central_widget.setLayout(self.layout)
        self.setCentralWidget(central_widget)

    def log(self, message, status="INFO"):
        """Affiche un message formaté via le logger."""
        self.logger(format_message(message, status))

    def setup_global_params(self):
        """Champs pour définir les paramètres globaux."""
        params_layout = QVBoxLayout()

        # Clé API Replicate
        replicate_api_layout = QHBoxLayout()
        self.replicate_api_input = QLineEdit()
        self.replicate_api_input.setPlaceholderText("Entrez votre clé REPLICATE_API_TOKEN")
        replicate_api_layout.addWidget(QLabel("Clé API Replicate :"))
        replicate_api_layout.addWidget(self.replicate_api_input)

        # Menu déroulant pour sélectionner la voix RVC
        rvc_voice_layout = QHBoxLayout()
        self.rvc_voice_combo = QComboBox()
        self.rvc_voice_combo.addItems(["CUSTOM", "Obama", "Trump", "Sandy", "Rogan"])
        self.rvc_voice_combo.currentTextChanged.connect(self.toggle_custom_rvc_url)
        rvc_voice_layout.addWidget(QLabel("Voix RVC :"))
        rvc_voice_layout.addWidget(self.rvc_voice_combo)

        # Champ texte pour l'URL du modèle RVC (si CUSTOM est sélectionné)
        rvc_url_layout = QHBoxLayout()
        self.custom_rvc_url_input = QLineEdit("https://replicate.delivery/xezq/Kmoz4AGJAZrGKtla5kn2yh6eqEArVr9u7WcHHiqykO1VG9eTA/PaulWOISARDTheBG.zip")
        self.custom_rvc_url_input.setPlaceholderText("Entrez l'URL ou le chemin du modèle RVC v2 (si CUSTOM)")
        browse_button = QPushButton("[...]")
        browse_button.clicked.connect(self.browse_rvc_model)
        rvc_url_layout.addWidget(self.custom_rvc_url_input)
        rvc_url_layout.addWidget(browse_button)
        params_layout.addLayout(replicate_api_layout)
        params_layout.addLayout(rvc_voice_layout)
        params_layout.addLayout(rvc_url_layout)

        # Autres paramètres globaux
        self.output_file_input = QLineEdit("voice_sounds.wav")
        self.output_file_input.setPlaceholderText("Fichier de sortie audio")
        params_layout.addWidget(QLabel("Fichier de sortie audio :"))
        params_layout.addWidget(self.output_file_input)

        self.layout.addLayout(params_layout)

    def browse_rvc_model(self):
        """Ouvre une boîte de dialogue pour sélectionner un fichier local pour le modèle RVC."""
        file_dialog = QFileDialog()
        file_dialog.setNameFilter("Fichiers ZIP (*.zip);;Tous les fichiers (*)")
        if file_dialog.exec():
            selected_file = file_dialog.selectedFiles()[0]
            self.custom_rvc_url_input.setText(selected_file)

    def toggle_custom_rvc_url(self, voice):
        """Affiche ou masque le champ URL RVC personnalisé."""
        self.custom_rvc_url_input.setVisible(voice == "CUSTOM")

    def setup_table(self):
        """Tableau pour associer fichiers MIDI et lignes de paroles."""
        self.table = QTableWidget(0, 5)  # 5 colonnes : Action, Fichier MIDI, Paroles, Durée, Pitch
        self.table.setHorizontalHeaderLabels(["Action", "Fichier MIDI", "Ligne de paroles", "Durée", "Pitch"])

        header = self.table.horizontalHeader()
        self.table.setColumnWidth(0, 80)  # Colonne "Action" : taille fixe
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Colonne "Fichier MIDI"
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)  # Colonne "Paroles"
        self.table.setColumnWidth(3, 60)  # Colonne "Durée" : taille fixe
        self.table.setColumnWidth(4, 60)  # Colonne "Pitch" : taille fixe

        self.table.cellChanged.connect(self.check_last_row)
        self.layout.addWidget(self.table)
        self.add_table_row()  # Ajouter une ligne initiale

    def create_spinbox(self, default_value, min_value, max_value):
        """Crée un QSpinBox configuré."""
        spinbox = QSpinBox()
        spinbox.setValue(default_value)
        spinbox.setMinimum(min_value)
        spinbox.setMaximum(max_value)
        spinbox.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return spinbox

    def add_table_row(self):
        """Ajoute une ligne au tableau pour une nouvelle association MIDI/paroles."""
        row_count = self.table.rowCount()
        self.table.insertRow(row_count)

        # Colonne Action : Bouton pour parcourir les fichiers MIDI
        browse_button = QPushButton("[...]")
        browse_button.clicked.connect(lambda _, row=row_count: self.browse_file(row))
        self.table.setCellWidget(row_count, 0, browse_button)

        # Colonne Fichier MIDI
        self.table.setItem(row_count, 1, QTableWidgetItem(""))

        # Colonne Paroles
        self.table.setItem(row_count, 2, QTableWidgetItem(""))

        # Colonne Durée : SpinBox
        duration_spinbox = QSpinBox()
        duration_spinbox.setMinimum(1)
        duration_spinbox.setMaximum(10)
        duration_spinbox.setValue(3)  # Par défaut : 3 secondes
        self.table.setCellWidget(row_count, 3, duration_spinbox)

        # Colonne Pitch : SpinBox
        pitch_spinbox = QSpinBox()
        pitch_spinbox.setMinimum(-12)
        pitch_spinbox.setMaximum(12)
        pitch_spinbox.setValue(0)  # Par défaut : 0 demi-ton
        self.table.setCellWidget(row_count, 4, pitch_spinbox)

    def browse_file(self, row):
        """Ouvre une boîte de dialogue pour sélectionner un fichier MIDI."""
        file_dialog = QFileDialog()
        file_dialog.setNameFilters(["Fichiers MIDI (*.mid *.midi)", "Tous les fichiers (*)"])
        if file_dialog.exec():
            selected_file = file_dialog.selectedFiles()[0]
            self.table.setItem(row, 1, QTableWidgetItem(selected_file))  # Colonne Fichier MIDI

    def check_last_row(self):
        """Vérifie si la dernière ligne est remplie et ajoute une nouvelle ligne si nécessaire."""
        row_count = self.table.rowCount()
        if row_count == 0:
            return

        last_row_filled = all(
            self.table.item(row_count - 1, col) and self.table.item(row_count - 1, col).text().strip()
            for col in range(1, 3)  # Vérifie les colonnes "Fichier MIDI" et "Ligne de paroles"
        )

        if last_row_filled:
            self.add_table_row()

    def setup_buttons(self):
        """Boutons pour lancer le pipeline."""
        buttons_layout = QHBoxLayout()

        self.add_row_button = QPushButton("Ajouter une ligne")
        self.add_row_button.clicked.connect(self.add_table_row)
        buttons_layout.addWidget(self.add_row_button)

        self.run_pipeline_button = QPushButton("Lancer le pipeline")
        self.run_pipeline_button.clicked.connect(self.run_pipeline)
        buttons_layout.addWidget(self.run_pipeline_button)

        self.layout.addLayout(buttons_layout)

    def get_pipeline_data(self):
        """Récupère les paramètres globaux et les associations MIDI/paroles."""
        # Paramètres globaux
        global_params = {
            "replicate_api_token": self.replicate_api_input.text().strip(),
            "rvc_model": self.rvc_voice_combo.currentText(),
            "custom_rvc_model_url": self.custom_rvc_url_input.text().strip() if self.rvc_voice_combo.currentText() == "CUSTOM" else None,
            "output_file": self.output_file_input.text().strip(),
        }

        # Associations MIDI/paroles
        associations = []
        for row in range(self.table.rowCount()):
            # Récupérer chaque cellule ou widget pour la ligne
            midi_item = self.table.item(row, 1)  # Colonne MIDI
            lyrics_item = self.table.item(row, 2)  # Colonne Paroles
            duration_widget = self.table.cellWidget(row, 3)  # Spinbox Durée
            pitch_widget = self.table.cellWidget(row, 4)  # Spinbox Pitch

            # Vérifier si toutes les données nécessaires sont présentes et valides
            if (
                midi_item and midi_item.text().strip() and
                lyrics_item and lyrics_item.text().strip() and
                duration_widget and pitch_widget
            ):
                associations.append((
                    midi_item.text().strip(),  # Chemin du fichier MIDI
                    lyrics_item.text().strip(),  # Ligne de paroles
                    duration_widget.value(),  # Durée (int)
                    pitch_widget.value()  # Pitch (int)
                ))

        return global_params, associations

    def check_and_add_row(self):
        """Vérifie si la dernière ligne est remplie et ajoute une nouvelle ligne si nécessaire."""
        last_row = self.table.rowCount() - 1
        if last_row >= 0:
            midi_item = self.table.item(last_row, 1)  # Colonne Fichier MIDI
            lyrics_item = self.table.item(last_row, 2)  # Colonne Paroles
            duration_widget = self.table.cellWidget(last_row, 3)  # Colonne Durée
            pitch_widget = self.table.cellWidget(last_row, 4)  # Colonne Pitch

            if (
                midi_item and midi_item.text().strip() and
                lyrics_item and lyrics_item.text().strip() and
                duration_widget and pitch_widget
            ):
                # Ajouter une nouvelle ligne si la dernière est remplie
                self.add_table_row()

    def generate_lyrics_file(self):
        """
        Génère un fichier temporaire contenant les lignes de paroles saisies dans l'UI.
        """
        lyrics_file = "lignes_UI.txt"
        with open(lyrics_file, "w", encoding="utf-8") as file:
            for row in range(self.table.rowCount()):
                lyrics_item = self.table.item(row, 1)  # Colonne "Ligne de paroles"
                if lyrics_item and lyrics_item.text().strip():
                    file.write(lyrics_item.text().strip() + "\n")
        return lyrics_file

    def run_pipeline(self):
        """Lance le pipeline avec les données récupérées."""
        global_params, associations = self.get_pipeline_data()

        if not associations:
            self.log("Aucune association MIDI/paroles valide trouvée.", "ERREUR")
            return

        replicate_api_token = global_params.get("replicate_api_token")
        custom_rvc_model_url = global_params.get("custom_rvc_model_url")

        # Vérifiez si custom_rvc_model_url est défini et valide
        if not custom_rvc_model_url:
            self.log("URL ou chemin du modèle RVC personnalisée non spécifié.", "ERREUR")
            return

        # Vérifiez si l'URL ou le fichier est valide
        if not os.path.exists(custom_rvc_model_url) and not custom_rvc_model_url.startswith("http"):
            self.log("Modèle RVC personnalisé non trouvé ou URL invalide.", "ERREUR")
            return

        # Configuration de la clé API Replicate
        if replicate_api_token:
            os.environ["REPLICATE_API_TOKEN"] = replicate_api_token
            self.log("Clé REPLICATE_API_TOKEN configurée avec succès.", "INFO")
        else:
            self.log("Aucune clé REPLICATE_API_TOKEN trouvée.", "ATTENTION")

        self.log("Lancement du pipeline...")

        try:
            all_wave_files = []
            for midi_file, lyrics, duration, pitch in associations:
                wave_file = self.pipeline_runner.run_pipeline(
                    midi_file=midi_file,
                    lyrics=lyrics,
                    duration=duration,
                    pitch=pitch,
                    custom_rvc_model_url=custom_rvc_model_url,
                )
                all_wave_files.append(wave_file)
            
            # Concaténez les fichiers audio générés
            output_file = global_params["output_file"]
            
            # Uniformisations des différents waves
            uniform_wave_files = []
            for wave_file in all_wave_files:
                uniform_file = wave_file.replace(".wav", "_uniform.wav")
                convert_to_uniform_format(wave_file, uniform_file)
                uniform_wave_files.append(uniform_file)

            # Concaténation avec les fichiers uniformisés
            concatenate_audio(output_file, uniform_wave_files)
            
            # Nettoyage final
            clean_all_temporary_files(len(uniform_wave_files))
            
            self.log(f"Pipeline terminé avec succès. Fichier final : {output_file}", "RÉUSSI")
        
        except Exception as e:
            self.log(f"Erreur lors de l'exécution du pipeline : {str(e)}", "ERREUR")

def main():
    app = QApplication([])
    main_window = MainWindow(logger=print, pipeline_runner=None)
    main_window.show()
    app.exec()


if __name__ == "__main__":
    main()
