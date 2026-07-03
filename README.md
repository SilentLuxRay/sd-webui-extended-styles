# Extended Styles

An extension for **Stable Diffusion WebUI Forge / Forge Neo / AUTOMATIC1111** that upgrades the
built‑in *Styles* system with **multiple, named placeholders**.

The native styles system only understands a single `{prompt}`. Extended Styles lets a single style
template contain as many slots as you want — `{prompt_face}`, `{prompt_haircolor}`,
`{prompt_flowercolor}`, … — and gives you a labeled field for each, so you can reuse one template for
many different results without rewriting it every time.

![preview](images/preview.png)

## Features

- **Multiple placeholders per style** — `{prompt}`, numbered `{prompt1}`, and named `{prompt_xxx}`.
- **Auto‑generated fields** — pick a style and one labeled input appears per placeholder.
- **Built‑in translation** — write your values in any language and translate them to English with one
  click (auto‑detects the language; text already in English is left unchanged).
- **Write to main prompt** — one button drops the assembled prompt into the real prompt box, so
  *Send to img2img*, PNG info and everything downstream just work.
- **Create / edit styles** — add or update styles and save them straight into your `.csv` files
  (a `.bak` backup is made before writing).
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

## Placeholder syntax

| In the CSV | Meaning | Field label |
|---|---|---|
| `{prompt}` | classic single slot | `prompt` |
| `{prompt1}`, `{prompt2}` | numbered slots | `1`, `2` |
| `{prompt_face}`, `{prompt_haircolor}` | **named** slots (recommended) | `face`, `haircolor` |

Named placeholders are recommended because the field label tells you exactly what each slot is for.

## CSV format

Standard Forge/A1111 styles format:

```csv
name,prompt,negative_prompt
Girl with flower,a girl {prompt_face} holding the {prompt_flowercolor} flower,
Detailed portrait,portrait of a woman {prompt_face} with {prompt_haircolor},lowres bad anatomy
```

To extend an existing single‑`{prompt}` style, just open the CSV and add more `{prompt_xxx}`
placeholders wherever you need them. Up to **8** placeholders per style (see `MAXF` in the script).

## Notes

- **Translation** uses the free Google Translate endpoint and therefore needs an internet connection.
- **Styles saved into files loaded by the native `--styles-file`** will also show up in the native
  styles dropdown, where only the classic `{prompt}` works — apply named/numbered styles **through this
  extension**.
- **Dynamic Prompts:** generating with a completely empty prompt while the Dynamic Prompts extension is
  enabled raises `StopIteration` (a Dynamic Prompts limitation). If you use both together, don't leave
  the prompt box empty — press **Write to main prompt** first, or type at least a space.

## License

MIT — see [LICENSE](LICENSE).
