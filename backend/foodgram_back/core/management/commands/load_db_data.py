import csv
import os

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.utils import IntegrityError
from recipes.models import Ingredient, Tag


class Command(BaseCommand):

    def handle(self, *args, **options):

        path = os.path.join(
            settings.BASE_DIR, 'data', 'ingredients.csv'
        )
        with open(path, encoding='utf-8', newline='') as csvfile:
            for row in csv.reader(csvfile):
                try:
                    obj = Ingredient(name=row[0], measurement_unit=row[1])
                    obj.save()
                except IntegrityError:
                    pass

        TAGS = [
            ('breakfast', 'br', '#eb5284'),
            ('lunch', 'ln', '#008080'),
            ('dinner', 'dn', '#386087')
        ]

        for tag in TAGS:
            try:
                obj = Tag(
                    name=tag[0],
                    slug=tag[1],
                    color=tag[2]
                )
                obj.save()
            except IntegrityError:
                pass

        self.stdout.write(self.style.NOTICE('successfully loaded'))
