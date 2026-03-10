import threading
import rumps
from scraper import search

MAX_RESULTS = 20


class TurengApp(rumps.App):
    def __init__(self):
        super().__init__("TR", quit_button="Quit")
        self.menu = [
            "Search...",
            None,
            {"Results": [rumps.MenuItem("No results yet")]},
        ]

    @rumps.clicked("Search...")
    def on_search(self, _):
        window = rumps.Window(
            message="Enter a word to translate:",
            title="Tureng",
            default_text="",
            ok="Search",
            cancel="Cancel",
            dimensions=(260, 24),
        )
        response = window.run()
        if response.clicked == 1 and response.text.strip():
            word = response.text.strip()
            self._set_lines([f'Searching "{word}"...'])
            threading.Thread(target=self._fetch, args=(word,), daemon=True).start()

    def _fetch(self, word):
        try:
            results = search(word)
        except Exception as e:
            self._set_lines([f"Error: {e}"])
            return

        if not results:
            self._set_lines([f'No results for "{word}"'])
            return

        lines = []
        current_category = None
        for r in results[:MAX_RESULTS]:
            if r["category"] != current_category:
                current_category = r["category"]
                lines.append(f"── {current_category} ──")
            type_str = f"  {r['type']}" if r["type"] else ""
            lines.append(f"  {r['en']} → {r['tr']}{type_str}")

        self._set_lines(lines)

    def _set_lines(self, lines: list[str]):
        submenu = self.menu["Results"]
        submenu.clear()
        for i, text in enumerate(lines):
            # Append invisible zero-width spaces to make each key unique
            # while setTitle_ keeps the display text clean
            unique_key = text + "\u200b" * i
            item = rumps.MenuItem(unique_key)
            item._menuitem.setTitle_(text)
            item._menuitem.setEnabled_(False)
            submenu.add(item)


if __name__ == "__main__":
    TurengApp().run()
