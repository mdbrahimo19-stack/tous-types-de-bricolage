"""Données de départ pour le MVP : 14 catégories + wilayas (Alger, Oran, Constantine,
Blida, Tizi Ouzou) et leurs communes.

Idempotent : peut être relancé sans créer de doublons.
    python manage.py seed_base

NB : la liste des communes de Tizi Ouzou (67 au total) n'est pas garantie exhaustive
à 100 % ici — à vérifier auprès de la source officielle (wilaya) avant la mise en
production.
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

# Wilaya d'Oran (31) — 26 communes officielles.
ORAN_COMMUNES = [
    "Oran", "Aïn El Bia", "Aïn El Kerma", "Aïn El Turk", "Arzew", "Ben Freha",
    "Bir El Djir", "Boufatis", "Bousfer", "Boutlélis", "El Ançor", "El Braya",
    "El Kerma", "Es Senia", "Gdyel", "Hassi Ben Okba", "Hassi Bounif",
    "Hassi Mefsoukh", "Hassiane Ettoual", "Mers El Hadjadj", "Mers El Kébir",
    "Misserghin", "Oued Tlelat", "Sidi Benyebka", "Sidi Chami", "Tafraoui",
]

# Wilaya de Constantine (25) — 12 communes officielles.
CONSTANTINE_COMMUNES = [
    "Constantine", "Aïn Abid", "Aïn Smara", "Beni Hamiden", "Didouche Mourad",
    "El Khroub", "Hamma Bouziane", "Ibn Badis", "Ibn Ziad", "Messaoud Boudjriou",
    "Ouled Rahmoune", "Zighoud Youcef",
]

# Wilaya de Blida (09) — 25 communes officielles.
BLIDA_COMMUNES = [
    "Blida", "Chebli", "Bouinan", "Oued Alleug", "Ouled Yaïch", "Chréa",
    "El Affroun", "Chiffa", "Hammam Melouane", "Benkhelil", "Soumaa", "Mouzaia",
    "Souhane", "Meftah", "Ouled Slama", "Boufarik", "Larbaâ", "Oued Djer",
    "Beni Tamou", "Bouarfa", "Beni Mered", "Bougara", "Guerouaou", "Aïn Romana",
    "Djebabra",
]

# Wilaya de Tizi Ouzou (15) — 55/67 communes vérifiées (voir note en tête de fichier).
TIZI_OUZOU_COMMUNES = [
    "Tizi Ouzou", "Tizi Rached", "Abi Youcef", "Aghribs", "Agouni Gueghrane",
    "Aïn El Hammam", "Aïn Zaouia", "Aït Aïcha", "Aït Aïssa Mimoun", "Aït Aïssi",
    "Aït Aggouacha", "Aït Bouaddou", "Aït Boumahdi", "Aït Chafâa", "Aït Khellili",
    "Aït Mahmoud", "Aït Oumalou", "Aït Toudert", "Aït Yahia", "Aït Yahia Moussa",
    "Akbil", "Akerrou", "Assi Youcef", "Azazga", "Azeffoun", "Beni Douala",
    "Beni Yenni", "Beni Zmenzer", "Boghni", "Boudjima", "Bounouh", "Bouzeguène",
    "Draâ Ben Khedda", "Draâ El Mizan", "Freha", "Frikat", "Iboudraren", "Idjeur",
    "Iferhounène", "Ifigha", "Iflissen", "Illilten", "Illoula Oumalou", "Mekla",
    "Souama", "Ouacif", "Ouadhia", "Tizi N'Tleta", "Ouaguenoun", "Timizart",
    "Tigzirt", "Mizrana", "Yakouren", "Yatafen", "Zekri",
]

# (nom wilaya, code, communes) pour les wilayas au-delà d'Alger.
EXTRA_WILAYAS = [
    ("31", "Oran", "وهران", ORAN_COMMUNES),
    ("25", "Constantine", "قسنطينة", CONSTANTINE_COMMUNES),
    ("09", "Blida", "البليدة", BLIDA_COMMUNES),
    ("15", "Tizi Ouzou", "تيزي وزو", TIZI_OUZOU_COMMUNES),
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

        summary_parts = [f"communes Alger: +{created_communes} (total {wilaya.communes.count()})"]

        for code, name_fr, name_ar, communes in EXTRA_WILAYAS:
            w, _ = Wilaya.objects.update_or_create(
                code=code, defaults={"name_fr": name_fr, "name_ar": name_ar, "is_active": True}
            )
            created_w = 0
            for fr in communes:
                _, created = Commune.objects.get_or_create(wilaya=w, name_fr=fr)
                created_w += int(created)
            summary_parts.append(f"communes {name_fr}: +{created_w} (total {w.communes.count()})")

        self.stdout.write(self.style.SUCCESS(
            f"OK · catégories: +{created_cats} (total {Category.objects.count()}) · "
            + " · ".join(summary_parts)
        ))

    @staticmethod
    def _slug(name):
        from django.utils.text import slugify
        return slugify(name)
