from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError

from dcim.models import DeviceType
from dcim.svg.front_panel import FrontPanelRenderer, build_front_svg_filename


class Command(BaseCommand):
    help = "Generate flat front-panel SVGs for all DeviceTypes."

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true", help="Regenerate even if SVG exists.")
        parser.add_argument("--only", help="Limit to a single DeviceType id.")
        parser.add_argument("--dry-run", action="store_true", help="Do not write files or update models.")

    def handle(self, *args, **options):
        force = options["force"]
        only = options.get("only")
        dry_run = options["dry_run"]

        qs = DeviceType.objects.all()
        if only:
            qs = qs.filter(id=only)
            if not qs.exists():
                raise CommandError(f"DeviceType {only} not found")

        renderer = FrontPanelRenderer()
        created = updated = skipped = errors = 0

        for dt in qs:
            try:
                res = renderer.render(dt)
                filename = build_front_svg_filename(dt)
                should_write = force or not dt.front_svg
                if dry_run:
                    skipped += 1
                    continue
                if should_write:
                    content = ContentFile(res.svg.encode("utf-8"))
                    dt.front_svg.save(filename, content, save=False)
                    dt.save(update_fields=["front_svg"])
                    if dt.front_svg and force:
                        updated += 1
                    else:
                        created += 1
                else:
                    skipped += 1
            except Exception as exc:  # noqa
                errors += 1
                self.stderr.write(f"Error on {dt}: {exc}")

        self.stdout.write(
            f"Summary: created={created}, updated={updated}, skipped={skipped}, errors={errors}"
        )
