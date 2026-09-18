"""Master visual style, coloring-book rules, and negative constraints."""

MASTER_VISUAL_STYLE = """\
Clean black-and-white manga line art for a print coloring-book style children's \
manga. Bold, closed outlines; flat white background areas ready for coloring; \
clear silhouettes; consistent character proportions; expressive but simple faces; \
readable panel-friendly compositions; no screentones; no gray washes; no painterly \
shading; high contrast ink lines only.
"""

COLORING_BOOK_RULES = """\
COLORING BOOK RULES:
- Pure white backgrounds / open regions suitable for hand coloring
- Closed shapes with continuous black outlines
- No filled black areas larger than hair/eyes accents unless specified
- No grayscale gradients, hatching-as-shade, or photographic texture
- Leave clear negative space for speech balloons and captions (text added later)
- Keep important details inside safe margins
"""

NEGATIVE_CONSTRAINTS = """\
photorealistic, 3d render, cgi, blurry, lowres, watermark, signature, logo, \
text, letters, words, speech bubble text, caption text, speech balloons with writing, \
color, colored, watercolor, airbrush, soft shading, gradient, grayscale wash, \
screentone, moire, noise, jpeg artifacts, extra limbs, deformed hands, \
nsfw, gore, horror, creepy uncanny faces
"""
