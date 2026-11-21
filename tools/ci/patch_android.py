"""Adapte le projet Android généré par `flutter create` :
- permission INTERNET (absente du manifeste principal par défaut)
- HTTP en clair autorisé (serveur de développement en http://)
- nom affiché de l'application

Usage : python3 patch_android.py <dossier android>
"""
import pathlib
import sys

root = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "android")
manifest = root / "app" / "src" / "main" / "AndroidManifest.xml"
text = manifest.read_text(encoding="utf-8")

if "android.permission.INTERNET" not in text:
    text = text.replace(
        "<application",
        '<uses-permission android:name="android.permission.INTERNET"/>\n    <application',
        1,
    )
if "usesCleartextTraffic" not in text:
    text = text.replace("<application", '<application\n        android:usesCleartextTraffic="true"', 1)
text = text.replace('android:label="ttb"', 'android:label="Bricolages"')

manifest.write_text(text, encoding="utf-8")
print(f"Manifeste adapté : {manifest}")
