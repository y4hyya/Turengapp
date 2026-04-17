import objc
import threading

from AppKit import (
    NSApplication, NSApplicationActivationPolicyAccessory,
    NSStatusBar, NSVariableStatusItemLength,
    NSPanel, NSWindowStyleMaskBorderless,
    NSBackingStoreBuffered,
    NSVisualEffectView, NSVisualEffectMaterialPopover,
    NSVisualEffectBlendingModeBehindWindow,
    NSVisualEffectStateFollowsWindowActiveState,
    NSSearchField, NSTextField,
    NSScrollView, NSTextView,
    NSView,
    NSMenu, NSMenuItem,
    NSColor, NSFont, NSCursor,
    NSScreen, NSApp,
    NSWorkspace,
    NSPasteboard, NSPasteboardTypeString,
    NSAnimationContext,
    NSTextAlignmentCenter,
    NSForegroundColorAttributeName, NSFontAttributeName,
    NSLinkAttributeName, NSUnderlineStyleAttributeName,
    NSCursorAttributeName,
    NSAttributedString,
    NSNoBorder,
    NSMakeRect, NSMakePoint, NSMakeSize, NSMakeRange,
    NSStatusWindowLevel,
    NSEventTypeRightMouseUp,
    NSEventMaskLeftMouseUp, NSEventMaskRightMouseUp,
)
from Foundation import NSObject

from scraper import search

PANEL_WIDTH = 400
PANEL_HEIGHT = 480

# 8pt grid spacing tokens (HIG Visual Design)
SPACE_XS = 4
SPACE_SM = 8
SPACE_MD = 12
SPACE_LG = 16
SPACE_XL = 20

RADIUS_PANEL = 12

SEARCH_HEIGHT = 24
ANCHOR_GAP = SPACE_SM
EDGE_MARGIN = SPACE_SM


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
        bg_frame = NSMakeRect(0, 0, PANEL_WIDTH, PANEL_HEIGHT)

        if NSWorkspace.sharedWorkspace().accessibilityDisplayShouldReduceTransparency():
            bg = NSView.alloc().initWithFrame_(bg_frame)
            bg.setWantsLayer_(True)
            bg.layer().setBackgroundColor_(
                NSColor.windowBackgroundColor().CGColor()
            )
        else:
            bg = NSVisualEffectView.alloc().initWithFrame_(bg_frame)
            bg.setMaterial_(NSVisualEffectMaterialPopover)
            bg.setBlendingMode_(NSVisualEffectBlendingModeBehindWindow)
            bg.setState_(NSVisualEffectStateFollowsWindowActiveState)
            bg.setWantsLayer_(True)

        bg.layer().setCornerRadius_(RADIUS_PANEL)
        bg.layer().setMasksToBounds_(True)

        search_y = PANEL_HEIGHT - SPACE_LG - SEARCH_HEIGHT
        field_w = PANEL_WIDTH - SPACE_LG * 2

        self.search_field = NSSearchField.alloc().initWithFrame_(
            NSMakeRect(SPACE_LG, search_y, field_w, SEARCH_HEIGHT)
        )
        self.search_field.setPlaceholderString_("Type a word, press Enter...")
        self.search_field.setFont_(NSFont.systemFontOfSize_(NSFont.systemFontSize()))
        self.search_field.setFocusRingType_(1)  # NSFocusRingTypeNone
        bg.addSubview_(self.search_field)

        sep_y = search_y - SPACE_SM
        sep = NSView.alloc().initWithFrame_(NSMakeRect(0, sep_y, PANEL_WIDTH, 1))
        sep.setWantsLayer_(True)
        sep.layer().setBackgroundColor_(NSColor.separatorColor().CGColor())
        bg.addSubview_(sep)

        results_height = sep_y - 1
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
        self.results_view.setTextContainerInset_(NSMakeSize(SPACE_LG, SPACE_LG))
        self.results_view.setLinkTextAttributes_({
            NSForegroundColorAttributeName: NSColor.labelColor(),
            NSUnderlineStyleAttributeName: 0,
            NSCursorAttributeName: NSCursor.pointingHandCursor(),
        })

        scroll.setDocumentView_(self.results_view)
        bg.addSubview_(scroll)

        toast_w = 80
        toast_h = 22
        toast_x = (PANEL_WIDTH - toast_w) // 2
        toast_y = SPACE_SM

        self.copied_toast = NSView.alloc().initWithFrame_(
            NSMakeRect(toast_x, toast_y, toast_w, toast_h)
        )
        self.copied_toast.setWantsLayer_(True)
        self.copied_toast.layer().setBackgroundColor_(
            NSColor.controlBackgroundColor().colorWithAlphaComponent_(0.85).CGColor()
        )
        self.copied_toast.layer().setCornerRadius_(6)
        self.copied_toast.layer().setMasksToBounds_(True)
        self.copied_toast.setAlphaValue_(0.0)

        toast_label = NSTextField.alloc().initWithFrame_(
            NSMakeRect(0, 3, toast_w, 16)
        )
        toast_label.setStringValue_("Copied")
        toast_label.setEditable_(False)
        toast_label.setSelectable_(False)
        toast_label.setBordered_(False)
        toast_label.setBezeled_(False)
        toast_label.setDrawsBackground_(False)
        toast_label.setAlignment_(NSTextAlignmentCenter)
        toast_label.setTextColor_(NSColor.secondaryLabelColor())
        toast_label.setFont_(NSFont.systemFontOfSize_(NSFont.smallSystemFontSize()))
        self.copied_toast.addSubview_(toast_label)

        bg.addSubview_(self.copied_toast)

        self.setContentView_(bg)
        self._setPlaceholder("Type a word above and press Enter to translate")

    def cancelOperation_(self, sender):
        self.orderOut_(None)

    def orderOut_(self, sender):
        if hasattr(self, "copied_toast"):
            NSObject.cancelPreviousPerformRequestsWithTarget_selector_object_(
                self, "_hideCopiedToast:", None
            )
            self.copied_toast.layer().removeAllAnimations()
            self.copied_toast.setAlphaValue_(0.0)
        objc.super(TurengPanel, self).orderOut_(sender)

    @objc.python_method
    def showCopiedToast(self):
        NSObject.cancelPreviousPerformRequestsWithTarget_selector_object_(
            self, "_hideCopiedToast:", None
        )

        reduce_motion = NSWorkspace.sharedWorkspace().accessibilityDisplayShouldReduceMotion()

        if reduce_motion:
            self.copied_toast.setAlphaValue_(1.0)
        else:
            NSAnimationContext.beginGrouping()
            NSAnimationContext.currentContext().setDuration_(0.2)
            self.copied_toast.animator().setAlphaValue_(1.0)
            NSAnimationContext.endGrouping()

        self.performSelector_withObject_afterDelay_(
            "_hideCopiedToast:", None, 0.8
        )

    def _hideCopiedToast_(self, _):
        reduce_motion = NSWorkspace.sharedWorkspace().accessibilityDisplayShouldReduceMotion()
        if reduce_motion:
            self.copied_toast.setAlphaValue_(0.0)
        else:
            NSAnimationContext.beginGrouping()
            NSAnimationContext.currentContext().setDuration_(0.2)
            self.copied_toast.animator().setAlphaValue_(0.0)
            NSAnimationContext.endGrouping()

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

            line_attrs = {
                NSForegroundColorAttributeName: NSColor.labelColor(),
                NSFontAttributeName: NSFont.systemFontOfSize_(13),
            }
            target_attrs = dict(line_attrs)
            target_attrs[NSLinkAttributeName] = tr

            prefix = f"  {en}  →  "
            suffix = f"  {rtype}\n" if rtype else "\n"

            storage.appendAttributedString_(
                NSAttributedString.alloc().initWithString_attributes_(prefix, line_attrs)
            )
            storage.appendAttributedString_(
                NSAttributedString.alloc().initWithString_attributes_(tr, target_attrs)
            )
            storage.appendAttributedString_(
                NSAttributedString.alloc().initWithString_attributes_(suffix, line_attrs)
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

    @objc.python_method
    def _buildAppMenu(self):
        menubar = NSMenu.alloc().init()
        edit_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Edit", None, "")
        edit_menu = NSMenu.alloc().initWithTitle_("Edit")
        for title, action, key in [
            ("Cut",        "cut:",       "x"),
            ("Copy",       "copy:",      "c"),
            ("Paste",      "paste:",     "v"),
            ("Undo",       "undo:",      "z"),
            ("Select All", "selectAll:", "a"),
        ]:
            edit_menu.addItemWithTitle_action_keyEquivalent_(title, action, key)
        edit_item.setSubmenu_(edit_menu)
        menubar.addItem_(edit_item)
        NSApp.setMainMenu_(menubar)

    @objc.python_method
    def _buildStatusMenu(self):
        menu = NSMenu.alloc().init()
        quit_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Quit Tureng", "terminate:", "q"
        )
        quit_item.setTarget_(NSApp)
        menu.addItem_(quit_item)
        return menu

    def applicationDidFinishLaunching_(self, notification):
        NSApp.setActivationPolicy_(NSApplicationActivationPolicyAccessory)
        self._buildAppMenu()

        self._status_item = NSStatusBar.systemStatusBar().statusItemWithLength_(
            NSVariableStatusItemLength
        )
        self._status_item.button().setTitle_("TR")
        self._status_item.button().setTarget_(self)
        self._status_item.button().setAction_("statusItemClicked:")
        self._status_item.button().sendActionOn_(
            NSEventMaskLeftMouseUp | NSEventMaskRightMouseUp
        )

        self._status_menu = self._buildStatusMenu()

        self._panel = TurengPanel.alloc().initPanel()
        self._panel.setDelegate_(self)

        self._panel.search_field.setTarget_(self)
        self._panel.search_field.setAction_("performSearch:")
        self._panel.search_field.setDelegate_(self)
        self._panel.results_view.setDelegate_(self)

    @objc.IBAction
    def statusItemClicked_(self, sender):
        event = NSApp.currentEvent()
        if event is not None and event.type() == NSEventTypeRightMouseUp:
            self._status_item.setMenu_(self._status_menu)
            self._status_item.button().performClick_(None)
            self._status_item.setMenu_(None)
            return
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
            y = frame.origin.y - PANEL_HEIGHT - ANCHOR_GAP
            screen_w = NSScreen.mainScreen().frame().size.width
            x = max(EDGE_MARGIN, min(x, screen_w - PANEL_WIDTH - EDGE_MARGIN))
            self._panel.setFrameOrigin_(NSMakePoint(x, max(EDGE_MARGIN, y)))

        self._panel.makeKeyAndOrderFront_(None)
        NSApp.activateIgnoringOtherApps_(True)
        self._panel.makeFirstResponder_(self._panel.search_field)

    def windowDidResignKey_(self, notification):
        self._panel.orderOut_(None)

    def control_textView_doCommandBySelector_(self, control, textView, selector):
        if str(selector) == "cancelOperation:":
            self._panel.orderOut_(None)
            return True
        return False

    def textView_clickedOnLink_atIndex_(self, textView, link, charIndex):
        word = str(link).strip()
        if not word:
            return False
        pb = NSPasteboard.generalPasteboard()
        pb.clearContents()
        pb.setString_forType_(word, NSPasteboardTypeString)
        self._panel.showCopiedToast()
        return True

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
