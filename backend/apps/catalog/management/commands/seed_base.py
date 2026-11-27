"""Données de départ : 44 catégories + wilayas (Alger, Oran, Constantine,
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
    # --- catalogue élargi (prix indicatifs à compléter dans l'admin) ---------------
    # bâtiment et second œuvre
    ("Carrelage", "تبليط", "tiles", "m2", None, None),
    ("Plâtrerie et faux plafond", "جبس وأسقف مستعارة", "ceiling", "m2", None, None),
    ("Étanchéité", "عزل مائي", "roof", "m2", None, None),
    ("Pose de parquet", "تركيب الباركي", "floor", "m2", None, None),
    ("Vitrerie", "زجاج", "window", "forfait", None, None),
    ("Serrurerie", "أقفال", "key", "forfait", None, None),
    ("Ferronnerie et soudure", "حدادة ولحام", "welding", "forfait", None, None),
    ("Aluminium et PVC", "ألمنيوم وبي في سي", "door", "forfait", None, None),
    ("Chauffage et chaudière", "تدفئة وسخانات", "heater", "forfait", None, None),
    ("Débouchage de canalisations", "تسليك المجاري", "drain", "forfait", None, None),
    ("Lavage de citernes", "تنظيف الخزانات", "water-tank", "forfait", None, None),
    ("Décoration intérieure", "ديكور داخلي", "sofa", "forfait", None, None),
    ("Montage de meubles", "تركيب الأثاث", "cabinet", "forfait", None, None),
    ("Tapisserie et rideaux", "تنجيد وستائر", "curtains", "forfait", None, None),
    ("Entretien de piscine", "صيانة المسابح", "pool", "forfait", None, None),
    # sécurité, électronique
    ("Caméras de surveillance", "كاميرات المراقبة", "cctv", "forfait", None, None),
    ("Antenne et parabole", "هوائيات وصحون مقعرة", "satellite", "forfait", None, None),
    ("Réparation de téléphones", "تصليح الهواتف", "phone", "forfait", None, None),
    # nettoyage, hygiène
    ("Désinsectisation et dératisation", "مكافحة الحشرات والقوارض", "bug", "forfait", None, None),
    ("Nettoyage de canapés et tapis", "تنظيف الأرائك والزرابي", "carpet", "forfait", None, None),
    # services à la personne
    ("Garde d'enfants", "رعاية الأطفال", "baby", "heure", None, None),
    ("Aide à domicile", "مساعدة منزلية", "home-heart", "heure", None, None),
    ("Cours particuliers", "دروس خصوصية", "school", "heure", None, None),
    ("Coiffure à domicile", "حلاقة وتجميل في المنزل", "scissors", "forfait", None, None),
    # événements
    ("Cuisinier et traiteur", "طباخ وممون حفلات", "chef", "forfait", None, None),
    ("Cuisinière à domicile", "طباخة في المنزل", "chef", "forfait", None, None),
    ("Pâtissière (gâteaux et gâteaux traditionnels)", "صانعة الحلويات", "cake", "forfait", None, None),
    ("Couturière", "خياطة", "sewing", "forfait", None, None),
    ("Photographe", "مصور", "camera", "forfait", None, None),
    # transport, automobile
    ("Transport de marchandises", "نقل البضائع", "van", "forfait", None, None),
    ("Carrosserie auto", "هيكلة السيارات", "car-door", "forfait", None, None),
    ("Lavage auto à domicile", "غسل السيارات في المنزل", "car-wash", "forfait", None, None),
    ("Dépannage et remorquage", "سحب وإسعاف السيارات", "tow-truck", "forfait", None, None),
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

# Wilaya de Tizi Ouzou (15) — 65/67 communes vérifiées (voir note en tête de fichier).
TIZI_OUZOU_COMMUNES = [
    "Tizi Ouzou", "Tizi Rached", "Abi Youcef", "Aghribs", "Agouni Gueghrane",
    "Aïn El Hammam", "Aïn Zaouia", "Aït Aïcha", "Aït Aïssa Mimoun", "Aït Aïssi",
    "Aït Aggouacha", "Aït Bouaddou", "Aït Boumahdi", "Aït Chafâa", "Aït Khellili",
    "Aït Mahmoud", "Aït Oumalou", "Aït Toudert", "Aït Yahia", "Aït Yahia Moussa",
    "Akbil", "Akerrou", "Assi Youcef", "Azazga", "Azeffoun", "Beni Douala",
    "Beni Yenni", "Beni Zmenzer", "Boghni", "Boudjima", "Bounouh", "Bouzeguène",
    "Draâ Ben Khedda", "Draâ El Mizan", "Freha", "Frikat", "Iboudraren", "Idjeur",
    "Iferhounène", "Ifigha", "Iflissen", "Illilten", "Illoula Oumalou",
    "Larbaâ Nath Irathen", "Mâatkas", "Makouda", "Mechtras", "Mekla", "Mizrana",
    "M'Kira", "Ouacif", "Ouadhia", "Ouaguenoun", "Sidi Nâamane", "Souama",
    "Souk El Tenine", "Tadmaït", "Tigzirt", "Timizart", "Tirmitine",
    "Tizi Ghenif", "Tizi N'Tleta", "Yakouren", "Yatafen", "Zekri",
]

# Wilaya d'Annaba (23) — 12 communes officielles (liste complète et vérifiée).
ANNABA_COMMUNES = [
    "Annaba", "Aïn Berda", "Berrahal", "Chetaïbi", "Cheurfa", "El Bouni",
    "El Hadjar", "El Eulma (Annaba)", "Oued El Aneb", "Seraïdi", "Sidi Amar",
    "Treat",
]

# Wilaya de Béjaïa (06) — 52 communes officielles (liste quasi-complète, ~53 récoltées).
BEJAIA_COMMUNES = [
    "Béjaïa", "Adekar", "Aït Mellikeche", "Aït Smaïl", "Akbou", "Akfadou",
    "Amalou", "Amizour", "Aokas", "Barbacha", "Beni Djellil", "Beni Ksila",
    "Beni Maouche", "Boudjellil", "Bouhamza", "Boukhelifa", "Chellata",
    "Chemini", "Darguina", "Draâ El Kaïd", "El Kseur", "Fenaïa Ilmaten",
    "Feraoun", "Ighil Ali", "Ighram", "Kendira", "Kherrata", "Leflaye",
    "Letnayen", "M'cisna", "Melbou", "Mouzaïa", "Oued Ghir", "Ouzellaguen",
    "Seddouk", "Semaoun", "Sidi Aïch", "Sidi Ayad", "Souk El Ténine",
    "Souk Oufella", "Tala Hamza", "Tamokra", "Tamridjet", "Taourirt Ighil",
    "Taskriout", "Tazmalt", "Tibane", "Tichy", "Tifra", "Timezrit",
    "Tinebdar", "Tizi N'Berber", "Toudja",
]

# Wilaya de Sétif (19) — 60 communes officielles (liste quasi-complète, ~65 récoltées ;
# à vérifier avant production en cas de doublons/variantes orthographiques).
SETIF_COMMUNES = [
    "Sétif", "Aïn Abessa", "Aïn Arnat", "Aïn Azel", "Aïn El Kebira",
    "Aïn Lahdjar", "Aïn Legradj", "Aïn Oulmène", "Aïn Roua", "Aïn Sebt",
    "Aït Naoual Mezada", "Aït Tizi", "Amoucha", "Babor", "Bazer Sakhra",
    "Beidha Bordj", "Belaa", "Beni Aziz", "Beni Chebana", "Beni Fouda",
    "Beni Hocine", "Beni Mouhli", "Beni Ourtilane", "Bir El Arch",
    "Bir Haddada", "Bouandas", "Bouferoudj", "Bougaa", "Bousselam",
    "Boutaleb", "Dehamcha", "Djemila", "Draa Kebila", "El Eulma",
    "El Ouldja", "El Ouricia", "Guellal", "Guelta Zerka", "Guenzet",
    "Guidjel", "Hamma", "Hammam Guergour", "Hammam Soukhna", "Harbil",
    "Ksar El Abtal", "Maaouia", "Maoklane", "Mezloug", "Oued El Barad",
    "Oued Sebt", "Ouled Addouane", "Ouled Ayad", "Ouled Sabor",
    "Ouled Si Ahmed", "Ouled Tebben", "Oum Ladjoul", "Rosfa", "Salah Bey",
    "Serdj El Ghoul", "Tachouda", "Talaifacene", "Taya", "Tella",
    "Tizi N'Bechar",
]

# Wilaya de Batna (05) — 61 communes officielles (liste quasi-complète, ~62 récoltées).
BATNA_COMMUNES = [
    "Batna", "Abdelkader Azil", "Aïn Djasser", "Aïn Touta", "Aïn Yagout",
    "Amentane", "Arris", "Ben Foudhala El Hakania", "Bitam", "Boulhilat",
    "Boumagueur", "Boumia", "Bouzina", "Chemora", "Chir", "Djerma", "Djezar",
    "El Hassi", "El Madher", "Fesdis", "Foum Toub", "Ghassira", "Gosbat",
    "Guigba", "Hidoussa", "Ichmoul", "Inoughissen", "Kimmel", "Ksar Bellezma",
    "Larbaâ", "Lazrou", "Lemsane", "M'doukal", "Maafa", "Menaa", "Merouana",
    "N'Gaous", "Nara", "Oued Chaaba", "Oued El Ma", "Oued Taga", "Ouled Ammar",
    "Ouled Aouf", "Ouled Fadel", "Ouled Sellam", "Ouled Si Slimane",
    "Ouyoun El Assafir", "Rahbat", "Ras El Aioun", "Sefiane", "Seggana",
    "Seriana", "T'Kout", "Talkhamt", "Taxlent", "Tazoult", "Teniet El Abed",
    "Tighanimine", "Tigherghar", "Timgad", "Zana El Beida",
]

# Wilaya d'Oum El Bouaghi (04) — 29 communes officielles (liste complète).
OUM_EL_BOUAGHI_COMMUNES = [
    "Oum El Bouaghi", "Aïn Babouche", "Aïn Beïda", "Aïn Diss", "Aïn Fakroun",
    "Aïn Kercha", "Aïn M'lila", "Aïn Zitoun", "Behir Chergui", "Berriche",
    "Bir Chouhada", "Dhalâa", "El Amiria", "El Belala", "El Djazia",
    "El Fedjoudj Boughrara Saoudi", "El Harmilia", "Fkirina", "Hanchir Toumghani",
    "Ksar Sbahi", "Meskiana", "Oued Nini", "Ouled Gacem", "Ouled Hamla",
    "Ouled Zouaï", "Rahia", "Sigus", "Souk Naamane", "Zorg",
]

# Wilaya de Skikda (21) — 38 communes officielles (liste complète et vérifiée).
SKIKDA_COMMUNES = [
    "Skikda", "Aïn Bouziane", "Aïn Charchar", "Aïn Kechra", "Aïn Zouit",
    "Azzaba", "Bekkouche Lakhdar", "Bin El Ouiden", "Ben Azzouz", "Beni Bechir",
    "Beni Oulbane", "Beni Zid", "Bouchtata", "Cheraïa", "Collo",
    "Djendel Saadi Mohamed", "El Ghedir", "El Hadaiek", "El Harrouch",
    "El Marsa", "Emdjez Edchich", "Es Sebt", "Filfila", "Hamadi Krouma",
    "Kanoua", "Kerkera", "Kheneg Mayoum", "Oued Zehour", "Ouldja Boulballout",
    "Ouled Attia", "Ouled Hbaba", "Oum Toub", "Ramdane Djamel",
    "Salah Bouchaour", "Sidi Mezghiche", "Tamalous", "Zerdaza", "Zitouna",
]

# Wilaya de Tlemcen (13) — 53 communes officielles (liste complète).
TLEMCEN_COMMUNES = [
    "Tlemcen", "Aïn Fetah", "Aïn Fezza", "Aïn Ghoraba", "Aïn Kebira",
    "Aïn Nehala", "Aïn Tallout", "Aïn Youcef", "Akid Abbes", "Amieur",
    "Azaïls", "Bab El Assa", "Beni Bahdel", "Beni Boussaïd", "Beni Khellad",
    "Beni Mester", "Beni Ouarsous", "Beni Semiel", "Beni Snous", "Bensekrane",
    "Bouhlou", "Chetouane", "Dar Yaghmouracene", "Djebala", "El Aricha",
    "El Bouihi", "El Fehoul", "El Gor", "Fellaoucene", "Ghazaouet",
    "Hammam Boughrara", "Hennaya", "Honaïne", "Maghnia", "Mansourah",
    "Marsa Ben M'Hidi", "MSirda Fouaga", "Nedroma", "Oued Lakhdar",
    "Ouled Mimoun", "Ouled Riyah", "Remchi", "Sabra", "Sebaa Chioukh",
    "Sebdou", "Sidi Abdelli", "Sidi Djillali", "Sidi Medjahed", "Souahlia",
    "Souani", "Souk Tlata", "Terny Beni Hdiel", "Tienet",
]

# Wilaya de Mostaganem (27) — 32 communes officielles (liste complète et vérifiée).
MOSTAGANEM_COMMUNES = [
    "Mostaganem", "Abdelmalek Ramdane", "Achaacha", "Aïn Boudinar",
    "Aïn Sidi Cherif", "Aïn Tedles", "Aïn Nouïssy", "Bouguirat", "El Hassiane",
    "Fornaka", "Hadjadj", "Hassi Mameche", "Khadra", "Kheireddine",
    "Mansourah", "Mazagran", "Mesra", "Nekmaria", "Oued El Kheir",
    "Ouled Boughalem", "Ouled Maallah", "Safsaf", "Sayada", "Sidi Ali",
    "Sidi Belattar", "Sidi Lakhdar", "Sirat", "Souaflia", "Sour", "Stidia",
    "Tazgait", "Touahria",
]

# (nom wilaya, code, communes) pour les wilayas au-delà d'Alger.
EXTRA_WILAYAS = [
    ("31", "Oran", "وهران", ORAN_COMMUNES),
    ("25", "Constantine", "قسنطينة", CONSTANTINE_COMMUNES),
    ("09", "Blida", "البليدة", BLIDA_COMMUNES),
    ("15", "Tizi Ouzou", "تيزي وزو", TIZI_OUZOU_COMMUNES),
    ("19", "Sétif", "سطيف", SETIF_COMMUNES),
    ("05", "Batna", "باتنة", BATNA_COMMUNES),
    ("23", "Annaba", "عنابة", ANNABA_COMMUNES),
    ("06", "Béjaïa", "بجاية", BEJAIA_COMMUNES),
    ("04", "Oum El Bouaghi", "أم البواقي", OUM_EL_BOUAGHI_COMMUNES),
    ("21", "Skikda", "سكيكدة", SKIKDA_COMMUNES),
    ("13", "Tlemcen", "تلمسان", TLEMCEN_COMMUNES),
    ("27", "Mostaganem", "مستغانم", MOSTAGANEM_COMMUNES),
]


class Command(BaseCommand):
    help = "Crée ou met à jour les catégories et les wilayas avec leurs communes."

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
