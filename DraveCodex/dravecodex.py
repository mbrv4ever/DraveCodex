#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DraveCodex - offline campagne-wiki.
Pagina's voor NPC's, locaties, items, sessies en lore, met [[links]],
zoeken en categorieen. Alles lokaal als gewone .md-tekstbestanden.
Dravenlock-huisstijl. Werkt zonder internet.
"""
import os
import re
import sys
import json

from PyQt6.QtCore import Qt, QLocale, QUrl, QSize
from PyQt6.QtGui import (QPixmap, QIcon, QDesktopServices, QAction,
                         QKeySequence, QShortcut, QTextCursor)
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QPushButton, QVBoxLayout,
    QHBoxLayout, QComboBox, QLineEdit, QListWidget, QListWidgetItem,
    QPlainTextEdit, QTextBrowser, QStackedWidget, QFileDialog, QMessageBox,
    QDialog, QFrame, QStatusBar, QToolButton, QSplitter)

APP_NAME = "DraveCodex"
APP_VERSION = "0.2"
DONATE_URL = "https://paypal.me/roger076"
SUPPORT_MAIL = "service@dravenlock.nl"

# ---- Dravenlock-huisstijl ----
BG = "#0e0e11"
PANEL = "#16161b"
SILVER = "#d4d4d4"
MUTE = "#8a8a94"
ACCENT = "#6fa3d6"
WARN = "#e0a23a"

CATEGORIES = ["NPC", "Locatie", "Item", "Sessie", "Lore", "Overig"]


# ---------------------------------------------------------------------------
# Pad-helpers (frozen-bewust)
# ---------------------------------------------------------------------------
def _app_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def _config_path():
    return os.path.join(_app_dir(), "dravecodex_config.json")


def _default_codex():
    return os.path.join(_app_dir(), "codex")


DEFAULT_CONFIG = {"lang": "", "codex": ""}


def load_config():
    cfg = dict(DEFAULT_CONFIG)
    try:
        with open(_config_path(), "r", encoding="utf-8") as f:
            cfg.update(json.load(f))
    except Exception:
        pass
    return cfg


def save_config(cfg):
    try:
        with open(_config_path(), "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Taal
# ---------------------------------------------------------------------------
_LANG = "nl"

TRANSLATIONS = {
    "en": {
        "Nieuwe pagina": "New page", "Opslaan": "Save", "Verwijderen": "Delete",
        "Map kiezen\u2026": "Choose folder\u2026", "Zoeken\u2026": "Search\u2026",
        "Alle categorieen": "All categories", "Categorie:": "Category:",
        "Titel": "Title", "Lezen": "Read", "Bewerken": "Edit",
        "Instellingen\u2026": "Settings\u2026", "Snelgids": "Quick guide",
        "Over": "About", "Sluiten": "Close", "Taal:": "Language:",
        "Automatisch (OS)": "Automatic (OS)", "Nederlands": "Dutch",
        "Engels": "English", "Donatie": "Donate",
        "Kies een pagina of maak een nieuwe.": "Pick a page or create a new one.",
        "Nog geen pagina's. Klik 'Nieuwe pagina'.":
            "No pages yet. Click 'New page'.",
        "Naamloos": "Untitled", "pagina's": "pages", "pagina": "page",
        "Niet-opgeslagen wijzigingen": "Unsaved changes",
        "Wil je de wijzigingen opslaan?": "Do you want to save your changes?",
        "Pagina verwijderen?": "Delete page?",
        "Weet je zeker dat je deze pagina wilt verwijderen?":
            "Are you sure you want to delete this page?",
        "Pagina bestaat niet (nog niet aangemaakt):":
            "Page does not exist (not created yet):",
        "Aanmaken?": "Create it?", "Map:": "Folder:",
        "snelgids_titel": "DraveCodex - quick guide",
        "Geef de pagina eerst een titel.": "Give the page a title first.",
    }
}


def t(s, lang=None):
    lg = lang or _LANG
    if lg == "nl":
        return s
    return TRANSLATIONS.get(lg, {}).get(s, s)


def detect_lang(cfg):
    forced = (cfg.get("lang") or "").strip().lower()
    if forced in ("nl", "en"):
        return forced
    try:
        if QLocale.system().name().lower().startswith("nl"):
            return "nl"
        return "en"
    except Exception:
        return "nl"


# ---------------------------------------------------------------------------
# Logo / icoon
# ---------------------------------------------------------------------------
def _logo_path(name):
    p = os.path.join(_app_dir(), name)
    return p if os.path.exists(p) else None


def logo_pixmap(size=32):
    p = _logo_path("logo.png")
    if p:
        pm = QPixmap(p)
        if not pm.isNull():
            return pm.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio,
                             Qt.TransformationMode.SmoothTransformation)
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    return pm


def app_icon():
    for n in ("logo.ico", "logo.png"):
        p = _logo_path(n)
        if p:
            ic = QIcon(p)
            if not ic.isNull():
                return ic
    return QIcon()


# ---------------------------------------------------------------------------
# Opslag: codex-map met .md-bestanden + kleine kop (front matter)
# ---------------------------------------------------------------------------
def slugify(title):
    s = (title or "").strip().lower()
    s = re.sub(r"[^\w\s-]", "", s, flags=re.UNICODE)
    s = re.sub(r"[\s]+", "-", s).strip("-")
    return s or "naamloos"


class Page:
    def __init__(self, slug="", title="", category="Overig", body="", path=""):
        self.slug = slug
        self.title = title
        self.category = category
        self.body = body
        self.path = path


def parse_md(text):
    """Lees front matter (titel/categorie) + body uit een .md-tekst."""
    title = ""
    category = "Overig"
    body = text
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            head = text[3:end].strip()
            body = text[end + 4:].lstrip("\n")
            for line in head.splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    k = k.strip().lower()
                    v = v.strip()
                    if k in ("titel", "title"):
                        title = v
                    elif k in ("categorie", "category"):
                        category = v
    return title, category, body


def page_to_md(page):
    cat = page.category if page.category in CATEGORIES else "Overig"
    head = "---\ntitel: %s\ncategorie: %s\n---\n\n" % (page.title or "", cat)
    return head + (page.body or "")


def load_pages(folder):
    pages = []
    try:
        names = sorted(os.listdir(folder))
    except Exception:
        return pages
    for name in names:
        if not name.lower().endswith(".md"):
            continue
        path = os.path.join(folder, name)
        try:
            with open(path, "r", encoding="utf-8") as f:
                text = f.read()
        except Exception:
            continue
        title, category, body = parse_md(text)
        slug = name[:-3]
        if not title:
            title = slug.replace("-", " ").strip().title()
        pages.append(Page(slug, title, category, body, path))
    return pages


# ---------------------------------------------------------------------------
# Snelgids
# ---------------------------------------------------------------------------
GUIDE_NL = """DraveCodex - Snelgids

DraveCodex is je offline campagne-wiki. Je maakt pagina's voor NPC's,
locaties, items, sessies en lore, en je linkt ze aan elkaar. Alles wordt
lokaal opgeslagen als gewone tekstbestanden (.md) in je codex-map - geen
internet nodig, en je kunt ze ook buiten DraveCodex lezen.

Aan de slag
- Klik 'Nieuwe pagina', geef een titel en kies een categorie.
- Typ je tekst in het grote vak. Klik 'Opslaan' (of Ctrl+S).
- Links staat de lijst met pagina's. Zoek bovenin of filter op categorie.

Pagina's aan elkaar linken
- Zet een paginatitel tussen dubbele blokhaken: [[De Herberg]].
- Klik op 'Lezen' om de pagina netjes te bekijken; de links zijn dan
  aanklikbaar en brengen je naar die pagina. Bestaat de pagina nog niet,
  dan kun je 'm meteen aanmaken.

Opmaak (markdown)
- # Kop, ## Subkop
- **vet**, *cursief*
- - opsomming (streepje + spatie)
- Gewone webadressen (http...) werken ook als link.

Tips
- 'Map kiezen' om een andere codex-map te openen (bijv. per campagne).
- Je tekstbestanden staan veilig in die map; maak gerust een back-up.

Vragen of een tip? service@dravenlock.nl
"""

GUIDE_EN = """DraveCodex - Quick guide

DraveCodex is your offline campaign wiki. Create pages for NPCs, locations,
items, sessions and lore, and link them together. Everything is stored
locally as plain text files (.md) in your codex folder - no internet
needed, and you can read them outside DraveCodex too.

Getting started
- Click 'New page', give it a title and pick a category.
- Type in the big box. Click 'Save' (or Ctrl+S).
- The page list is on the left. Search at the top or filter by category.

Linking pages
- Put a page title in double brackets: [[The Inn]].
- Click 'Read' to view the page nicely; links are clickable and take you
  to that page. If the page doesn't exist yet, you can create it.

Formatting (markdown)
- # Heading, ## Subheading
- **bold**, *italic*
- - bullet list (dash + space)
- Plain web addresses (http...) work as links too.

Tips
- 'Choose folder' to open another codex folder (e.g. per campaign).
- Your text files live safely in that folder; feel free to back them up.

Questions or feedback? service@dravenlock.nl
"""


class GuideDialog(QDialog):
    def __init__(self, parent, lang):
        super().__init__(parent)
        self.setWindowTitle(t("snelgids_titel", lang))
        self.resize(580, 560)
        lay = QVBoxLayout(self)
        box = QTextBrowser()
        box.setOpenExternalLinks(True)
        box.setPlainText(GUIDE_NL if lang == "nl" else GUIDE_EN)
        box.setObjectName("guide")
        lay.addWidget(box)
        row = QHBoxLayout()
        donate = QPushButton("\u2665 " + t("Donatie", lang))
        donate.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(DONATE_URL)))
        row.addWidget(donate)
        row.addStretch(1)
        close = QPushButton(t("Sluiten", lang))
        close.clicked.connect(self.accept)
        row.addWidget(close)
        lay.addLayout(row)


# ---------------------------------------------------------------------------
# Instellingen
# ---------------------------------------------------------------------------
class SettingsDialog(QDialog):
    def __init__(self, parent, cfg, lang):
        super().__init__(parent)
        self.cfg = cfg
        self.setWindowTitle(t("Instellingen\u2026", lang))
        self.resize(420, 200)
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel(t("Taal:", lang)))
        self.langbox = QComboBox()
        self.langbox.addItem(t("Automatisch (OS)", lang), "")
        self.langbox.addItem(t("Nederlands", lang), "nl")
        self.langbox.addItem(t("Engels", lang), "en")
        self.langbox.setCurrentIndex(
            {"": 0, "nl": 1, "en": 2}.get(cfg.get("lang", ""), 0))
        lay.addWidget(self.langbox)
        hint = QLabel(t("Sommige instellingen gaan pas in na herstarten.", lang)
                      if lang == "nl" else "Some settings apply after a restart.")
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        lay.addWidget(hint)
        lay.addStretch(1)
        row = QHBoxLayout()
        row.addStretch(1)
        ok = QPushButton("OK")
        ok.clicked.connect(self.accept)
        row.addWidget(ok)
        lay.addLayout(row)

    def result_cfg(self):
        self.cfg["lang"] = self.langbox.currentData()
        return self.cfg


# ---------------------------------------------------------------------------
# Hoofdvenster
# ---------------------------------------------------------------------------
class DraveCodex(QMainWindow):
    def __init__(self, cfg):
        super().__init__()
        self.cfg = cfg
        self.lang = _LANG
        self.folder = cfg.get("codex") or _default_codex()
        self.pages = []
        self.current = None      # Page in bewerking
        self.dirty = False
        self._loading = False

        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(app_icon())
        self.resize(1100, 720)

        central = QWidget()
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(self._header())
        outer.addWidget(self._toolbar())

        split = QSplitter(Qt.Orientation.Horizontal)
        split.addWidget(self._sidebar())
        split.addWidget(self._editor())
        split.setStretchFactor(0, 0)
        split.setStretchFactor(1, 1)
        split.setSizes([320, 780])
        outer.addWidget(split, 1)

        sb = QStatusBar()
        self.setStatusBar(sb)
        self.count_lbl = QLabel("")
        self.count_lbl.setObjectName("muted")
        sb.addWidget(self.count_lbl)
        sb.addPermanentWidget(QLabel("v" + APP_VERSION))
        donate = QToolButton()
        donate.setText("\u2665 " + t("Donatie", self.lang))
        donate.setObjectName("donate")
        donate.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(DONATE_URL)))
        sb.addPermanentWidget(donate)

        QShortcut(QKeySequence("Ctrl+S"), self, self.save_page)
        QShortcut(QKeySequence("Ctrl+N"), self, self.new_page)

        self._ensure_folder()
        self.reload(select_first=True)

    # ---- UI-opbouw ----
    def _header(self):
        w = QWidget()
        w.setObjectName("header")
        w.setFixedHeight(54)
        lay = QHBoxLayout(w)
        lay.setContentsMargins(14, 8, 14, 8)
        logo = QLabel()
        logo.setPixmap(logo_pixmap(32))
        lay.addWidget(logo)
        title = QLabel(APP_NAME)
        title.setObjectName("title")
        lay.addWidget(title)
        ver = QLabel("v" + APP_VERSION)
        ver.setObjectName("ver")
        lay.addWidget(ver)
        lay.addStretch(1)
        for label, slot in [(t("Instellingen\u2026", self.lang), self._settings),
                            (t("Snelgids", self.lang), self._guide),
                            (t("Over", self.lang), self._about)]:
            b = QPushButton(label)
            b.setObjectName("headerbtn")
            b.clicked.connect(lambda _=False, s=slot: s())
            lay.addWidget(b)
        return w

    def _toolbar(self):
        w = QWidget()
        w.setObjectName("toolbar")
        w.setFixedHeight(50)
        lay = QHBoxLayout(w)
        lay.setContentsMargins(12, 6, 12, 6)
        lay.setSpacing(8)

        self.b_new = QPushButton("\u002b  " + t("Nieuwe pagina", self.lang))
        self.b_new.setObjectName("primary")
        self.b_new.clicked.connect(self.new_page)
        lay.addWidget(self.b_new)

        self.b_save = QPushButton(t("Opslaan", self.lang))
        self.b_save.clicked.connect(self.save_page)
        lay.addWidget(self.b_save)

        self.b_del = QPushButton(t("Verwijderen", self.lang))
        self.b_del.clicked.connect(self.delete_page)
        lay.addWidget(self.b_del)

        lay.addWidget(self._sep())
        self.b_folder = QPushButton("\U0001f4c1  " + t("Map kiezen\u2026", self.lang))
        self.b_folder.clicked.connect(self.choose_folder)
        lay.addWidget(self.b_folder)

        lay.addStretch(1)
        return w

    def _sidebar(self):
        w = QWidget()
        w.setObjectName("sidebar")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(8)

        self.search = QLineEdit()
        self.search.setPlaceholderText(t("Zoeken\u2026", self.lang))
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self._refresh_list)
        lay.addWidget(self.search)

        self.catfilter = QComboBox()
        self.catfilter.addItem(t("Alle categorieen", self.lang), "")
        for c in CATEGORIES:
            self.catfilter.addItem(c, c)
        self.catfilter.currentIndexChanged.connect(self._refresh_list)
        lay.addWidget(self.catfilter)

        self.listw = QListWidget()
        self.listw.setObjectName("pagelist")
        self.listw.currentItemChanged.connect(self._on_select)
        lay.addWidget(self.listw, 1)
        return w

    def _editor(self):
        w = QWidget()
        w.setObjectName("editorpane")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(8)

        toprow = QHBoxLayout()
        self.title_edit = QLineEdit()
        self.title_edit.setObjectName("titleedit")
        self.title_edit.setPlaceholderText(t("Titel", self.lang))
        self.title_edit.textEdited.connect(self._mark_dirty)
        toprow.addWidget(self.title_edit, 1)

        toprow.addWidget(QLabel(t("Categorie:", self.lang)))
        self.cat_edit = QComboBox()
        for c in CATEGORIES:
            self.cat_edit.addItem(c, c)
        self.cat_edit.currentIndexChanged.connect(self._mark_dirty)
        toprow.addWidget(self.cat_edit)

        self.b_mode = QPushButton(t("Lezen", self.lang))
        self.b_mode.setCheckable(True)
        self.b_mode.toggled.connect(self._toggle_mode)
        toprow.addWidget(self.b_mode)
        lay.addLayout(toprow)

        self.stack = QStackedWidget()
        self.body_edit = QPlainTextEdit()
        self.body_edit.setObjectName("body")
        self.body_edit.setPlaceholderText(
            "[[Naam]] linkt naar een andere pagina. # Kop, **vet**, - lijst\u2026")
        self.body_edit.textChanged.connect(self._mark_dirty)
        self.preview = QTextBrowser()
        self.preview.setObjectName("preview")
        self.preview.setOpenLinks(False)
        self.preview.setOpenExternalLinks(False)
        self.preview.anchorClicked.connect(self._on_anchor)
        self.stack.addWidget(self.body_edit)
        self.stack.addWidget(self.preview)
        lay.addWidget(self.stack, 1)

        self.empty_hint = QLabel(t("Kies een pagina of maak een nieuwe.", self.lang))
        self.empty_hint.setObjectName("muted")
        lay.addWidget(self.empty_hint)
        return w

    def _sep(self):
        s = QFrame()
        s.setFrameShape(QFrame.Shape.VLine)
        s.setObjectName("sep")
        return s

    # ---- map / laden ----
    def _ensure_folder(self):
        try:
            os.makedirs(self.folder, exist_ok=True)
        except Exception as e:
            QMessageBox.warning(self, APP_NAME, str(e))

    def reload(self, select_first=False, select_slug=None):
        self.pages = load_pages(self.folder)
        self._refresh_list()
        if select_slug:
            self._select_slug(select_slug)
        elif select_first and self.listw.count():
            self.listw.setCurrentRow(0)
        else:
            self._show_current(None)
        self._update_count()

    def _refresh_list(self):
        q = (self.search.text() or "").strip().lower()
        cat = self.catfilter.currentData() if hasattr(self, "catfilter") else ""
        self.listw.blockSignals(True)
        keep = self.current.slug if self.current else None
        self.listw.clear()
        for p in sorted(self.pages, key=lambda x: x.title.lower()):
            if cat and p.category != cat:
                continue
            if q and q not in p.title.lower() and q not in p.body.lower():
                continue
            it = QListWidgetItem("%s\n%s" % (p.title or t("Naamloos", self.lang),
                                             p.category))
            it.setData(Qt.ItemDataRole.UserRole, p.slug)
            self.listw.addItem(it)
        self.listw.blockSignals(False)
        if keep:
            self._select_slug(keep, silent=True)
        if not self.pages:
            self.empty_hint.setText(
                t("Nog geen pagina's. Klik 'Nieuwe pagina'.", self.lang))

    def _select_slug(self, slug, silent=False):
        for i in range(self.listw.count()):
            if self.listw.item(i).data(Qt.ItemDataRole.UserRole) == slug:
                if silent:
                    self.listw.blockSignals(True)
                self.listw.setCurrentRow(i)
                if silent:
                    self.listw.blockSignals(False)
                return True
        return False

    def _page_by_slug(self, slug):
        for p in self.pages:
            if p.slug == slug:
                return p
        return None

    def _page_by_title(self, title):
        tl = (title or "").strip().lower()
        for p in self.pages:
            if p.title.strip().lower() == tl:
                return p
        return None

    # ---- selectie / weergave ----
    def _on_select(self, cur, _prev):
        if self._loading:
            return
        if not self._maybe_save_changes():
            return
        if cur is None:
            self._show_current(None)
            return
        slug = cur.data(Qt.ItemDataRole.UserRole)
        self._show_current(self._page_by_slug(slug))

    def _show_current(self, page):
        self._loading = True
        self.current = page
        has = page is not None
        self.title_edit.setEnabled(has)
        self.cat_edit.setEnabled(has)
        self.body_edit.setEnabled(has)
        self.b_mode.setEnabled(has)
        self.b_save.setEnabled(has)
        self.b_del.setEnabled(has)
        if has:
            self.title_edit.setText(page.title)
            idx = self.cat_edit.findData(page.category)
            self.cat_edit.setCurrentIndex(idx if idx >= 0 else 0)
            self.body_edit.setPlainText(page.body)
            self.empty_hint.setVisible(False)
            if self.b_mode.isChecked():
                self._render_preview()
        else:
            self.title_edit.clear()
            self.body_edit.clear()
            self.b_mode.setChecked(False)
            self.empty_hint.setVisible(True)
        self.dirty = False
        self._loading = False
        self._update_title()

    def _toggle_mode(self, on):
        self.b_mode.setText(t("Bewerken", self.lang) if on
                            else t("Lezen", self.lang))
        if on:
            self._render_preview()
            self.stack.setCurrentWidget(self.preview)
        else:
            self.stack.setCurrentWidget(self.body_edit)

    def _render_preview(self):
        md = self.body_edit.toPlainText()
        # [[Titel]] -> markdown-link met schema page:
        def repl(m):
            name = m.group(1).strip()
            return "[%s](page:%s)" % (name, QUrl.toPercentEncoding(name)
                                      .data().decode("ascii"))
        md = re.sub(r"\[\[([^\]]+)\]\]", repl, md)
        self.preview.setMarkdown(md)

    def _on_anchor(self, url):
        scheme = url.scheme()
        if scheme in ("http", "https", "mailto"):
            QDesktopServices.openUrl(url)
            return
        if scheme == "page":
            raw = url.toString()[5:]      # alles na 'page:'
            name = QUrl.fromPercentEncoding(raw.encode("ascii"))
            self._goto_title(name)

    def _goto_title(self, title):
        p = self._page_by_title(title)
        if p:
            if not self._maybe_save_changes():
                return
            self._select_slug(p.slug)
            return
        # bestaat niet -> aanbieden aan te maken
        r = QMessageBox.question(
            self, t("Pagina bestaat niet (nog niet aangemaakt):", self.lang),
            "%s\n\n%s   %s" % (title,
                               t("Pagina bestaat niet (nog niet aangemaakt):",
                                 self.lang), t("Aanmaken?", self.lang)),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if r == QMessageBox.StandardButton.Yes:
            self.new_page(title=title)

    # ---- bewerken ----
    def _mark_dirty(self, *_):
        if not self._loading:
            self.dirty = True
            self._update_title()

    def _maybe_save_changes(self):
        """Vraagt om opslaan bij niet-bewaarde wijzigingen. False = annuleren."""
        if not self.current or not self.dirty:
            return True
        r = QMessageBox.question(
            self, t("Niet-opgeslagen wijzigingen", self.lang),
            t("Wil je de wijzigingen opslaan?", self.lang),
            QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel)
        if r == QMessageBox.StandardButton.Save:
            return self.save_page()
        if r == QMessageBox.StandardButton.Cancel:
            return False
        self.dirty = False
        return True

    def new_page(self, _checked=False, title=""):
        if not self._maybe_save_changes():
            return
        p = Page(slug="", title=title or "", category="Overig", body="")
        self.current = p
        self._loading = True
        self.title_edit.setEnabled(True)
        self.cat_edit.setEnabled(True)
        self.body_edit.setEnabled(True)
        self.b_mode.setEnabled(True)
        self.b_save.setEnabled(True)
        self.b_del.setEnabled(True)
        self.b_mode.setChecked(False)
        self.title_edit.setText(p.title)
        self.cat_edit.setCurrentIndex(self.cat_edit.findData("Overig"))
        self.body_edit.setPlainText("")
        self.empty_hint.setVisible(False)
        self._loading = False
        self.dirty = bool(title)
        self.title_edit.setFocus()
        self._update_title()

    def save_page(self):
        if not self.current:
            return False
        title = self.title_edit.text().strip()
        if not title:
            QMessageBox.information(self, APP_NAME,
                                    t("Geef de pagina eerst een titel.", self.lang))
            self.title_edit.setFocus()
            return False
        p = self.current
        old_slug = p.slug
        p.title = title
        p.category = self.cat_edit.currentData() or "Overig"
        p.body = self.body_edit.toPlainText()
        new_slug = slugify(title)
        # uniek maken bij botsing met andere pagina
        existing = {x.slug for x in self.pages if x is not p}
        base = new_slug
        n = 2
        while new_slug in existing and new_slug != old_slug:
            new_slug = "%s-%d" % (base, n)
            n += 1
        p.slug = new_slug
        p.path = os.path.join(self.folder, new_slug + ".md")
        try:
            with open(p.path, "w", encoding="utf-8") as f:
                f.write(page_to_md(p))
            if old_slug and old_slug != new_slug:
                old_path = os.path.join(self.folder, old_slug + ".md")
                if os.path.exists(old_path):
                    os.remove(old_path)
        except Exception as e:
            QMessageBox.warning(self, APP_NAME, str(e))
            return False
        if p not in self.pages:
            self.pages.append(p)
        self.dirty = False
        self._refresh_list()
        self._select_slug(p.slug, silent=True)
        self.statusBar().showMessage(t("Opslaan", self.lang) + " \u2713", 2500)
        self._update_count()
        self._update_title()
        if self.b_mode.isChecked():
            self._render_preview()
        return True

    def delete_page(self):
        if not self.current:
            return
        r = QMessageBox.question(
            self, t("Pagina verwijderen?", self.lang),
            t("Weet je zeker dat je deze pagina wilt verwijderen?", self.lang),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if r != QMessageBox.StandardButton.Yes:
            return
        p = self.current
        try:
            if p.path and os.path.exists(p.path):
                os.remove(p.path)
        except Exception as e:
            QMessageBox.warning(self, APP_NAME, str(e))
            return
        if p in self.pages:
            self.pages.remove(p)
        self.current = None
        self.dirty = False
        self.reload(select_first=True)

    def choose_folder(self):
        if not self._maybe_save_changes():
            return
        path = QFileDialog.getExistingDirectory(
            self, t("Map kiezen\u2026", self.lang), self.folder)
        if not path:
            return
        self.folder = path
        self.cfg["codex"] = path
        save_config(self.cfg)
        self.current = None
        self.dirty = False
        self.reload(select_first=True)

    # ---- diversen ----
    def _update_count(self):
        n = len(self.pages)
        word = t("pagina", self.lang) if n == 1 else t("pagina's", self.lang)
        self.count_lbl.setText("%d %s  \u2014  %s" % (n, word, self.folder))

    def _update_title(self):
        mark = "*" if (self.current and self.dirty) else ""
        name = self.current.title if self.current else ""
        if name:
            self.setWindowTitle("%s \u2014 %s%s" % (APP_NAME, name, mark))
        else:
            self.setWindowTitle(APP_NAME)

    def _settings(self):
        dlg = SettingsDialog(self, dict(self.cfg), self.lang)
        if dlg.exec():
            self.cfg = dlg.result_cfg()
            save_config(self.cfg)

    def _guide(self):
        GuideDialog(self, self.lang).exec()

    def _about(self):
        QMessageBox.information(
            self, t("Over", self.lang),
            "%s v%s\n\nOffline campagne-wiki.\nDravenlock\n%s\n%s"
            % (APP_NAME, APP_VERSION, SUPPORT_MAIL, DONATE_URL))

    def closeEvent(self, ev):
        if not self._maybe_save_changes():
            ev.ignore()
            return
        ev.accept()


QSS = """
* { font-family: 'Segoe UI', sans-serif; font-size: 15px; color: %(silver)s; }
QMainWindow, QWidget { background: %(bg)s; }
#header { background: %(panel)s; border-bottom: 1px solid #23232b; }
#title { font-size: 19px; font-weight: 700; }
#ver { color: %(mute)s; font-size: 12px; }
#toolbar { background: %(bg)s; border-bottom: 1px solid #23232b; }
#sidebar { background: %(panel)s; border-right: 1px solid #23232b; }
QPushButton { background: %(panel)s; border: 1px solid #2c2c36; border-radius: 8px;
              padding: 8px 13px; color: %(silver)s; }
QPushButton:hover { border-color: %(accent)s; }
QPushButton:disabled { color: #5a5a63; border-color: #23232b; }
QPushButton#primary { background: %(accent)s; color: #08131f; font-weight: 700;
                      border: none; }
QPushButton#primary:hover { background: #87b6e3; }
QPushButton#headerbtn { padding: 6px 11px; }
QToolButton#donate { border: none; background: transparent; color: %(accent)s; }
QFrame#sep { color: #2c2c36; }
#muted, #hint { color: %(mute)s; font-size: 13px; }
QLineEdit, QComboBox, QPlainTextEdit, QTextBrowser {
    background: #1a1a20; border: 1px solid #2c2c36; border-radius: 8px;
    padding: 8px; color: %(silver)s; selection-background-color: %(accent)s;
    selection-color: #08131f; }
QLineEdit:focus, QComboBox:focus, QPlainTextEdit:focus { border-color: %(accent)s; }
QLineEdit#titleedit { font-size: 18px; font-weight: 700; }
QPlainTextEdit#body, QTextBrowser#preview { font-size: 16px; }
QListWidget#pagelist { background: #1a1a20; border: 1px solid #2c2c36;
    border-radius: 8px; padding: 4px; }
QListWidget#pagelist::item { padding: 9px 8px; border-radius: 6px; color: %(silver)s; }
QListWidget#pagelist::item:selected { background: #26323f; color: #ffffff;
    font-weight: 700; border-left: 3px solid %(accent)s; }
QListWidget#pagelist::item:hover { background: #23232c; }
QComboBox QAbstractItemView { background: #1a1a20; color: %(silver)s;
    selection-background-color: %(accent)s; selection-color: #08131f; }
QTextBrowser#guide { background: %(panel)s; }
QStatusBar { background: %(panel)s; }
QSplitter::handle { background: #23232b; }
QDialog { background: %(bg)s; }
""" % {"bg": BG, "panel": PANEL, "silver": SILVER, "mute": MUTE,
       "accent": ACCENT, "warn": WARN}


def _install_excepthook():
    import traceback

    def hook(exctype, value, tb):
        msg = "".join(traceback.format_exception(exctype, value, tb))
        try:
            with open(os.path.join(_app_dir(), "dravecodex-fout.txt"),
                      "w", encoding="utf-8") as f:
                f.write(msg)
        except Exception:
            pass
        try:
            if QApplication.instance():
                QMessageBox.critical(None, "DraveCodex - fout",
                                     "Er ging iets mis:\n\n" + msg[-1500:]
                                     + "\n\n(Ook opgeslagen in dravecodex-fout.txt)")
        except Exception:
            pass
        sys.__excepthook__(exctype, value, tb)

    sys.excepthook = hook


def main():
    global _LANG
    _install_excepthook()
    app = QApplication(sys.argv)
    try:
        cfg = load_config()
        _LANG = detect_lang(cfg)
        app.setStyleSheet(QSS)
        win = DraveCodex(cfg)
        win.show()
    except Exception:
        sys.excepthook(*sys.exc_info())
        return
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
