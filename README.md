# Extended Styles

An extension for **Stable Diffusion WebUI Forge / Forge Neo / AUTOMATIC1111** that upgrades the
built‑in *Styles* system with **multiple, named placeholders**.

The native styles system only understands a single `{prompt}`. Extended Styles lets a single style
template contain as many slots as you want — `{prompt_face}`, `{prompt_haircolor}`,
`{prompt_flowercolor}`, … — and gives you a labeled field for each, so you can reuse one template for
many different results without rewriting it every time.

![preview](images/preview-1.png)

## Features

- **Multiple placeholders per style** — `{prompt}`, numbered `{prompt1}`, and named `{prompt_xxx}`.
- **Auto‑generated fields** — pick a style and one labeled input appears per placeholder.
- **Choice variables** — `{prompt_Gender=Male|Female}` becomes a dropdown; later placeholders with the
  same name follow the chosen option by index, so one menu drives several coordinated substitutions.
  Multiple independent variables per style are supported. Controls appear in the same order as the
  placeholders in the prompt (text fields and menus interleaved).
- **Branch variables (labels + nesting)** — an option can read `Label=>text`, so the menu shows a clean
  label (e.g. `Safe` / `Explicit`) while inserting a whole sub‑template. That sub‑template can contain
  its own **nested placeholders** that **appear/disappear** with the choice, so one menu can switch
  between entirely different pieces of text and fields — e.g. a safe/explicit toggle.
- **In‑panel help** — a collapsible *Help / Placeholder syntax* section explains every placeholder type.
- **Per‑style generation settings** — optionally save the **seed, sampler, steps, CFG and size** for a
  style and load them back with one click (or automatically on selection). Stored in a separate file,
  so your style CSVs stay untouched.
- **NSFW preview filter** — a toggle that blurs the carousel thumbnails of styles whose name contains
  "NSFW" (case-insensitive); hover a thumbnail to peek. Remembered per browser.
- **Preview carousel** — each style shows a thumbnail; click one to select it. Set a thumbnail from the
  last generated image with one click, or by dropping an image. A slider resizes the thumbnails and the
  size is remembered (per browser).
- **Category separators** — rows named `----SECTION----` in a CSV act as visual dividers and are hidden
  from the style list, so you can organize big files.
- **Optional placeholders** — leave a field empty and its placeholder is simply dropped from the prompt
  (leftover spaces and commas are cleaned up), so one template covers cases with or without a detail.
- **Readable field labels** — a hyphen in a named placeholder is shown as a space, e.g.
  `{prompt_hair-color}` → label "hair color".
- **Built‑in translation** — write your values in any language and translate them to English with one
  click (auto‑detects the language; text already in English is left unchanged).
- **Write to main prompt** — one button drops the assembled prompt **and negative prompt** into the real
  boxes, so *Send to img2img*, PNG info and everything downstream just work. (The negative is only
  written when the style has one, so your own negative isn't wiped.)
- **Create / edit styles** — pick a style to edit and its fields fill in automatically; saving updates
  the CSV in place (or adds a new one), with a `.bak` backup before writing.
- **Works alongside prompt editors** like *prompt‑all‑in‑one* — values are filled in this panel and the
  substitution happens server‑side.

## Installation

1. Copy this folder into your WebUI `extensions` directory
   (e.g. `webui/extensions/sd-webui-extended-styles`), or use
   *Extensions → Install from URL* with this repository's URL.
2. Fully restart the WebUI.
3. A new **Extended styles** panel appears in txt2img and img2img.

## Usage

1. Open the **Extended styles** panel.
2. In **CSV folder**, enter the folder that holds your style `.csv` files (you can point it at your
   existing styles folder) and press **Reload**. Each `.csv` file becomes a **Category**.
3. Choose a **Category** and a **Template**. One labeled field appears per placeholder.
4. Fill in the fields.
5. *(optional)* Press **Translate fields to English** if you wrote in another language.
6. Press **Write to main prompt** — the assembled prompt is written into the real prompt box.
7. Generate as usual.

> You can also tick **Enable extended styles** instead of using *Write to main prompt*: with it on, the
> extension rewrites the prompt automatically at generation time and you can leave the main prompt box
> empty. (See the note about Dynamic Prompts below.)

### Creating or editing a style

Open **Create / edit style**, then pick the **Category** and **Style to edit** — the name, prompt and
negative fields fill in automatically. Change what you want and press **Save style** (same name → updates
it in place; a new name → adds it). Press **New** to clear the fields and start from scratch, or
**Delete style** to remove the one selected in *Style to edit* (with a confirmation). Use **▲ Move up** /
**▼ Move down** to reorder the selected style in its file (separators stay in place). A `.bak`
backup of the CSV is made before every save, delete or move.

### Style previews

Every style shows a thumbnail in the **Style previews** carousel (a gray name tile until you set one);
click a thumbnail to select that style. Use the **Thumbnail size** slider to resize the carousel — the
value is remembered in your browser. To set a preview, open **Set style preview**: select the style,
**generate** an image and press **Apply last generation**, or drag an image and press **Apply uploaded
image**. Previews are stored as PNGs in the extension's `previews/` folder.

## Placeholder syntax

| In the CSV | Meaning | Field label |
|---|---|---|
| `{prompt}` | classic single slot | `prompt` |
| `{prompt1}`, `{prompt2}` | numbered slots | `1`, `2` |
| `{prompt_face}`, `{prompt_haircolor}` | **named** slots (recommended) | `face`, `haircolor` |
| `{prompt_hair-color}` | named slot, hyphen shown as a space | `hair color` |

Named placeholders are recommended because the field label tells you exactly what each slot is for.
Use a hyphen when you want a multi‑word label (`{prompt_eye-color}` → "eye color").

Any field you leave empty is **optional**: its placeholder is removed from the final prompt (instead of
appearing literally), and the surrounding spaces and commas are tidied up. Tip: for optional details,
place the placeholder as its own comma‑separated clause (e.g. `a girl, {prompt_extra}, red hair`) so it
disappears cleanly when empty.

### Choice variables

Add options after `=`, separated by `|`, to turn a placeholder into a **dropdown**:

```
{prompt_Gender=Male|Female}
```

The **first** occurrence of a name defines the menu (its options are the labels). Every later
placeholder with the **same name** is linked to it: it inserts its own option at the **same index** as
the selected choice. Commas inside an option go straight into the prompt.

```
a human {prompt_Gender=Male|Female} in a loose shirt revealing his {prompt_Gender=hairy chest|chest with a pink bra}
```

- Choosing **Male** → "a human Male in a loose shirt revealing his hairy chest"
- Choosing **Female** → "a human Female in a loose shirt revealing his chest with a pink bra"

You can define **several independent variables** in one style, each with its own dropdown.
If a linked option list is shorter than the selected index, that spot is left empty. Tip: put fixed
words that must change with the choice *inside* the options (e.g. `{prompt_Gender=A man|A woman}`).

### Branch variables — labels and nesting

Two extra pieces make choices much more powerful:

- **`Label=>text`** — the part before `=>` is what the **menu shows**; the part after is what goes into
  the **prompt**. So the menu can read `Safe` / `Explicit` instead of the raw text.
- **Nesting** — the text after `=>` can contain **other placeholders**. Their fields appear in the
  panel, and they are only used when that branch is selected.

Put together, one menu can add or remove a whole clause (and its own fields):

```
a girl,{prompt_Top=Dressed=>wearing a {prompt_ShirtColor} shirt,|Nude=>}on a beach
```

- The **Top** menu shows `Dressed` / `Nude`.
- Choose **Dressed** → a **ShirtColor** field is used → `a girl,wearing a red shirt,on a beach`.
- Choose **Nude** → the whole clause is dropped → `a girl,on a beach`.

Use the **same variable name in several spots** to toggle multiple parts of the prompt with one menu
(they follow the same choice by index). A branch's `text` can even contain another `{prompt_X=...}`.
Nested fields **show and hide** automatically based on the selected branch, and the values you've
already typed are **kept** when you switch back.

## CSV format

Standard Forge/A1111 styles format:

```csv
name,prompt,negative_prompt
Girl with flower,a girl {prompt_face} holding the {prompt_flowercolor} flower,
Detailed portrait,portrait of a woman {prompt_face} with {prompt_haircolor},lowres bad anatomy
```

To extend an existing single‑`{prompt}` style, just open the CSV and add more `{prompt_xxx}`
placeholders wherever you need them. Up to **30** placeholders per style (see `MAXSLOTS` in the script).

To group styles inside one file, add rows whose name is wrapped in dashes, e.g. `----WOMEN----`. These
are treated as separators and hidden from the style list (they still remain in the file).

## Notes

- **Translation** uses the free Google Translate endpoint and therefore needs an internet connection.
- **Styles saved into files loaded by the native `--styles-file`** will also show up in the native
  styles dropdown, where only the classic `{prompt}` works — apply named/numbered styles **through this
  extension**.
- **Dynamic Prompts:** generating with a completely empty prompt while the Dynamic Prompts extension is
  enabled raises `StopIteration` (a Dynamic Prompts limitation). If you use both together, don't leave
  the prompt box empty — press **Write to main prompt** first, or type at least a space.

## Screenshots

<!-- Rename your images to images/preview-1.png ... preview-5.png and edit the captions below. -->

| | |
|---|---|
| ![](images/preview-2.png) | ![](images/preview-3.png) |
| ![](images/preview-4.png) | ![](images/preview-5.png) |

## Changelog

### v3.2.2
- Fix: **translation** no longer fails for *every* field because of one field. Two causes
  are addressed: with many fields the old endpoint returned HTTP 429 (rate-limit), and a
  field that was already English or misspelled could abort the whole batch. Translation now
  uses a more reliable Google endpoint (fewer 429s, all fields in a single request) and is
  resilient per field — anything untranslatable is left as-is while the rest is translated.

### v3.2.1
- Fix: the **CSV folder** path is no longer overwritten on restart. It was also stored in Forge's
  `ui-config.json`, which restored the old path over the extension's own `config.json`; the field is now
  excluded from `ui-config`, so the folder you set persists.

### v3.2.0
- **Per‑style generation settings** — a *Style settings* panel to save the seed, sampler, steps, CFG and
  size for the selected style (to a separate `style_settings.json`) and load them back with a button or
  automatically. The style CSVs are left untouched.

### v3.1.1
- Fix: raise the placeholder limit per style from 12 to 30, so complex styles no longer lose the
  fields past the 12th.

### v3.1.0
- **Conditional fields** — nested placeholders now **show/hide** based on the selected branch (values
  you've typed are kept when switching).
- **In‑panel help** — a *Help / Placeholder syntax* accordion explaining all placeholder types.

### v3.0.0
- **Branch variables** — new templating engine (brace‑aware, recursive). Choice options now support
  `Label=>text` for readable menu labels, and **nested placeholders** inside options, so one menu can
  swap between whole sub‑templates with their own fields. Fully backward‑compatible with existing
  styles. (Nested fields stay visible in the panel until their branch is selected.)

### v2.2.0
- **Reorder styles** — ▲/▼ buttons in the Create/edit panel move the selected style up or down in its
  CSV file (separators stay put), with a backup.

### v2.1.1
- Fix: **Write to main prompt** now also fills the **negative prompt** box (previously the style's
  negative was only applied with *Enable extended styles* ticked). Left untouched when the style has
  no negative.

### v2.1.0
- **Placeholder order** — controls now render in the order the placeholders appear in the prompt
  (text fields and choice menus interleaved), instead of variables always last.
- **Delete style** — a button to remove the selected style from its CSV, with confirmation and backup.
- **NSFW preview filter** — toggle to blur thumbnails of styles with "NSFW" in the name; hover to peek.

### v2.0.0
- **Choice variables** — `{prompt_Name=opt1|opt2}` placeholders become dropdowns; later placeholders
  with the same name follow the selected option by index. Multiple independent variables per style.

### v1.1.0
- Hide the numeric value box next to the thumbnail-size slider (cosmetic).

### v1.0.0
- **Preview carousel** — per-style thumbnails (click to select), set from the last generation or an
  uploaded image, with a size slider remembered per browser.
- **Category separators** — `----SECTION----` rows are hidden from the style list.
- **Optional placeholders** — empty fields are dropped from the prompt, with cleanup of leftover
  spaces and commas.
- **Hyphen labels** — a hyphen in a named placeholder is shown as a space in the field label.
- **Direct style editing** — dropdowns to pick the style to edit (fields auto‑fill) plus a **New** button.
- **Faster translation** — all fields are translated in a single request.

## License

MIT — see [LICENSE](LICENSE).
