# Extended Styles - extension for Stable Diffusion Forge / Forge Neo / A1111
#
# Placeholders in the CSV template:
#   {prompt}                       classic, single placeholder
#   {prompt1} {prompt2} ...        numbered
#   {prompt_face} ...              named (text field)
#   {prompt_Gender=Male|Female}    choice VARIABLE -> dropdown menu
#
# Variables: the FIRST occurrence of "_Name=opt1|opt2" creates the dropdown (the options are
# the labels). Later occurrences with the same _Name use the CHOSEN INDEX and insert their own
# option at the same position (commas inside an option go into the prompt). Index out of range -> empty.
# Controls render in the order the placeholders appear in the prompt (text fields and menus interleaved).
#
# You fill the values INSIDE this panel, so it also works with third-party prompt editors
# (e.g. prompt-all-in-one): the substitution happens at generation time.

import os
import re
import csv
import json
import shutil
import gradio as gr
import modules.scripts as scripts

MAXSLOTS = 12  # max placeholders per style (each slot = a text box OR a menu)

# ------------------------------------------------------------------ global state
BASEDIR = scripts.basedir()
CONFIG_PATH = os.path.join(BASEDIR, "config.json")
STYLES = {}   # { category: { name: {"pos": str, "neg": str} } }
FILES = {}    # { category: path_of_the_csv_file }
PREVIEW_DIR = os.path.join(BASEDIR, "previews")  # style preview thumbnails

# placeholder: group1 = name (_Name / number / empty) ; group2 = "=opt1|opt2" (optional)
PH_RE = r"\{prompt(_[A-Za-z0-9-]+|\d*)(=[^}]*)?\}"
TAG_RE = r"<\s*([A-Za-z0-9_-]+)\s*:\s*([^>]*)>"    # optional <name: ...> in the prompt

def default_folder():
    return os.path.join(BASEDIR, "styles")

def _load_cfg():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception:
        return {}

def _save_cfg(cfg):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f)
    except Exception:
        pass

def get_folder():
    return _load_cfg().get("folder") or default_folder()

def save_folder(folder):
    cfg = _load_cfg(); cfg["folder"] = folder; _save_cfg(cfg)

# ------------------------------------------------------------------ CSV loading
def scan_styles(folder):
    STYLES.clear()
    FILES.clear()
    if not folder or not os.path.isdir(folder):
        return
    for fname in sorted(os.listdir(folder)):
        if not fname.lower().endswith(".csv"):
            continue
        cat = os.path.splitext(fname)[0]
        path = os.path.join(folder, fname)
        try:
            with open(path, "r", encoding="utf-8-sig", newline="") as f:
                rows = list(csv.reader(f))
        except Exception:
            continue
        FILES[cat] = path
        if not rows:
            STYLES[cat] = {}
            continue
        start = 0
        head = [c.strip().lower() for c in rows[0]]
        if head and head[0] == "name" and len(head) > 1 and head[1].startswith("prompt"):
            start = 1
        entries = {}
        for r in rows[start:]:
            if not r:
                continue
            name = (r[0] if len(r) > 0 else "").strip()
            if re.match(r"^-{2,}.*-{2,}$", name):   # separator/category row (----XXX----): not a style
                continue
            pos  = (r[1] if len(r) > 1 else "")
            neg  = (r[2] if len(r) > 2 else "")
            if not name and not pos:
                continue
            entries[name or "(unnamed)"] = {"pos": pos, "neg": neg}
        STYLES[cat] = entries

def style_choices(cat):
    return list(STYLES.get(cat, {}).keys())

# ------------------------------------------------------------------ placeholders / merge
def _key_from_raw(raw):
    if raw == "":
        return "_"
    if raw.startswith("_"):
        return raw[1:]
    return raw

def display_label(key):
    # a hyphen in the placeholder name is shown as a space in the field label
    return "prompt" if key == "_" else key.replace("-", " ")

def _split_opts(opts_raw):
    # opts_raw = "=a|b|c" -> ["a","b","c"]
    return [o.strip() for o in opts_raw[1:].split("|")]

def analyze(pos, neg=""):
    """Return (order, choice_vars). order = [(kind, key)] of the unique placeholders IN PROMPT ORDER
    (kind = 'text' or 'choice'). choice_vars = {key: master options}."""
    order, seen, choice_vars = [], set(), {}
    for tpl in (pos, neg):
        for m in re.finditer(PH_RE, tpl or ""):
            key = _key_from_raw(m.group(1))
            opts = m.group(2)
            if opts is not None and key not in choice_vars:
                choice_vars[key] = _split_opts(opts)     # first occurrence with options = master
            if key not in seen:
                seen.add(key)
                order.append(key)                        # position = first appearance
    order = [("choice" if k in choice_vars else "text", k) for k in order]
    return order, choice_vars

def analyze_style(cat, name):
    s = STYLES.get(cat, {}).get(name)
    if not s:
        return [], {}
    return analyze(s["pos"], s["neg"])

def fill(tpl, text_vals, choice_index):
    if not tpl:
        return ""
    def repl(m):
        key = _key_from_raw(m.group(1))
        opts = m.group(2)
        if opts is not None:                       # choice variable: use the index
            options = _split_opts(opts)
            idx = choice_index.get(key, 0)
            return options[idx] if 0 <= idx < len(options) else ""
        if key in choice_index:                    # bare occurrence of a variable
            return ""
        v = text_vals.get(key, "")                 # text field
        return v if v.strip() else ""
    out = re.sub(PH_RE, repl, tpl)
    out = re.sub(r"[ \t]{2,}", " ", out)            # collapse extra spaces
    out = re.sub(r"\s+([,.;])", r"\1", out)          # no space before , . ;
    out = re.sub(r"([,;])(?:\s*[,;])+", r"\1", out)  # collapse repeated , or ;
    out = re.sub(r"^[\s,;]+", "", out)               # trim leading punctuation/space
    out = re.sub(r"[\s,;]+$", "", out)               # trim trailing punctuation/space
    return out.strip()

def _collect(cat, style, vals):
    """From (cat, style, control values) build text_vals and choice_index.
    vals = [textboxes...MAXSLOTS] + [menus...MAXSLOTS]; slot i uses its textbox or its menu."""
    s = STYLES.get(cat, {}).get(style)
    if not s:
        return None, {}, {}
    text_list = vals[:MAXSLOTS]
    choice_list = vals[MAXSLOTS:2 * MAXSLOTS]
    order, choice_vars = analyze(s["pos"], s["neg"])
    text_vals, choice_index = {}, {}
    for i, (kind, key) in enumerate(order):
        if i >= MAXSLOTS:
            break
        if kind == "text":
            v = (text_list[i] or "").strip()
            if v:
                text_vals[key] = v
        else:
            opts = choice_vars[key]
            label = choice_list[i] if i < len(choice_list) else None
            choice_index[key] = opts.index(label) if (label in opts) else 0
    return s, text_vals, choice_index

def build_results(cat, style, *vals):
    """Return (final prompt, final negative) from the control values."""
    s, text_vals, choice_index = _collect(cat, style, vals)
    if not s:
        return "", ""
    return fill(s["pos"], text_vals, choice_index), fill(s["neg"], text_vals, choice_index)

def default_results(cat, name):
    return list(build_results(cat, name, *([""] * MAXSLOTS + [None] * MAXSLOTS)))

def control_updates(cat, name):
    """Per-slot updates: textbox (MAXSLOTS) + menu (MAXSLOTS). Each slot shows the right control
    (textbox if text, menu if variable), preserving the placeholder order in the prompt."""
    order, choice_vars = analyze_style(cat, name)
    text_ups, drop_ups = [], []
    for i in range(MAXSLOTS):
        if i < len(order):
            kind, key = order[i]
            if kind == "text":
                text_ups.append(gr.update(visible=True, label=display_label(key), value=""))
                drop_ups.append(gr.update(visible=False, choices=[], value=None))
            else:
                opts = choice_vars[key]
                text_ups.append(gr.update(visible=False, value=""))
                drop_ups.append(gr.update(visible=True, label=display_label(key),
                                          choices=opts, value=(opts[0] if opts else None)))
        else:
            text_ups.append(gr.update(visible=False, value=""))
            drop_ups.append(gr.update(visible=False, choices=[], value=None))
    return text_ups + drop_ups

def translate_text(text, target="en"):
    """Translate text (auto -> target) via the free Google Translate endpoint."""
    text = (text or "").strip()
    if not text:
        return text
    import requests
    url = "https://translate.googleapis.com/translate_a/single"
    params = {"client": "gtx", "sl": "auto", "tl": target, "dt": "t", "q": text}
    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    data = r.json()
    return "".join(seg[0] for seg in data[0] if seg and seg[0])

def translate_many(texts, target="en"):
    """Translate several texts in ONE request (avoids rate-limiting)."""
    if not texts:
        return []
    joined = "\n".join(texts)
    res = translate_text(joined, target)
    parts = res.split("\n")
    if len(parts) == len(texts):
        return parts
    return [translate_text(t, target) for t in texts]  # fallback

def js_set_prompts(pos_id, neg_id):
    """JS: write prompt and negative into the native boxes (notifying Gradio / prompt-all-in-one).
    The negative is only written when the style has one, so the user's own negative isn't wiped."""
    return (
        "(p, n) => {"
        "  const root = (typeof gradioApp !== 'undefined') ? gradioApp() : document;"
        "  function setv(id, v) {"
        "    const el = (root.querySelector('#' + id + ' textarea') || document.querySelector('#' + id + ' textarea'));"
        "    if (el && typeof v === 'string') {"
        "      el.value = v;"
        "      el.dispatchEvent(new Event('input', { bubbles: true }));"
        "      el.dispatchEvent(new Event('change', { bubbles: true }));"
        "    }"
        "  }"
        "  setv('%s', p);"
        "  if (n && n.length) setv('%s', n);"
        "  return [];"
        "}" % (pos_id, neg_id)
    )

# ------------------------------------------------------------------ save / delete style
def save_style(folder, cat, name, pos, neg):
    """Save (or update by name) a style into a .csv file. Returns (ok, message)."""
    name = (name or "").strip()
    if not name:
        return False, "Error: style name is required."
    if not (pos or "").strip():
        return False, "Error: the prompt is empty."

    path = FILES.get(cat)
    if not path:
        if not folder or not os.path.isdir(folder):
            return False, "Error: invalid folder."
        fn = cat if cat.lower().endswith(".csv") else (cat + ".csv")
        path = os.path.join(folder, fn)

    rows = []
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8-sig", newline="") as f:
                rows = list(csv.reader(f))
        except Exception as e:
            return False, "Error reading file: %s" % e

    start = 0
    header = ["name", "prompt", "negative_prompt"]
    if rows:
        h = [c.strip().lower() for c in rows[0]]
        if h and h[0] == "name" and len(h) > 1 and h[1].startswith("prompt"):
            header = rows[0]
            start = 1
    data = rows[start:]

    updated = False
    for r in data:
        if r and (r[0] or "").strip() == name:
            while len(r) < 3:
                r.append("")
            r[1] = pos
            r[2] = neg
            updated = True
            break
    if not updated:
        data.append([name, pos, neg])

    try:
        if os.path.isfile(path):
            shutil.copy2(path, path + ".bak")
    except Exception:
        pass

    try:
        with open(path, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(header)
            for r in data:
                w.writerow(r)
    except Exception as e:
        return False, "Error writing file: %s" % e

    verb = "updated" if updated else "saved"
    return True, "Style \"%s\" %s in %s" % (name, verb, os.path.basename(path))

def delete_style(folder, cat, name):
    """Delete a style (by name) from a .csv file. Returns (ok, message). Makes a .bak backup."""
    name = (name or "").strip()
    if not name:
        return False, "Error: no style selected."
    path = FILES.get(cat)
    if not path or not os.path.isfile(path):
        return False, "Error: file not found."
    try:
        with open(path, "r", encoding="utf-8-sig", newline="") as f:
            rows = list(csv.reader(f))
    except Exception as e:
        return False, "Error reading file: %s" % e

    start = 0
    header = ["name", "prompt", "negative_prompt"]
    if rows:
        h = [c.strip().lower() for c in rows[0]]
        if h and h[0] == "name" and len(h) > 1 and h[1].startswith("prompt"):
            header = rows[0]
            start = 1
    data = rows[start:]
    new_data = [r for r in data if not (r and (r[0] or "").strip() == name)]
    if len(new_data) == len(data):
        return False, "Style \"%s\" not found." % name

    try:
        shutil.copy2(path, path + ".bak")
    except Exception:
        pass
    try:
        with open(path, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(header)
            for r in new_data:
                w.writerow(r)
    except Exception as e:
        return False, "Error writing file: %s" % e

    return True, "Style \"%s\" deleted from %s" % (name, os.path.basename(path))

# ------------------------------------------------------------------ previews (thumbnails)
def _safe(s):
    return re.sub(r"[^A-Za-z0-9_-]+", "_", s or "")

def preview_path(cat, name):
    return os.path.join(PREVIEW_DIR, "%s__%s.png" % (_safe(cat), _safe(name)))

def make_placeholder(name):
    """Gray tile with the name, for styles without a preview."""
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (200, 200), (58, 58, 64))
    d = ImageDraw.Draw(img)
    lines, line = [], ""
    for w in (name or "").split():
        if len(line) + len(w) + 1 > 16:
            lines.append(line); line = w
        else:
            line = (line + " " + w).strip()
    if line:
        lines.append(line)
    lines = lines[:6]
    y = 100 - len(lines) * 7
    for ln in lines:
        d.text((10, y), ln[:22], fill=(205, 205, 210))
        y += 14
    return img

def gallery_items(cat):
    items = []
    for name in style_choices(cat):
        p = preview_path(cat, name)
        items.append((p if os.path.isfile(p) else make_placeholder(name), name))
    return items

def _src_to_local(src):
    """From a src like '.../file=C:/.../img.png?...' extract the local path."""
    import urllib.parse
    if not src:
        return None
    i = src.find("file=")
    if i != -1:
        p = src[i + 5:].split("&")[0].split("?")[0]
        return urllib.parse.unquote(p)
    return None

def save_preview_image(cat, name, image):
    """image: file path or PIL object. Saves the style thumbnail."""
    from PIL import Image
    os.makedirs(PREVIEW_DIR, exist_ok=True)
    img = Image.open(image) if isinstance(image, str) else image
    img = img.convert("RGB")
    img.thumbnail((256, 256))
    img.save(preview_path(cat, name), "PNG")

def js_get_last_image(gid):
    """JS: read the src of the last image shown in the output gallery."""
    return (
        "(c, s, _) => {"
        "  const root = (typeof gradioApp!=='undefined')?gradioApp():document;"
        "  const g = root.querySelector('#%s');"
        "  let img = null;"
        "  if (g) {"
        "    img = g.querySelector('.preview img') || g.querySelector('button.selected img');"
        "    if (!img) { const a = g.querySelectorAll('img'); if (a.length) img = a[a.length-1]; }"
        "  }"
        "  return [c, s, img ? img.src : ''];"
        "}" % gid
    )

# ------------------------------------------------------------------ Gradio Script
class ExtendedStyles(scripts.Script):
    def title(self):
        return "Extended styles"

    def show(self, is_img2img):
        return scripts.AlwaysVisible

    def ui(self, is_img2img):
        scan_styles(get_folder())
        cats = list(STYLES.keys())
        c0 = cats[0] if cats else None
        s0 = style_choices(c0)[0] if style_choices(c0) else None

        with gr.Accordion("Extended styles", open=False):
            enabled = gr.Checkbox(value=False, label="Enable extended styles (rewrites the prompt at generation)")
            with gr.Row():
                folder = gr.Textbox(value=get_folder(), label="CSV folder", scale=4)
                reload_btn = gr.Button("Reload", scale=1)
            with gr.Row():
                cat = gr.Dropdown(choices=cats, value=c0, label="Category")
                style = gr.Dropdown(choices=style_choices(c0), value=s0, label="Template")

            gal_id = "extended_styles_gallery_i2i" if is_img2img else "extended_styles_gallery_t2i"
            gallery = gr.Gallery(value=gallery_items(c0), label="Style previews (click to select)",
                                 columns=4, height="auto", object_fit="cover", allow_preview=False,
                                 elem_id=gal_id)
            slider_id = "es_size_slider_i2i" if is_img2img else "es_size_slider_t2i"
            # the slider is handled client-side (javascript/extended_styles.js) via localStorage
            gr.Slider(minimum=50, maximum=200, value=150, step=5,
                      label="Thumbnail size (px)", elem_id=slider_id)

            nsfw_id = "es_nsfw_i2i" if is_img2img else "es_nsfw_t2i"
            gr.Checkbox(value=False, label="Blur NSFW previews (styles with \"NSFW\" in the name)",
                        elem_id=nsfw_id)   # handled client-side (javascript/extended_styles.js)

            gr.Markdown("Fill in the fields and menus below: the **final prompt** is built and used at "
                        "generation (you can leave the main prompt box empty).")

            init_order, init_choice_vars = analyze_style(c0, s0)

            # one "slot" per position: a textbox + a menu, created together; only one is shown.
            # This way the visual order matches the placeholder order in the prompt.
            fields, choices = [], []
            for i in range(MAXSLOTS):
                kind, key = init_order[i] if i < len(init_order) else (None, None)
                if kind == "text":
                    fields.append(gr.Textbox(label=display_label(key), visible=True, value=""))
                    choices.append(gr.Dropdown(label="", choices=[], value=None, visible=False))
                elif kind == "choice":
                    opts = init_choice_vars[key]
                    fields.append(gr.Textbox(label="", visible=False, value=""))
                    choices.append(gr.Dropdown(label=display_label(key), choices=opts,
                                               value=(opts[0] if opts else None), visible=True))
                else:
                    fields.append(gr.Textbox(label="", visible=False, value=""))
                    choices.append(gr.Dropdown(label="", choices=[], value=None, visible=False))

            ctrls = fields + choices   # inputs/outputs: all textboxes first, then all menus

            with gr.Row():
                tr_btn = gr.Button("Translate fields to English")
                write_btn = gr.Button("Write to main prompt", variant="primary")
            tr_status = gr.Markdown("")

            # hidden previews: sources for "Write to main prompt" (prompt and negative)
            _r0 = default_results(c0, s0)
            result = gr.Textbox(value=_r0[0], visible=False)
            result_neg = gr.Textbox(value=_r0[1], visible=False)

            write_btn.click(None, inputs=[result, result_neg], outputs=[],
                            _js=js_set_prompts("img2img_prompt" if is_img2img else "txt2img_prompt",
                                               "img2img_neg_prompt" if is_img2img else "txt2img_neg_prompt"))

            # translate only the text boxes (menus are not translated)
            def on_translate(c, s, *vals):
                text_list = list(vals[:MAXSLOTS])
                choice_list = list(vals[MAXSLOTS:2 * MAXSLOTS])
                order, _ = analyze_style(c, s)
                text_slots = [i for i in range(min(len(order), MAXSLOTS)) if order[i][0] == "text"]
                idxs = [i for i in text_slots if (text_list[i] or "").strip()]
                msg = "Nothing to translate." if not idxs else "Translated to English."
                if idxs:
                    try:
                        translated = translate_many([text_list[i] for i in idxs])
                        for j, i in enumerate(idxs):
                            text_list[i] = translated[j]
                    except Exception:
                        msg = "Translation failed (connection?)."
                np_, nn_ = build_results(c, s, *(text_list + choice_list))
                return [gr.update(value=o) for o in text_list] + [np_, nn_, msg]
            tr_btn.click(on_translate, inputs=[cat, style] + ctrls,
                         outputs=fields + [result, result_neg, tr_status])

            # category change -> template, controls, preview and gallery
            def on_cat(c):
                ch = style_choices(c)
                ns = ch[0] if ch else None
                return ([gr.update(choices=ch, value=ns)] + control_updates(c, ns)
                        + default_results(c, ns) + [gallery_items(c)])
            cat.change(on_cat, inputs=[cat], outputs=[style] + ctrls + [result, result_neg, gallery])

            def on_style(c, s):
                return control_updates(c, s) + default_results(c, s)
            style.change(on_style, inputs=[cat, style], outputs=ctrls + [result, result_neg])

            # click on a thumbnail -> select that style
            def on_gallery_select(c, evt: gr.SelectData):
                ch = style_choices(c)
                if evt.index is None or evt.index >= len(ch):
                    return ([gr.update()] + [gr.update() for _ in range(2 * MAXSLOTS)]
                            + [gr.update(), gr.update()])
                s = ch[evt.index]
                return [gr.update(value=s)] + control_updates(c, s) + default_results(c, s)
            gallery.select(on_gallery_select, inputs=[cat], outputs=[style] + ctrls + [result, result_neg])

            def on_reload(f):
                save_folder(f)
                scan_styles(f)
                cs = list(STYLES.keys())
                nc = cs[0] if cs else None
                ch = style_choices(nc)
                ns = ch[0] if ch else None
                return ([gr.update(choices=cs, value=nc), gr.update(choices=ch, value=ns)]
                        + control_updates(nc, ns) + default_results(nc, ns) + [gallery_items(nc)])
            reload_btn.click(on_reload, inputs=[folder],
                             outputs=[cat, style] + ctrls + [result, result_neg, gallery])

            # live update of prompt and negative while filling in
            for comp in ctrls:
                comp.change(build_results, inputs=[cat, style] + ctrls, outputs=[result, result_neg])

            # ---------------------------------------------------------- set style preview
            with gr.Accordion("Set style preview", open=False):
                gr.Markdown("Select the style (menu or carousel), then **generate** an image and press "
                            "**Apply last generation**. Alternatively drag an image and press "
                            "**Apply uploaded image**. Previews are saved in `previews/`.")
                img_src = gr.Textbox(visible=False)
                apply_auto_btn = gr.Button("Apply last generation", variant="primary")
                prev_upload = gr.Image(label="...or drag an image here", type="filepath")
                apply_manual_btn = gr.Button("Apply uploaded image")
                prev_status = gr.Markdown("")

                def on_apply_auto(c, s, src):
                    if not s:
                        return gr.update(), "Select a style first."
                    try:
                        if src and src.startswith("data:"):
                            import base64
                            from io import BytesIO
                            from PIL import Image
                            img = Image.open(BytesIO(base64.b64decode(src.split(",", 1)[1])))
                            save_preview_image(c, s, img)
                        else:
                            path = _src_to_local(src)
                            if not path or not os.path.isfile(path):
                                return gr.update(), "No image found: generate an image first."
                            save_preview_image(c, s, path)
                    except Exception as e:
                        return gr.update(), "Error: %s" % e
                    return gr.update(value=gallery_items(c)), "Preview saved for \"%s\"." % s
                apply_auto_btn.click(on_apply_auto, inputs=[cat, style, img_src],
                                     outputs=[gallery, prev_status],
                                     _js=js_get_last_image("img2img_gallery" if is_img2img else "txt2img_gallery"))

                def on_apply_manual(c, s, img):
                    if not s:
                        return gr.update(), "Select a style first."
                    if not img:
                        return gr.update(), "No image uploaded."
                    try:
                        save_preview_image(c, s, img)
                    except Exception as e:
                        return gr.update(), "Error: %s" % e
                    return gr.update(value=gallery_items(c)), "Preview saved for \"%s\"." % s
                apply_manual_btn.click(on_apply_manual, inputs=[cat, style, prev_upload],
                                       outputs=[gallery, prev_status])

            # ---------------------------------------------------------- create / edit style
            with gr.Accordion("Create / edit style", open=False):
                gr.Markdown("Pick a **category** and the **style to edit**: the fields below fill in "
                            "automatically. To create a new one, press **New** and type. "
                            "Choice variables: `{prompt_Gender=Male|Female}` (later occurrences with the "
                            "same name follow the index). If the name exists it is **updated**; "
                            "**Delete style** removes the one selected in \"Style to edit\" "
                            "(a `.bak` backup is made before writing).")
                with gr.Row():
                    edit_cat = gr.Dropdown(choices=cats, value=c0, label="Category to edit")
                    edit_style = gr.Dropdown(choices=style_choices(c0), value=s0, label="Style to edit")
                save_file = gr.Dropdown(choices=cats, value=c0, label="Save to file")
                save_name = gr.Textbox(label="Style name", placeholder="e.g. Girl with flower")
                save_pos = gr.Textbox(label="Prompt", lines=3,
                                      placeholder="a girl {prompt_face} with {prompt_Gender=he|she}...")
                save_neg = gr.Textbox(label="Negative prompt (optional)", lines=2)
                with gr.Row():
                    new_btn = gr.Button("New (clear the fields)")
                    save_btn = gr.Button("Save style", variant="primary")
                    delete_btn = gr.Button("Delete style")
                save_status = gr.Markdown("")

                def load_for_edit(c, s):
                    st = STYLES.get(c, {}).get(s)
                    if not st:
                        return gr.update(value=c), gr.update(value=(s or "")), gr.update(value=""), gr.update(value="")
                    return gr.update(value=c), gr.update(value=s), gr.update(value=st["pos"]), gr.update(value=st["neg"])

                def on_edit_cat(c):
                    ch = style_choices(c)
                    ns = ch[0] if ch else None
                    return [gr.update(choices=ch, value=ns)] + list(load_for_edit(c, ns))
                edit_cat.change(on_edit_cat, inputs=[edit_cat],
                                outputs=[edit_style, save_file, save_name, save_pos, save_neg])
                edit_style.change(load_for_edit, inputs=[edit_cat, edit_style],
                                  outputs=[save_file, save_name, save_pos, save_neg])

                def on_new():
                    return gr.update(value=""), gr.update(value=""), gr.update(value="")
                new_btn.click(on_new, outputs=[save_name, save_pos, save_neg])

                def on_save(f, target, name, pos, neg):
                    ok, msg = save_style(f, target, name, pos, neg)
                    scan_styles(f)
                    cs = list(STYLES.keys())
                    ncat = target if target in STYLES else (cs[0] if cs else None)
                    nstyle = name if (ncat and (name or "").strip() in STYLES.get(ncat, {})) \
                             else (style_choices(ncat)[0] if style_choices(ncat) else None)
                    prefix = "OK: " if ok else ""
                    return ([prefix + msg,
                             gr.update(choices=cs, value=ncat),
                             gr.update(choices=style_choices(ncat), value=nstyle)]
                            + control_updates(ncat, nstyle)
                            + default_results(ncat, nstyle)
                            + [gr.update(choices=cs, value=(target if target in cs else ncat)),
                               gr.update(choices=cs, value=ncat),
                               gr.update(choices=style_choices(ncat), value=nstyle),
                               gallery_items(ncat)])
                save_btn.click(on_save, inputs=[folder, save_file, save_name, save_pos, save_neg],
                               outputs=[save_status, cat, style] + ctrls
                                       + [result, result_neg, save_file, edit_cat, edit_style, gallery])

                # delete the style selected in "Style to edit" (with confirmation)
                def on_delete(f, ecat, ename):
                    ok, msg = delete_style(f, ecat, ename)
                    scan_styles(f)
                    cs = list(STYLES.keys())
                    ncat = ecat if ecat in STYLES else (cs[0] if cs else None)
                    nstyle = style_choices(ncat)[0] if style_choices(ncat) else None
                    st = STYLES.get(ncat, {}).get(nstyle) or {"pos": "", "neg": ""}
                    prefix = "OK: " if ok else ""
                    return ([prefix + msg,
                             gr.update(choices=cs, value=ncat),
                             gr.update(choices=style_choices(ncat), value=nstyle)]
                            + control_updates(ncat, nstyle)
                            + default_results(ncat, nstyle)
                            + [gr.update(choices=cs, value=ncat),                     # save_file
                               gr.update(value=(nstyle or "")),                        # save_name
                               gr.update(value=st["pos"]),                             # save_pos
                               gr.update(value=st["neg"]),                             # save_neg
                               gr.update(choices=cs, value=ncat),                      # edit_cat
                               gr.update(choices=style_choices(ncat), value=nstyle),   # edit_style
                               gallery_items(ncat)])
                delete_btn.click(on_delete, inputs=[folder, edit_cat, edit_style],
                                 outputs=[save_status, cat, style] + ctrls
                                         + [result, result_neg, save_file, save_name, save_pos, save_neg,
                                            edit_cat, edit_style, gallery],
                                 _js="(f,c,s)=>{ return (s && confirm('Delete style: '+s+' ?')) ? [f,c,s] : [f,c,'']; }")

        return [enabled, cat, style] + ctrls

    def process(self, p, enabled, cat, style, *vals):
        if not enabled or not style:
            return
        s, text_vals, choice_index = _collect(cat, style, vals)
        if not s:
            return

        # fallback: any <name: value> typed by hand in the prompt box (text fields only)
        for m in re.finditer(TAG_RE, p.prompt or ""):
            k = m.group(1)
            if k.lower() == "prompt":
                k = "_"
            text_vals.setdefault(k, m.group(2).strip())

        new_pos = fill(s["pos"], text_vals, choice_index)
        p.prompt = new_pos
        if getattr(p, "all_prompts", None):
            p.all_prompts = [new_pos for _ in p.all_prompts]

        if s.get("neg"):
            filled_neg = fill(s["neg"], text_vals, choice_index)
            base_neg = (p.negative_prompt or "").strip()
            new_neg = (base_neg + (", " if base_neg and filled_neg else "") + filled_neg).strip()
            p.negative_prompt = new_neg
            if getattr(p, "all_negative_prompts", None):
                p.all_negative_prompts = [new_neg for _ in p.all_negative_prompts]
