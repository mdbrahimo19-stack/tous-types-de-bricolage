"""Site vitrine en anglais (troisième langue, à côté du français et de l'arabe)."""

SHIELD = "M12 3l7 3v6c0 4.5-3 7.5-7 9-4-1.5-7-4.5-7-9V6zM9 12l2 2 4-4"
STAR = "M12 3l2.6 5.6 6 .7-4.5 4.1 1.2 6L12 16.6 6.7 19.4l1.2-6L3.4 9.3l6-.7z"
CASH = "M3 7h18v10H3zM12 12h.01M6 10v4M18 10v4"

SITE_TEXT_EN = {
    "tagline": "Find the right professional, near you",
    "meta": "BRICOOL connects clients with verified professionals in Algeria: plumbing, electrical work, painting, "
            "air conditioning and more. Free quotes, pay at the end.",
    "nav_label": "Menu", "nav_how": "How it works", "nav_apps": "The app", "nav_faq": "Questions",
    "eyebrow": "Verified professionals all over Algeria",
    "h1": "Find the right professional, near you",
    "lead": "Describe your problem: BRICOOL automatically sends it to the nearest verified professionals. "
            "Compare their quotes, chat with them, and only pay once the work is done.",
    "dl_client": "Download BRICOOL", "dl_client_sub": "I am looking for a professional",
    "space_client": "Client space", "space_pro": "Professional space",
    "dl_pro": "I am a professional", "dl_pro_sub": "Same app, professional space",
    "mock_q": "What do you need?", "mock_card": "Describe your problem",
    "mock_card_sub": "Nearby professionals receive your request.",
    "how_title": "How it works", "how_sub": "Three steps, no searching or calling at random.",
    "steps": [
        {"t": "Describe the need", "p": "A leak, a socket, some painting: a few words and a photo are enough."},
        {"t": "Receive quotes", "p": "The nearest verified professionals send you their price and timing."},
        {"t": "Choose, pay at the end", "p": "You see their reviews and profile, you choose, and you pay "
                                            "in cash once the work is finished."},
    ],
    "apps_title": "One app, two spaces",
    "apps_sub": "When you first open the app, choose your space: client or professional. You can switch at any time.",
    "client_for": "For individuals",
    "client_points": ["Post a request in 1 minute", "Compare quotes and reviews",
                      "Chat with the professional in the app"],
    "pro_for": "For professionals and service providers",
    "pro_points": ["Receive requests near you", "Send your quotes in seconds",
                   "Show your work and your reviews"],
    "trust_title": "Trust comes first",
    "trust": [
        {"d": SHIELD, "t": "Verified professionals",
         "p": "Every professional is checked by the BRICOOL team before receiving requests."},
        {"d": STAR, "t": "Real reviews", "p": "Only clients who hired the professional can leave a review."},
        {"d": CASH, "t": "Pay at the end", "p": "No payment in advance: you pay the professional when the work is done."},
    ],
    "services_title": "More than 40 services", "services_sub": "For the home, the car and everyday life.",
    "services": ["Plumbing", "Electrical work", "Painting", "Air conditioning", "Masonry", "Carpentry", "Appliances",
                 "Cleaning", "Gardening", "Moving", "Locksmith", "Tiling", "Water heaters",
                 "Security cameras", "Car mechanics"],
    "faq_title": "Frequently asked questions",
    "faq": [
        {"q": "Is BRICOOL free for clients?",
         "a": "Yes. Posting a request, receiving quotes and chatting with professionals is free."},
        {"q": "How are professionals verified?",
         "a": "The BRICOOL team checks each professional's profile before they can send quotes."},
        {"q": "How does payment work?", "a": "You pay the professional directly, in cash, at the end of the work."},
        {"q": "I am a professional: how do I join BRICOOL?",
         "a": "Download BRICOOL, choose “I am a professional”, sign up with your number and complete your profile: "
              "the team validates your account."},
        {"q": "Is my data protected?",
         "a": "Yes, in accordance with Law 18-07. Your number is only shared once a quote is accepted."},
    ],
    "privacy": "Privacy policy",
    "stats_label": "BRICOOL in numbers", "stat_artisans": "verified professionals", "stat_missions": "jobs completed",
    "stat_wilayas": "wilayas covered", "stat_rating": "average client rating",
    "promo_pro_title": "Are you a professional? Join BRICOOL",
    "promo_pro_text": "Receive requests from clients near you. When you sign up:",
    "promo_pro_points": "free points.",
    "artisans_short": "professionals", "featured_title": "Our top-rated professionals",
    "featured_sub": "Verified by BRICOOL and recommended by their clients.", "verified": "Verified",
    "missions_short": "jobs", "reviews_title": "What clients say",
    "promo_client_title": "A problem at home? BRICOOL takes care of it",
    "promo_client_text": "Free for clients. Quotes within minutes, from verified professionals near you.",
}

# Noms anglais des services (même liste que l'app, lib/l10n_en.dart), par nom français.
CATEGORY_NAMES_EN = {
    "Plomberie": "Plumbing",
    "Électricité": "Electrical work",
    "Climatisation": "Air conditioning",
    "Peinture": "Painting",
    "Maçonnerie": "Masonry",
    "Menuiserie": "Carpentry",
    "Réparation électroménager": "Appliance repair",
    "Nettoyage": "Cleaning",
    "Jardinage": "Gardening",
    "Déménagement": "Moving",
    "Mécanicien auto": "Car mechanic",
    "Électricien auto": "Car electrician",
    "Maintenance informatique": "IT maintenance",
    "Réparateur TV": "TV repair",
    "Carrelage": "Tiling",
    "Plâtrerie et faux plafond": "Plastering and false ceilings",
    "Étanchéité": "Waterproofing",
    "Pose de parquet": "Parquet flooring",
    "Vitrerie": "Glazing",
    "Serrurerie": "Locksmith",
    "Ferronnerie et soudure": "Ironwork and welding",
    "Aluminium et PVC": "Aluminium and PVC",
    "Chauffage et chaudière": "Heating and boilers",
    "Débouchage de canalisations": "Drain unblocking",
    "Lavage de citernes": "Water tank cleaning",
    "Décoration intérieure": "Interior decoration",
    "Montage de meubles": "Furniture assembly",
    "Tapisserie et rideaux": "Upholstery and curtains",
    "Entretien de piscine": "Pool maintenance",
    "Caméras de surveillance": "Security cameras",
    "Antenne et parabole": "Antennas and satellite dishes",
    "Réparation de téléphones": "Phone repair",
    "Désinsectisation et dératisation": "Pest control",
    "Nettoyage de canapés et tapis": "Sofa and carpet cleaning",
    "Garde d'enfants": "Childcare",
    "Aide à domicile": "Home help",
    "Cours particuliers": "Private lessons",
    "Coiffure à domicile": "Home hairdressing",
    "Cuisinier et traiteur": "Cook and caterer",
    "Cuisinière à domicile": "Home cook",
    "Pâtissière (gâteaux et gâteaux traditionnels)": "Pastry maker (cakes and traditional cakes)",
    "Pâtisserie traditionnelle (makrout, baklawa, griwech…)": "Traditional pastries (makrout, baklava, griwech…)",
    "Couturière": "Seamstress",
    "Photographe": "Photographer",
    "DJ pour fêtes et mariages": "DJ for parties and weddings",
    "Location de tables et chaises pour fêtes": "Table and chair rental for parties",
    "Location de tenues de fête (robes, caftans, costumes)": "Party outfit rental (dresses, caftans, suits)",
    "Transport de marchandises": "Goods transport",
    "Carrosserie auto": "Car bodywork",
    "Lavage auto à domicile": "Car wash at home",
    "Dépannage et remorquage": "Breakdown and towing",
}


def category_name(obj, lang):
    """Nom d'une catégorie (ou wilaya) dans la langue du site ; anglais : table ci-dessus, sinon français."""
    if obj is None:
        return ""
    if lang == "ar":
        return obj.name_ar or obj.name_fr
    if lang == "en":
        return CATEGORY_NAMES_EN.get(obj.name_fr, obj.name_fr)
    return obj.name_fr
