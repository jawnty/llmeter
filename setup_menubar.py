"""py2app build script for the llmeter menu bar app.

Usage:

    python3 -m venv .venv-menubar
    . .venv-menubar/bin/activate
    pip install -r requirements.txt -r requirements-menubar.txt

    # alias mode (fast iteration, runs from source):
    python setup_menubar.py py2app -A

    # standalone bundle:
    python setup_menubar.py py2app

The resulting bundle is at dist/Llmeter.app. Drag it to /Applications and
add to Login Items via System Settings → General → Login Items.
"""

from setuptools import setup

APP = ["llmeter/menubar/__main__.py"]
OPTIONS = {
    "argv_emulation": False,
    "iconfile": None,
    "plist": {
        "CFBundleName": "Llmeter",
        "CFBundleDisplayName": "Llmeter",
        "CFBundleIdentifier": "com.jawnty.llmeter.menubar",
        "CFBundleVersion": "0.1.0",
        "CFBundleShortVersionString": "0.1.0",
        "LSUIElement": True,  # menu bar only, no Dock icon
    },
    "packages": ["rumps", "llmeter"],
}

setup(
    app=APP,
    name="Llmeter",
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
