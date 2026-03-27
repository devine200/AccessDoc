import logging
import shutil
from pathlib import Path

from django.conf import settings
from django.db.models.signals import pre_delete
from django.dispatch import receiver

from items.models import PublishedItem

logger = logging.getLogger(__name__)


@receiver(
    pre_delete,
    sender=PublishedItem,
    dispatch_uid="items.remove_published_item_artifacts",
)
def remove_published_item_artifacts(
    sender, instance: PublishedItem, **kwargs
) -> None:
    """
    Remove the Docusaurus build snapshot (``DOCUSAURUS_BUILDS_ROOT/<upload id>/``) and
    the uploaded PDF **before** the row is removed.

    ``pre_delete`` is used so ``FileField`` paths and storage are still reliable (see
    Django docs on deleting ``FileField`` files). ``demo_docs/`` staging is unchanged.
    """
    pk = str(instance.pk)
    builds_root = Path(settings.DOCUSAURUS_BUILDS_ROOT).resolve()
    build_dir = (builds_root / pk).resolve()
    if build_dir.is_dir() and str(build_dir).startswith(str(builds_root)):
        try:
            shutil.rmtree(build_dir)
        except OSError as exc:
            logger.warning(
                "Could not remove viewer build directory %s: %s", build_dir, exc
            )

    file_name = getattr(instance.source_file, "name", "") or ""
    if file_name:
        try:
            instance.source_file.delete(save=False)
        except OSError as exc:
            logger.warning(
                "Could not remove uploaded source file for %s: %s", pk, exc
            )
        except Exception as exc:
            logger.warning(
                "Storage error removing source file for %s: %s", pk, exc
            )
