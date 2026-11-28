from django.conf import settings
from django.shortcuts import render
from rest_framework import generics, serializers, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from . import privacy
from .models import User
from .otp import issue_otp, verify_otp
from .sms import SMSError
from .serializers import (
    OTPRequestSerializer,
    OTPVerifySerializer,
    UserSerializer,
    get_or_create_user_after_otp,
)


def _tokens_for(user) -> dict:
    refresh = RefreshToken.for_user(user)
    return {"access": str(refresh.access_token), "refresh": str(refresh)}


class OTPRequestView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = "otp"

    def post(self, request):
        s = OTPRequestSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        phone = s.validated_data["phone"]
        purpose = s.validated_data["purpose"]

        if purpose == "login" and not User.objects.filter(phone=phone).exists():
            return Response(
                {"detail": "Aucun compte associé à ce numéro."}, status=status.HTTP_404_NOT_FOUND
            )

        try:
            _, code = issue_otp(phone, purpose)
        except SMSError:
            return Response(
                {"detail": "Envoi du SMS impossible pour le moment. Réessayez dans quelques minutes."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        payload = {"detail": "Code envoyé par SMS.", "expires_in": settings.OTP_TTL_SECONDS}
        if settings.OTP_EXPOSE_IN_RESPONSE:
            payload["debug_code"] = code  # uniquement en DEBUG
        return Response(payload, status=status.HTTP_200_OK)


class OTPVerifyView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = "auth"

    def post(self, request):
        s = OTPVerifySerializer(data=request.data)
        s.is_valid(raise_exception=True)
        data = s.validated_data
        phone, code, purpose = data["phone"], data["code"], data["purpose"]

        # loi 18-07 : pas d'inscription sans consentement explicite (vérifié AVANT de consommer le code)
        if purpose == "registration" and not data.get("accept_privacy"):
            return Response(
                {"detail": "Vous devez accepter la politique de confidentialité pour créer un compte.",
                 "code": "privacy_required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not verify_otp(phone, code, purpose):
            return Response(
                {"detail": "Code invalide ou expiré."}, status=status.HTTP_400_BAD_REQUEST
            )

        if purpose == "login":
            try:
                user = User.objects.get(phone=phone)
            except User.DoesNotExist:
                return Response({"detail": "Compte introuvable."}, status=status.HTTP_404_NOT_FOUND)
            created = False
            if data.get("as_provider") and not user.is_provider:
                # client existant qui se connecte dans l'app BRICOOL Pro : il devient
                # aussi prestataire (profil « en attente », validé par l'équipe)
                user, _ = get_or_create_user_after_otp(phone, as_provider=True)
        else:  # registration (reset géré plus tard)
            user, created = get_or_create_user_after_otp(
                phone,
                full_name=data.get("full_name", ""),
                as_provider=data.get("as_provider", False),
                language=data.get("language", "fr"),
            )

        if not user.is_active:
            return Response({"detail": "Compte suspendu."}, status=status.HTTP_403_FORBIDDEN)

        if data.get("accept_privacy"):
            user.accept_privacy(settings.PRIVACY_POLICY_VERSION)

        return Response(
            {
                "created": created,
                "tokens": _tokens_for(user),
                "user": UserSerializer(user, context={"request": request}).data,
            },
            status=status.HTTP_200_OK,
        )


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            RefreshToken(request.data["refresh"]).blacklist()
        except Exception:
            return Response({"detail": "Jeton refresh manquant ou invalide."}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_205_RESET_CONTENT)


class MeView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user


class MePrivacyView(APIView):
    """POST /api/auth/me/privacy/ : l'utilisateur accepte la version actuelle de la politique de confidentialité."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        request.user.accept_privacy(settings.PRIVACY_POLICY_VERSION)
        return Response(UserSerializer(request.user, context={"request": request}).data)


class MeBecomeProviderView(APIView):
    """POST /api/auth/me/become-provider/ : un client passe à l'espace artisan (profil « en attente »)."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        user, _ = get_or_create_user_after_otp(request.user.phone, as_provider=True)
        return Response(UserSerializer(user, context={"request": request}).data)


class MeExportView(APIView):
    """GET /api/auth/me/export/ : droit d'accès, toutes les données de la personne (JSON)."""

    permission_classes = [IsAuthenticated]
    throttle_scope = "auth"

    def get(self, request):
        return Response(privacy.export_user_data(request.user, request))


class MeDeleteView(APIView):
    """POST /api/auth/me/delete/ {"confirm": true} : droit à l'effacement (anonymisation définitive)."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.data.get("confirm") is not True:
            return Response({"detail": "Confirmation manquante."}, status=status.HTTP_400_BAD_REQUEST)
        reasons = privacy.deletion_blockers(request.user)
        if reasons:
            return Response({"detail": " ".join(reasons), "code": "deletion_blocked"},
                            status=status.HTTP_400_BAD_REQUEST)
        privacy.anonymize_user(request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


_SITE_TILES = [
    ("M14 7l3-3 3 3-3 3M17 4v6M4 20l9-9M7 14l3 3", "Plomberie", "سباكة"),
    ("M13 2L4 14h7l-1 8 9-12h-7z", "Électricité", "كهرباء"),
    ("M4 4h12v5H4zM16 6h3v5h-7v3M11 14h2v7h-2z", "Peinture", "دهن"),
    ("M12 2v20M4.5 6.5l15 11M19.5 6.5l-15 11", "Climatisation", "تكييف"),
]
_SHIELD = "M12 3l7 3v6c0 4.5-3 7.5-7 9-4-1.5-7-4.5-7-9V6zM9 12l2 2 4-4"
_STAR = "M12 3l2.6 5.6 6 .7-4.5 4.1 1.2 6L12 16.6 6.7 19.4l1.2-6L3.4 9.3l6-.7z"
_CASH = "M3 7h18v10H3zM12 12h.01M6 10v4M18 10v4"

_SITE_TEXT = {
    "fr": {
        "tagline": "Trouvez le bon artisan, près de chez vous",
        "meta": "BRICOOL met en relation clients et artisans vérifiés en Algérie : plomberie, électricité, peinture, "
                "climatisation et plus. Devis gratuits, paiement à la fin.",
        "nav_label": "Menu", "nav_how": "Comment ça marche", "nav_apps": "Les applications", "nav_faq": "Questions",
        "switch": "العربية", "eyebrow": "Artisans vérifiés partout en Algérie",
        "h1": "Trouvez le bon artisan, près de chez vous",
        "lead": "Décrivez votre problème : BRICOOL l'envoie automatiquement aux artisans vérifiés les plus proches. "
                "Comparez leurs devis, discutez, et payez seulement à la fin du travail.",
        "dl_client": "Télécharger BRICOOL", "dl_client_sub": "Je cherche un artisan", "space_client": "Espace client", "space_pro": "Espace professionnel",
        "dl_pro": "Je suis professionnel", "dl_pro_sub": "Même application, espace artisan",
        "mock_q": "De quoi avez-vous besoin ?", "mock_card": "Décrivez votre problème",
        "mock_card_sub": "Les artisans proches reçoivent votre demande.",
        "how_title": "Comment ça marche", "how_sub": "Trois étapes, sans chercher ni appeler au hasard.",
        "steps": [
            {"t": "Décrivez le besoin", "p": "Une fuite, une prise, une peinture : quelques mots et une photo suffisent."},
            {"t": "Recevez des devis", "p": "Les artisans vérifiés les plus proches vous envoient leur prix et leur délai."},
            {"t": "Choisissez, payez à la fin", "p": "Vous voyez leurs avis et leur profil, vous choisissez, et vous payez "
                                                   "en espèces une fois le travail fini."},
        ],
        "apps_title": "Une application, deux espaces", "apps_sub": "Au premier lancement, choisissez votre espace : client ou artisan. Vous pouvez changer à tout moment.",
        "client_for": "Pour les particuliers",
        "client_points": ["Publier une demande en 1 minute", "Comparer les devis et les avis",
                          "Discuter avec l'artisan dans l'application"],
        "pro_for": "Pour les artisans et prestataires",
        "pro_points": ["Recevoir les demandes près de chez vous", "Envoyer vos devis en quelques secondes",
                       "Montrer vos réalisations et vos avis"],
        "trust_title": "La confiance avant tout",
        "trust": [
            {"d": _SHIELD, "t": "Artisans vérifiés", "p": "Chaque artisan est contrôlé par l'équipe BRICOOL avant de recevoir des demandes."},
            {"d": _STAR, "t": "Avis réels", "p": "Seuls les clients qui ont fait appel à l'artisan peuvent laisser un avis."},
            {"d": _CASH, "t": "Payez à la fin", "p": "Aucun paiement à l'avance : vous payez l'artisan quand le travail est terminé."},
        ],
        "services_title": "Plus de 40 services", "services_sub": "Pour la maison, la voiture et le quotidien.",
        "services": ["Plomberie", "Électricité", "Peinture", "Climatisation", "Maçonnerie", "Menuiserie", "Électroménager",
                     "Nettoyage", "Jardinage", "Déménagement", "Serrurerie", "Carrelage", "Chauffe-eau",
                     "Caméras de surveillance", "Mécanique auto"],
        "faq_title": "Questions fréquentes",
        "faq": [
            {"q": "BRICOOL est-il gratuit pour les clients ?", "a": "Oui. Publier une demande, recevoir des devis et discuter avec les artisans est gratuit."},
            {"q": "Comment les artisans sont-ils vérifiés ?", "a": "L'équipe BRICOOL contrôle chaque profil d'artisan avant qu'il puisse envoyer des devis."},
            {"q": "Comment se passe le paiement ?", "a": "Vous payez l'artisan directement, en espèces, à la fin du travail."},
            {"q": "Je suis artisan : comment rejoindre BRICOOL ?", "a": "Téléchargez BRICOOL, choisissez « Je suis professionnel », inscrivez-vous avec votre numéro et complétez votre profil : l'équipe valide votre compte."},
            {"q": "Mes données sont-elles protégées ?", "a": "Oui, conformément à la loi 18-07. Votre numéro n'est partagé qu'après l'acceptation d'un devis."},
        ],
        "privacy": "Politique de confidentialité",
        "stats_label": "BRICOOL en chiffres", "stat_artisans": "artisans vérifiés", "stat_missions": "missions réalisées",
        "stat_wilayas": "wilayas couvertes", "stat_rating": "note moyenne des clients",
        "promo_pro_title": "Vous êtes artisan ? Rejoignez BRICOOL",
        "promo_pro_text": "Recevez les demandes des clients près de chez vous. À l'inscription :",
        "promo_pro_points": "points offerts.",
        "artisans_short": "artisans", "featured_title": "Nos artisans les mieux notés",
        "featured_sub": "Vérifiés par BRICOOL et recommandés par leurs clients.", "verified": "Vérifié",
        "missions_short": "missions", "reviews_title": "Ce que disent les clients",
        "promo_client_title": "Un problème à la maison ? BRICOOL s'en occupe",
        "promo_client_text": "Gratuit pour les clients. Des devis en quelques minutes, d'artisans vérifiés près de chez vous.",
    },
    "ar": {
        "tagline": "اعثر على الحرفي المناسب بالقرب منك",
        "meta": "يربط BRICOOL بين الزبائن والحرفيين الموثّقين في الجزائر: سباكة، كهرباء، دهن، تكييف وغيرها. عروض مجانية والدفع في النهاية.",
        "nav_label": "القائمة", "nav_how": "كيف يعمل", "nav_apps": "التطبيقات", "nav_faq": "أسئلة",
        "switch": "Français", "eyebrow": "حرفيون موثّقون في كل الجزائر",
        "h1": "اعثر على الحرفي المناسب بالقرب منك",
        "lead": "صف مشكلتك: يرسلها BRICOOL تلقائياً إلى أقرب الحرفيين الموثّقين. قارن العروض، تحدّث معهم، وادفع فقط عند انتهاء العمل.",
        "dl_client": "حمّل BRICOOL", "dl_client_sub": "أبحث عن حرفي", "space_client": "فضاء الزبون", "space_pro": "فضاء المهني",
        "dl_pro": "أنا مهني", "dl_pro_sub": "نفس التطبيق، فضاء الحرفي",
        "mock_q": "ماذا تحتاج؟", "mock_card": "صف مشكلتك", "mock_card_sub": "يتلقى الحرفيون القريبون طلبك.",
        "how_title": "كيف يعمل", "how_sub": "ثلاث خطوات، دون بحث أو اتصال عشوائي.",
        "steps": [
            {"t": "صف حاجتك", "p": "تسرّب، مقبس، دهن: بضع كلمات وصورة تكفي."},
            {"t": "استلم العروض", "p": "يرسل لك أقرب الحرفيين الموثّقين السعر والمدة."},
            {"t": "اختر وادفع في النهاية", "p": "ترى آراءهم وملفاتهم، تختار، وتدفع نقداً بعد انتهاء العمل."},
        ],
        "apps_title": "تطبيق واحد، فضاءان", "apps_sub": "عند أول تشغيل اختر فضاءك: زبون أو حرفي. يمكنك التغيير في أي وقت.",
        "client_for": "للأفراد",
        "client_points": ["انشر طلباً في دقيقة", "قارن العروض والآراء", "تحدّث مع الحرفي داخل التطبيق"],
        "pro_for": "للحرفيين ومقدّمي الخدمات",
        "pro_points": ["استلم الطلبات القريبة منك", "أرسل عروضك في ثوانٍ", "اعرض أعمالك وآراء زبائنك"],
        "trust_title": "الثقة أولاً",
        "trust": [
            {"d": _SHIELD, "t": "حرفيون موثّقون", "p": "يتحقق فريق BRICOOL من كل حرفي قبل أن يستلم الطلبات."},
            {"d": _STAR, "t": "آراء حقيقية", "p": "فقط الزبائن الذين تعاملوا مع الحرفي يمكنهم ترك رأي."},
            {"d": _CASH, "t": "ادفع في النهاية", "p": "لا دفع مسبق: تدفع للحرفي عند انتهاء العمل."},
        ],
        "services_title": "أكثر من 40 خدمة", "services_sub": "للمنزل والسيارة والحياة اليومية.",
        "services": ["سباكة", "كهرباء", "دهن", "تكييف", "بناء", "نجارة", "أجهزة كهرومنزلية", "تنظيف", "بستنة",
                     "نقل الأثاث", "أقفال", "تبليط", "سخان الماء", "كاميرات المراقبة", "ميكانيك السيارات"],
        "faq_title": "أسئلة شائعة",
        "faq": [
            {"q": "هل BRICOOL مجاني للزبائن؟", "a": "نعم. نشر الطلب واستلام العروض والتحدث مع الحرفيين مجاني."},
            {"q": "كيف يتم التحقق من الحرفيين؟", "a": "يتحقق فريق BRICOOL من ملف كل حرفي قبل أن يرسل العروض."},
            {"q": "كيف يتم الدفع؟", "a": "تدفع للحرفي مباشرة، نقداً، عند انتهاء العمل."},
            {"q": "أنا حرفي: كيف أنضم إلى BRICOOL؟", "a": "حمّل BRICOOL، اختر «أنا مهني»، سجّل برقمك وأكمل ملفك: يقوم الفريق بتفعيل حسابك."},
            {"q": "هل معطياتي محمية؟", "a": "نعم، طبقاً للقانون 18-07. لا يُشارك رقمك إلا بعد قبول عرض سعر."},
        ],
        "privacy": "سياسة الخصوصية",
        "stats_label": "BRICOOL بالأرقام", "stat_artisans": "حرفي موثّق", "stat_missions": "مهمة منجزة",
        "stat_wilayas": "ولاية مغطاة", "stat_rating": "متوسط تقييم الزبائن",
        "promo_pro_title": "أنت حرفي؟ انضم إلى BRICOOL",
        "promo_pro_text": "استلم طلبات الزبائن القريبين منك. عند التسجيل:",
        "promo_pro_points": "نقطة مجانية.",
        "artisans_short": "حرفي", "featured_title": "أفضل حرفيينا تقييماً",
        "featured_sub": "موثّقون من BRICOOL ويوصي بهم زبائنهم.", "verified": "موثّق",
        "missions_short": "مهمة", "reviews_title": "ماذا يقول الزبائن",
        "promo_client_title": "مشكلة في البيت؟ BRICOOL يتكفّل بها",
        "promo_client_text": "مجاني للزبائن. عروض خلال دقائق من حرفيين موثّقين قريبين منك.",
    },
}


def _site_live_data(lang):
    """Données publiques en direct pour le site : chiffres, services, meilleurs artisans, derniers avis.
    Rien de privé : ni téléphone, ni adresse ; avis signés prénom + initiale."""
    from django.db.models import Avg, Count, Q

    from apps.catalog.models import Category
    from apps.marketplace.models import Mission, Review
    from apps.marketplace.serializers import PublicReviewSerializer

    from .models import ProviderProfile

    verified = ProviderProfile.objects.filter(
        verification_status=ProviderProfile.Verification.APPROVED, user__is_active=True
    )
    reviews = Review.objects.filter(moderation_status=Review.Moderation.APPROVED)
    rating = reviews.aggregate(avg=Avg("rating"))["avg"]
    stats = {
        "artisans": verified.count(),
        "missions": Mission.objects.filter(status__in=("completed", "paid")).count(),
        "wilayas": verified.exclude(base_wilaya=None).values("base_wilaya").distinct().count(),
        "rating": f"{rating:.1f}".replace(".", ",") if rating else None,
    }
    name_field = "name_ar" if lang == "ar" else "name_fr"
    categories = (
        Category.objects.filter(parent__isnull=True)
        .annotate(n=Count("providers", filter=Q(providers__provider__in=verified), distinct=True))
        .order_by("-n", "order")[:12]
    )
    top = (
        verified.select_related("user", "base_wilaya")
        .prefetch_related("categories__category")
        .order_by("-rating_avg", "-missions_count")[:6]
    )
    featured = []
    for p in top:
        cat = next(iter(p.categories.all()), None)
        featured.append({
            "name": p.business_name or p.user.full_name or "Artisan",
            "photo": p.user.photo.url if p.user.photo else "",
            "initials": "".join(w[0] for w in (p.business_name or p.user.full_name or "A").split()[:2]).upper(),
            "trade": getattr(cat.category, name_field, "") if cat else "",
            "wilaya": getattr(p.base_wilaya, name_field, "") if p.base_wilaya_id else "",
            "rating": f"{p.rating_avg:.1f}".replace(".", ",") if p.reviews_count else "",
            "missions": p.missions_count,
        })
    latest = [
        dict(PublicReviewSerializer(r).data, target=(r.target.full_name or ""))
        for r in reviews.select_related("author", "target").order_by("-created_at")[:3]
    ]
    return {
        "stats": stats,
        "categories": [{"name": getattr(c, name_field) or c.name_fr, "n": c.n} for c in categories],
        "featured": featured,
        "latest_reviews": latest,
        "free_points": settings.POINTS_WELCOME_FREE,
    }


def landing(request):
    """Site vitrine public (français / arabe) : présentation de BRICOOL, données en direct, téléchargement."""
    from .models import SiteText

    lang = "ar" if request.GET.get("lang") == "ar" else "fr"
    texts = dict(_SITE_TEXT[lang], announcement="")
    # textes modifiés par l'équipe dans l'administration (Textes du site web)
    for row in SiteText.objects.all():
        value = (row.ar if lang == "ar" else row.fr).strip()
        if value and row.key in texts and isinstance(texts[row.key], str):
            texts[row.key] = value
    return render(request, "site/accueil.html", {
        **_site_live_data(lang),
        "t": texts,
        "lang": lang,
        "dir": "rtl" if lang == "ar" else "ltr",
        "other_lang": "fr" if lang == "ar" else "ar",
        "tiles": [{"d": d, "label": ar if lang == "ar" else fr} for d, fr, ar in _SITE_TILES],
        "download_client": settings.DOWNLOAD_CLIENT_URL,
        "download_pro": settings.DOWNLOAD_PRO_URL,
        "legal_name": settings.LEGAL_NAME,
        "legal_address": settings.LEGAL_ADDRESS,
        "contact_email": settings.PRIVACY_CONTACT_EMAIL,
    })


def privacy_policy(request):
    """Page publique « Politique de confidentialité » (français, arabe, anglais), liée depuis l'app."""
    ai_abroad = bool(getattr(settings, "AI_ENABLED", False))
    if ai_abroad:
        transfer = (
            "L'assistant intelligent (aide à décrire une demande, estimation de prix, aide) transmet les textes "
            "que vous lui écrivez à un prestataire d'intelligence artificielle situé hors d'Algérie. Ce transfert "
            "n'est effectué qu'avec l'autorisation préalable de l'ANPDP. N'écrivez pas d'informations sensibles "
            "à l'assistant. Toutes les autres données restent traitées en Algérie."
        )
        transfer_ar = (
            "يرسل المساعد الذكي النصوص التي تكتبها له إلى مزوّد ذكاء اصطناعي خارج الجزائر، ولا يتم ذلك إلا بترخيص "
            "مسبق من السلطة الوطنية. لا تكتب معلومات حساسة للمساعد. تبقى بقية المعطيات معالجة في الجزائر."
        )
        transfer_en = (
            "The smart assistant (help describing a request, price estimate, help) sends the texts you write to it "
            "to an artificial intelligence provider located outside Algeria. This transfer only takes place with "
            "the prior authorisation of the ANPDP. Do not write sensitive information to the assistant. All other "
            "data is processed in Algeria."
        )
    else:
        transfer = "Aucune donnée personnelle n'est transférée hors d'Algérie."
        transfer_ar = "لا يتم نقل أي معطيات شخصية إلى خارج الجزائر."
        transfer_en = "No personal data is transferred outside Algeria."
    context = {
        "version": settings.PRIVACY_POLICY_VERSION,
        "legal_name": settings.LEGAL_NAME,
        "legal_address": settings.LEGAL_ADDRESS,
        "contact_email": settings.PRIVACY_CONTACT_EMAIL,
        "dpo": settings.PRIVACY_DPO,
        "anpdp_ref": settings.ANPDP_DECLARATION_REF,
        "retention_years": settings.PRIVACY_RETENTION_YEARS,
        "transfer_text": transfer,
        "transfer_text_ar": transfer_ar,
        "transfer_text_en": transfer_en,
    }
    return render(request, "legal/confidentialite.html", context)


MAX_PHOTO_BYTES = 5 * 1024 * 1024


class PhotoInSerializer(serializers.Serializer):
    photo = serializers.ImageField()

    def validate_photo(self, f):
        if f.size > MAX_PHOTO_BYTES:
            raise serializers.ValidationError("Photo trop lourde (5 Mo maximum).")
        return f


class MePhotoView(APIView):
    """Photo de profil : POST (multipart, champ « photo ») pour la changer, DELETE pour la retirer.

    Pour un artisan, c'est la photo que les clients voient sur ses devis."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        s = PhotoInSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        user = request.user
        if user.photo:
            user.photo.delete(save=False)  # pas de vieux fichiers orphelins
        user.photo = s.validated_data["photo"]
        user.save(update_fields=["photo"])
        return Response(UserSerializer(user, context={"request": request}).data)

    def delete(self, request):
        user = request.user
        if user.photo:
            user.photo.delete(save=False)
            user.photo = None
            user.save(update_fields=["photo"])
        return Response(UserSerializer(user, context={"request": request}).data)
