import shutil
import tempfile

from django.conf import settings
from django.test.runner import DiscoverRunner


class LanceurTests(DiscoverRunner):
    """Sans argument, `python manage.py test` cherche les tests dans backend/.

    Les documents déposés pendant les tests vont dans un dossier temporaire, effacé à la fin.
    """

    def build_suite(self, test_labels=None, **kwargs):
        if not test_labels:
            test_labels = [str(settings.BACKEND_DIR)]
            self.top_level = str(settings.BACKEND_DIR)
        return super().build_suite(test_labels, **kwargs)

    def setup_test_environment(self, **kwargs):
        super().setup_test_environment(**kwargs)
        self.dossier_documents = tempfile.mkdtemp(prefix="atelier-tests-")
        settings.MEDIA_ROOT = self.dossier_documents

    def teardown_test_environment(self, **kwargs):
        shutil.rmtree(self.dossier_documents, ignore_errors=True)
        super().teardown_test_environment(**kwargs)
