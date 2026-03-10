import objc
import threading

from AppKit import (
    NSApplication, NSApplicationActivationPolicyAccessory,
    NSStatusBar, NSVariableStatusItemLength,
    NSPanel, NSWindowStyleMaskBorderless,
    NSBackingStoreBuffered,
    NSVisualEffectView, NSVisualEffectMaterialPopover,
    NSVisualEffectBlendingModeBehindWindow, NSVisualEffectStateActive,
    NSSearchField,
    NSScrollView, NSTextView,
    NSView, NSButton,
    NSColor, NSFont,
    NSScreen, NSApp,
    NSForegroundColorAttributeName, NSFontAttributeName,
    NSAttributedString,
    NSNoBorder,
    NSMakeRect, NSMakePoint, NSMakeSize, NSMakeRange,
    NSStatusWindowLevel,
)
from Foundation import NSObject

from scraper import search

PANEL_WIDTH = 400
PANEL_HEIGHT = 480
PADDING = 14
SEARCH_HEIGHT = 36


class TurengPanel(NSPanel):

    def initPanel(self):
        style = NSWindowStyleMaskBorderless
        self = objc.super(TurengPanel, self).initWithContentRect_styleMask_backing_defer_(
            NSMakeRect(0, 0, PANEL_WIDTH, PANEL_HEIGHT),
            style,
            NSBackingStoreBuffered,
            False,
        )
        if self is None:
            return None

        self.setLevel_(NSStatusWindowLevel + 1)
        self.setHasShadow_(True)
        self.setOpaque_(False)
        self.setBackgroundColor_(NSColor.clearColor())
        self._buildUI()
        return self

    @objc.python_method
    def _buildUI(self):
        # Frosted glass background with rounded corners
        visual = NSVisualEffectView.alloc().initWithFrame_(
            NSMakeRect(0, 0, PANEL_WIDTH, PANEL_HEIGHT)
        )
        visual.setMaterial_(NSVisualEffectMaterialPopover)
        visual.setBlendingMode_(NSVisualEffectBlendingModeBehindWindow)
        visual.setState_(NSVisualEffectStateActive)
        visual.setWantsLayer_(True)
        visual.layer().setCornerRadius_(12)
        visual.layer().setMasksToBounds_(True)

        # Search field (80% width) + Exit button (remaining 20%)
        search_y = PANEL_HEIGHT - PADDING - SEARCH_HEIGHT
        available_w = PANEL_WIDTH - PADDING * 2
        btn_w = 60
        gap = 8
        field_w = available_w - btn_w - gap

        self.search_field = NSSearchField.alloc().initWithFrame_(
            NSMakeRect(PADDING, search_y, field_w, SEARCH_HEIGHT)
        )
        self.search_field.setPlaceholderString_("Type a word, press Enter...")
        self.search_field.setFont_(NSFont.systemFontOfSize_(14))
        self.search_field.setFocusRingType_(1)  # NSFocusRingTypeNone
        visual.addSubview_(self.search_field)

        # Exit button
        btn_x = PADDING + field_w + gap
        exit_btn = NSButton.alloc().initWithFrame_(
            NSMakeRect(btn_x, search_y, btn_w, SEARCH_HEIGHT)
        )
        exit_btn.setTitle_("Exit")
        exit_btn.setBezelStyle_(4)  # NSBezelStyleRounded
        exit_btn.setFont_(NSFont.systemFontOfSize_(13))
        exit_btn.setTarget_(self)
        exit_btn.setAction_("exitApp:")
        visual.addSubview_(exit_btn)

        # Separator
        sep_y = search_y - PADDING // 2
        sep = NSView.alloc().initWithFrame_(NSMakeRect(0, sep_y, PANEL_WIDTH, 1))
        sep.setWantsLayer_(True)
        sep.layer().setBackgroundColor_(
            NSColor.colorWithRed_green_blue_alpha_(0.5, 0.5, 0.5, 0.4).CGColor()
        )
        visual.addSubview_(sep)

        # Scroll view + text view
        results_height = sep_y - 2
        scroll = NSScrollView.alloc().initWithFrame_(
            NSMakeRect(0, 0, PANEL_WIDTH, results_height)
        )
        scroll.setHasVerticalScroller_(True)
        scroll.setAutohidesScrollers_(True)
        scroll.setBorderType_(NSNoBorder)
        scroll.setDrawsBackground_(False)

        self.results_view = NSTextView.alloc().initWithFrame_(
            NSMakeRect(0, 0, PANEL_WIDTH, results_height)
        )
        self.results_view.setEditable_(False)
        self.results_view.setSelectable_(True)
        self.results_view.setDrawsBackground_(False)
        self.results_view.setVerticallyResizable_(True)
        self.results_view.setHorizontallyResizable_(False)
        self.results_view.setMaxSize_(NSMakeSize(PANEL_WIDTH, 1e8))
        self.results_view.textContainer().setWidthTracksTextView_(True)
        self.results_view.textContainer().setContainerSize_(NSMakeSize(PANEL_WIDTH, 1e8))
        self.results_view.setTextContainerInset_(NSMakeSize(PADDING, PADDING))

        scroll.setDocumentView_(self.results_view)
        visual.addSubview_(scroll)

        self.setContentView_(visual)
        self._setPlaceholder("Type a word above and press Enter to translate")

    def exitApp_(self, sender):
        NSApp.terminate_(None)

    def canBecomeKeyWindow(self):
        return True

    def canBecomeMainWindow(self):
        return True

    @objc.python_method
    def _setPlaceholder(self, text):
        attrs = {
            NSForegroundColorAttributeName: NSColor.tertiaryLabelColor(),
            NSFontAttributeName: NSFont.systemFontOfSize_(13),
        }
        astr = NSAttributedString.alloc().initWithString_attributes_(text, attrs)
        self.results_view.textStorage().setAttributedString_(astr)

    def showLoading_(self, word):
        self._setPlaceholder(f'Searching "{word}"...')

    def showResults_(self, data):
        results = list(data["results"])
        word = str(data["word"])

        if not results:
            self._setPlaceholder(f'No results found for "{word}"')
            return

        storage = self.results_view.textStorage()
        storage.beginEditing()
        storage.setAttributedString_(NSAttributedString.alloc().initWithString_(""))

        current_category = None
        for r in results[:20]:
            category = str(r["category"])
            en = str(r["en"])
            tr = str(r["tr"])
            rtype = str(r.get("type", ""))

            if category != current_category:
                current_category = category
                cat_attrs = {
                    NSForegroundColorAttributeName: NSColor.secondaryLabelColor(),
                    NSFontAttributeName: NSFont.boldSystemFontOfSize_(11),
                }
                storage.appendAttributedString_(
                    NSAttributedString.alloc().initWithString_attributes_(
                        f"\n{category}\n", cat_attrs
                    )
                )

            type_str = f"  {rtype}" if rtype else ""
            line = f"  {en}  →  {tr}{type_str}\n"
            line_attrs = {
                NSForegroundColorAttributeName: NSColor.labelColor(),
                NSFontAttributeName: NSFont.systemFontOfSize_(13),
            }
            storage.appendAttributedString_(
                NSAttributedString.alloc().initWithString_attributes_(line, line_attrs)
            )

        storage.endEditing()
        self.results_view.scrollRangeToVisible_(NSMakeRange(0, 0))

    def showError_(self, message):
        attrs = {
            NSForegroundColorAttributeName: NSColor.systemRedColor(),
            NSFontAttributeName: NSFont.systemFontOfSize_(13),
        }
        self.results_view.textStorage().setAttributedString_(
            NSAttributedString.alloc().initWithString_attributes_(str(message), attrs)
        )


class AppDelegate(NSObject):

    def applicationDidFinishLaunching_(self, notification):
        NSApp.setActivationPolicy_(NSApplicationActivationPolicyAccessory)

        self._status_item = NSStatusBar.systemStatusBar().statusItemWithLength_(
            NSVariableStatusItemLength
        )
        self._status_item.button().setTitle_("TR")
        self._status_item.button().setTarget_(self)
        self._status_item.button().setAction_("togglePanel:")

        self._panel = TurengPanel.alloc().initPanel()
        self._panel.setDelegate_(self)

        self._panel.search_field.setTarget_(self)
        self._panel.search_field.setAction_("performSearch:")

    @objc.IBAction
    def togglePanel_(self, sender):
        if self._panel.isVisible():
            self._panel.orderOut_(None)
        else:
            self._showPanel()

    @objc.python_method
    def _showPanel(self):
        btn = self._status_item.button()
        if btn.window():
            frame = btn.window().frame()
            x = frame.origin.x + frame.size.width - PANEL_WIDTH
            y = frame.origin.y - PANEL_HEIGHT - 6
            screen_w = NSScreen.mainScreen().frame().size.width
            x = max(8, min(x, screen_w - PANEL_WIDTH - 8))
            self._panel.setFrameOrigin_(NSMakePoint(x, max(8, y)))

        self._panel.makeKeyAndOrderFront_(None)
        NSApp.activateIgnoringOtherApps_(True)
        self._panel.makeFirstResponder_(self._panel.search_field)

    def windowDidResignKey_(self, notification):
        self._panel.orderOut_(None)

    @objc.IBAction
    def performSearch_(self, sender):
        word = sender.stringValue().strip()
        if not word:
            return
        self._panel.showLoading_(word)
        threading.Thread(target=self._fetch, args=(word,), daemon=True).start()

    @objc.python_method
    def _fetch(self, word):
        try:
            results = search(word)
            self._panel.performSelectorOnMainThread_withObject_waitUntilDone_(
                "showResults:", {"results": results, "word": word}, False
            )
        except Exception as e:
            self._panel.performSelectorOnMainThread_withObject_waitUntilDone_(
                "showError:", str(e), False
            )


if __name__ == "__main__":
    app = NSApplication.sharedApplication()
    delegate = AppDelegate.alloc().init()
    app.setDelegate_(delegate)
    app.run()
