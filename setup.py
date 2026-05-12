"""
py2app build script for Tureng.

Usage:
    python3 setup.py py2app -A      # alias build (dev: symlinks to source)
    python3 setup.py py2app         # full standalone build
"""

from setuptools import setup

APP = ["app.py"]
ICON = "Tureng.icns"

PLIST = {
    "CFBundleName": "Tureng",
    "CFBundleDisplayName": "Tureng",
    "CFBundleIdentifier": "com.yahya.tureng",
    "CFBundleShortVersionString": "1.0",
    "CFBundleVersion": "1",
    "LSMinimumSystemVersion": "13.0",
    "NSHighResolutionCapable": True,
    "LSUIElement": True,
    "LSApplicationCategoryType": "public.app-category.reference",
    "NSHumanReadableCopyright": "© 2026 Yahya",
}

OPTIONS = {
    "iconfile": ICON,
    "plist": PLIST,
    "arch": "arm64",
    "optimize": 2,
    "packages": [
        "cloudscraper",
        "bs4",
        "requests",
        "urllib3",
        "certifi",
        "requests_toolbelt",
    ],
    "includes": [
        "objc",
        "AppKit",
        "Foundation",
        "PyObjCTools",
    ],
}

setup(
    app=APP,
    name="Tureng",
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
