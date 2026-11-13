# encoding: utf-8
"""CapTension Palette 的多語系字串（简体中文 / 繁體中文 / English）。

預設跟隨 Glyphs 介面語言。若要固定語言，可在 Macro Panel 設定：

    Glyphs.defaults["ptlg.CapTension.language"] = "zh-Hans"

可接受 "zh-Hans"、"zh-Hant"、"en"，也接受 zh_CN、zh_TW、en_US 等別名。
刪除該鍵即恢復跟隨 Glyphs 介面語言：

    del Glyphs.defaults["ptlg.CapTension.language"]
"""

from GlyphsApp import Glyphs

from batch_instructions import TEXT_EN, TEXT_ZH_HANS, TEXT_ZH_HANT

LANGUAGE_KEY = "ptlg.CapTension.language"
LANGUAGES = ("zh-Hans", "zh-Hant", "en")

# Glyphs.localize 以介面語言比對鍵；多列幾種寫法，避免不同版本用不同標記。
_LOCALIZE_KEYS = {
    "en": ("en", "en-US", "en_US", "Base"),
    "zh-Hans": ("zh-Hans", "zh_Hans", "zh-CN", "zh_CN", "zh-Hans-CN"),
    "zh-Hant": ("zh-Hant", "zh_Hant", "zh-TW", "zh_TW", "zh-HK", "zh_HK",
                "zh-Hant-TW", "zh-Hant-HK"),
}

_TABLE = {
    "reset": {
        "en": "Reset to Round",
        "zh-Hans": "重设到圆形",
        "zh-Hant": "重設到圓形",
    },
    "apply": {
        "en": "Apply to Selection",
        "zh-Hans": "套用到选取",
        "zh-Hant": "套用到選取",
    },
    "clear": {
        "en": "Clear",
        "zh-Hans": "清除",
        "zh-Hant": "清除",
    },
    "copy_batch": {
        "en": "Copy Batch Instructions",
        "zh-Hans": "复制批处理说明",
        "zh-Hant": "複製批次處理說明",
    },
    "selected_prefix": {
        "en": "Selected: ",
        "zh-Hans": "目前选取：",
        "zh-Hant": "目前選取：",
    },
    "not_applied": {
        "en": "Not applied",
        "zh-Hans": "未套用",
        "zh-Hant": "未套用",
    },
    "multiple_values": {
        "en": "Multiple values",
        "zh-Hans": "多个值",
        "zh-Hant": "多個值",
    },
    "no_value": {
        "en": "—",
        "zh-Hans": "—",
        "zh-Hant": "—",
    },
    "select_prompt": {
        "en": "Select endpoint(s) or path(s) first.",
        "zh-Hans": "请先选取端点或路径",
        "zh-Hant": "請先選取端點或路徑",
    },
    "cleared": {
        "en": "Cleared %d cap(s).",
        "zh-Hans": "清除 %d 个端帽",
        "zh-Hant": "清除 %d 個端帽",
    },
    "log_apply": {
        "en": "shape=%s, added=%d, removed=%d, kept=%d",
        "zh-Hans": "shape=%s，新增=%d，移除=%d，保留=%d",
        "zh-Hant": "shape=%s，新增=%d，移除=%d，保留=%d",
    },
    "err_read_font_ud": {
        "en": "Could not read font.userData",
        "zh-Hans": "读取 font.userData 失败",
        "zh-Hant": "讀取 font.userData 失敗",
    },
    "err_read_defaults": {
        "en": "Could not read Glyphs.defaults",
        "zh-Hans": "读取 Glyphs.defaults 失败",
        "zh-Hant": "讀取 Glyphs.defaults 失敗",
    },
    "err_write_font_ud": {
        "en": "Could not write font.userData",
        "zh-Hans": "写入 font.userData 失败",
        "zh-Hant": "寫入 font.userData 失敗",
    },
    "err_write_defaults": {
        "en": "Could not write Glyphs.defaults",
        "zh-Hans": "写入 Glyphs.defaults 失败",
        "zh-Hant": "寫入 Glyphs.defaults 失敗",
    },
    "err_update": {
        "en": "Live update failed",
        "zh-Hans": "实时更新失败",
        "zh-Hant": "即時更新失敗",
    },
}


def normalize_language(value):
    """把語言標記正規化成 zh-Hans / zh-Hant / en；auto 回傳 None。"""
    if value is None:
        return None
    try:
        tag = str(value).strip().replace("_", "-").lower()
    except Exception:
        return None
    if not tag or tag in ("auto", "system", "default"):
        return None
    if tag == "zh" or tag.startswith("zh-hans") or tag.startswith("zh-cn") \
            or tag.startswith("zh-sg"):
        return "zh-Hans"
    if tag.startswith("zh-hant") or tag.startswith("zh-tw") \
            or tag.startswith("zh-hk") or tag.startswith("zh-mo"):
        return "zh-Hant"
    if tag.startswith("en"):
        return "en"
    return None


def active_language():
    """回傳使用者在 Glyphs.defaults 指定的語言；None 代表跟隨介面語言。"""
    try:
        raw = Glyphs.defaults.get(LANGUAGE_KEY)
    except Exception:
        raw = None
    return normalize_language(raw)


def language_key():
    """回傳目前的語言狀態鍵，供介面判斷是否需要重新翻譯。"""
    return active_language()


def _localize(values):
    table = {}
    for lang, aliases in _LOCALIZE_KEYS.items():
        text = values.get(lang)
        if text is None:
            continue
        for alias in aliases:
            table.setdefault(alias, text)
    try:
        result = Glyphs.localize(table)
    except Exception:
        result = None
    if result:
        return result
    # 介面語言不在清單內時，Glyphs 通常會退回 en；這裡再保險一次。
    return values["en"]


def t(key):
    values = _TABLE.get(key)
    if not values:
        return key
    language = active_language()
    if language is not None:
        return values.get(language) or values["en"]
    return _localize(values)


def batch_text():
    values = {
        "en": TEXT_EN,
        "zh-Hans": TEXT_ZH_HANS,
        "zh-Hant": TEXT_ZH_HANT,
    }
    language = active_language()
    if language is not None:
        return values[language]
    return _localize(values)
