# The 3D work

Everything here is built by script, so every render can be made again from nothing. Blender 5.2, Cycles. No `.blend` file is kept.

## Steps

```sh
# 1. print each bag's label (colour + print mask) from label.html, with headless Chrome
node assets/3d/labels/make-labels.mjs

# 2. render (from the project root)
blender -b --factory-startup -P assets/3d/render.py -- --job hero     # one portrait of each bag, 1000 x 1500
blender -b --factory-startup -P assets/3d/render.py -- --job spin     # 24 frames of a full turn each, 480 x 720
blender -b --factory-startup -P assets/3d/render.py -- --job row      # all five in a line, 2400 x 900
blender -b --factory-startup -P assets/3d/beans.py  -- --job species  # each species' beans, 960 x 1200
blender -b --factory-startup -P assets/3d/beans.py  -- --job bed      # a bed of mixed beans, 1920 x 1080
```

Options: `--only atok,lipa` · `--samples 72` · `--scale 0.5` for a quick look · `--force` to render over a file that exists. Renders land in `assets/3d/out`, which is not in git.

On a four-core CPU with no supported GPU the full set takes about two hours; the turn frames are most of it.

## The bag (`wako_bag.py`)

A 250 g flat-bottom pouch, 130 × 74 × 250 mm. It is a loft of 258 cross-sections of 252 points each:

- Low down it is a box full of beans. Higher up, the front and back close on each other while the side gussets fold inward by exactly the length the paper has, so no panel stretches.
- Corners are rounder near the base and creased near the top.
- Dents, diagonal creases and folds come from noise, strongest where the bag is empty and none in the pressed seal. Near the seal the panels lie almost on each other, so the inward push is limited to keep one from showing through the next.
- A zipper ridge under the seal, a slight lean and twist from the seed, and a one-way valve on the back.
- The paper is matte with a fine tooth. The print is a little smoother than the bare stock (the mask image drives roughness), and the seal band is crimped by a wave in the bump.

Each coffee has its own seed, so each bag has its own wrinkles and every build of it is the same.

## The label (`labels/label.html`)

One HTML page, 8 px to the millimetre: front, right gusset, back, left gusset, 3264 × 2000. It reads a coffee from `src/content/coffees.json`, so the bag and the site can never disagree. The front carries the name up the side and an altitude column on a 0 to 2,000 m scale; in a row, the five columns step down like a chart. The back carries the story, the facts and the roast stamp.

## The beans (`beans.py`)

Each species has its own bean: arabica an oval with an S-shaped crease, robusta rounder with a straight one, excelsa a small teardrop, liberica the largest, lopsided, with a hooked tip. Every bean gets a slightly different roast from its object's random value, pale chaff in the crease, and oil on the dark roasts.
