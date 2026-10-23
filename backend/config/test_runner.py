from django.conf import settings
from django.test.runner import DiscoverRunner


class LanceurTests(DiscoverRunner):
    """Sans argument, `python manage.py test` cherche les tests dans backend/."""

    def build_suite(self, test_labels=None, **kwargs):
        if not test_labels:
            test_labels = [str(settings.BACKEND_DIR)]
            self.top_level = str(settings.BACKEND_DIR)
        return super().build_suite(test_labels, **kwargs)
