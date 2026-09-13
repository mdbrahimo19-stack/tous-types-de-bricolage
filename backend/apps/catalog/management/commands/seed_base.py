"""Données de départ pour le MVP : 10 catégories + wilaya d'Alger et ses communes.

Idempotent : peut être relancé sans créer de doublons.
    python manage.py seed_base
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.catalog.models import Category
from apps.locations.models import Commune, Wilaya

CATEGORIES = [
    # (name_fr, name_ar, icon, unit, price_min, price_max)
    ("Plomberie", "سباكة", "pipe", "forfait", 1500, 8000),
    ("Électricité", "كهرباء", "bolt", "forfait", 1500, 10000),
    ("Climatisation", "تكييف", "air-conditioning", "forfait", 2000, 15000),
    ("Peinture", "دهن", "paint-roller", "m2", 200, 600),
    ("Maçonnerie", "بناء", "wall", "jour", 4000, 9000),
    ("Menuiserie", "نجارة", "hammer", "forfait", 3000, 20000),
    ("Réparation électroménager", "تصليح أجهزة كهرومنزلية", "washing-machine", "forfait", 1000, 7000),
    ("Nettoyage", "تنظيف", "spray", "forfait", 2000, 12000),
    ("Jardinage", "بستنة", "plant", "forfait", 2000, 10000),
    ("Déménagement", "نقل الأثاث", "truck", "forfait", 5000, 30000),
    ("Mécanicien auto", "ميكانيكي سيارات", "car-wrench", "forfait", 2000, 15000),
    ("Électricien auto", "كهربائي سيارات", "car-battery", "forfait", 1500, 10000),
    ("Maintenance informatique", "صيانة معلوماتية", "computer", "forfait", 1000, 8000),
    ("Réparateur TV", "تصليح تلفزيون", "tv", "forfait", 1500, 6000),
]

# Sous-ensemble de communes d'Alger (wilaya 16) pour amorcer la bêta.
ALGER_COMMUNES = [
    ("Alger-Centre", "الجزائر الوسطى"), ("Bab El Oued", "باب الوادي"),
    ("El Harrach", "الحراش"), ("Hussein Dey", "حسين داي"),
    ("Bir Mourad Raïs", "بئر مراد رايس"), ("El Biar", "الأبيار"),
    ("Bab Ezzouar", "باب الزوار"), ("Dar El Beïda", "الدار البيضاء"),
    ("Kouba", "القبة"), ("Bourouba", "بوروبة"),
    ("Bologhine", "بولوغين"), ("Birkhadem", "بئر خادم"),
    ("Chéraga", "الشراقة"), ("Draria", "درارية"),
    ("Rouiba", "الرويبة"), ("Baraki", "براقي"),
]


class Command(BaseCommand):
    help = "Crée les 10 catégories MVP et la wilaya d'Alger avec ses communes."

    @transaction.atomic
    def handle(self, *args, **options):
        created_cats = 0
        for order, (fr, ar, icon, unit, pmin, pmax) in enumerate(CATEGORIES, start=1):
            _, created = Category.objects.update_or_create(
                slug=self._slug(fr),
                defaults={
                    "name_fr": fr, "name_ar": ar, "icon": icon, "unit": unit,
                    "price_min": pmin, "price_max": pmax, "order": order, "is_active": True,
                    "parent": None,
                },
            )
            created_cats += int(created)

        wilaya, _ = Wilaya.objects.update_or_create(
            code="16", defaults={"name_fr": "Alger", "name_ar": "الجزائر", "is_active": True}
        )
        created_communes = 0
        for fr, ar in ALGER_COMMUNES:
            _, created = Commune.objects.get_or_create(
                wilaya=wilaya, name_fr=fr, defaults={"name_ar": ar}
            )
            created_communes += int(created)

        self.stdout.write(self.style.SUCCESS(
            f"OK · catégories: +{created_cats} (total {Category.objects.count()}) · "
            f"communes Alger: +{created_communes} (total {wilaya.communes.count()})"
        ))

    @staticmethod
    def _slug(name):
        from django.utils.text import slugify
        return slugify(name)
