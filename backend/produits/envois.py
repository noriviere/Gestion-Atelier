"""Arrêt des envois de fichiers trop gros dès qu'ils dépassent la limite, sans les écrire en entier sur le disque."""
from django.core.files.uploadhandler import FileUploadHandler, StopUpload

from .models import TAILLE_MAXI_DOCUMENT


class LimiteTailleEnvoi(FileUploadHandler):
    """Premier gestionnaire d'envoi : compte les octets reçus et arrête la lecture au-delà de la limite.

    La vue lit request.envoi_trop_gros pour afficher un message clair au lieu d'un fichier manquant."""

    def new_file(self, *args, **kwargs):
        super().new_file(*args, **kwargs)
        self.octets_recus = 0

    def receive_data_chunk(self, raw_data, start):
        self.octets_recus += len(raw_data)
        if self.octets_recus > TAILLE_MAXI_DOCUMENT:
            self.request.envoi_trop_gros = True
            raise StopUpload(connection_reset=False)
        return raw_data

    def file_complete(self, file_size):
        return None
