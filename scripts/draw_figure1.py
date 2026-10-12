"""Illustrated vector Figure 1 using archived, attributed Lucide SVG geometry.

Run with the bundled Python runtime. The previous TikZ assets are not modified.
All positions use points, so the exported PDF has a predictable physical size.
"""
from pathlib import Path
import sys
from config import ROOT

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from matplotlib.patches import Rectangle, Circle, PathPatch
from matplotlib.path import Path as MplPath
from matplotlib.transforms import Affine2D
from reportlab.graphics.svgpath import SvgPath
from pypdf import PdfReader, PdfWriter
from io import BytesIO
import xml.etree.ElementTree as ET
import html
from PIL import Image as PILImage
from PIL.PngImagePlugin import PngInfo
import json
import pymupdf


OUT = ROOT / 'figures'
ASSETS = ROOT / 'assets/lucide'
OUT.mkdir(parents=True, exist_ok=True)
STEM = 'Figure_1_Evaluation_Object_Separation_Targeted_20261011'
W, H = 520, 381
INK = '#243640'
MUTED = '#596A72'
RULE = '#CFD8DC'
TEAL = '#296F67'
SLATE = '#536E87'
WARM = '#92624B'
REG = FontProperties(family='Arial')
BOLD = FontProperties(family='Arial', weight='bold')
matplotlib.rcParams.update({'pdf.fonttype': 42, 'ps.fonttype': 42,
    'svg.fonttype': 'none', 'savefig.facecolor': 'white'})

fig = plt.figure(figsize=(W/72, H/72))
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, W)
ax.set_ylim(H, 0)
ax.set_axis_off()
texts = []

def text(x, y, value, size=9, color=INK, bold=False, ha='left', va='top', **kwargs):
    artist = ax.text(x, y, value, fontproperties=BOLD if bold else REG,
        fontsize=size, color=color, ha=ha, va=va, linespacing=1.28, **kwargs)
    texts.append(artist)
    return artist

def line(xs, ys, color=RULE, lw=.7, **kwargs):
    return ax.plot(xs, ys, color=color, linewidth=lw, solid_capstyle='butt', **kwargs)

def rect(x, y, width, height, fill, edge='none', lw=.6):
    ax.add_patch(Rectangle((x, y), width, height, facecolor=fill,
        edgecolor=edge, linewidth=lw))


def icon(name, x, y, size, color, lw=1.25):
    """Translate the archived Lucide SVG geometry to true Matplotlib paths."""
    root=ET.parse(ASSETS / f'{name}.svg').getroot()
    for element in root:
        tag=element.tag.split('}')[-1]
        if tag=='circle':
            ax.add_patch(Circle((x+float(element.get('cx'))*size/24,
                                y+float(element.get('cy'))*size/24),
                float(element.get('r'))*size/24, fill=False,
                edgecolor=color, linewidth=lw))
        elif tag=='path':
            source=SvgPath(element.get('d'))
            points, codes, cursor=[], [], 0
            for operation in source.operators:
                if operation==3:
                    points.append((0,0)); codes.append(MplPath.CLOSEPOLY)
                    continue
                count=3 if operation==2 else 1
                for _ in range(count):
                    points.append((source.points[cursor],source.points[cursor+1]))
                    codes.append({0:MplPath.MOVETO,1:MplPath.LINETO,2:MplPath.CURVE4}[operation])
                    cursor+=2
            transform=Affine2D().scale(size/24).translate(x,y)+ax.transData
            ax.add_patch(PathPatch(MplPath(points,codes), transform=transform,
                facecolor='none', edgecolor=color, linewidth=lw,
                capstyle='round', joinstyle='round'))
        else:
            raise ValueError(f'Unsupported SVG element: {tag}')

# A single common frame, followed by three parallel evaluation objects.
text(18, 12, 'Public evaluation of AI governance', size=13.0, bold=True)
text(18, 33, 'Police facial recognition', size=9.3, color=MUTED)
line([18, 502], [51, 51], color=INK, lw=.9)

columns = [
    (18, SLATE, 'users-round', '#EDF2F6', 'Standard-setting\nrole expectations',
     'Who should help\nset the standards?'),
    (186, INK, 'scan-face', '#EEF1F3', 'Deployment\nevaluation',
     'Is widespread police use\na good idea for society?'),
    (354, TEAL, 'shield', '#EAF3EF', 'Comparative safeguard\njudgments',
     'Would a safeguard make\nuse more acceptable?'),
]
for x, color, name, wash, heading, question in columns:
    line([x, x+148], [64, 64], color=color, lw=2.1)
    ax.add_patch(Circle((x+16,89),18.5,facecolor=wash,edgecolor='none'))
    icon(name,x+2,75,28,color,lw=1.35)
    text(x+41, 77, heading, size=9.4, color=color, bold=True)
    text(x, 116, question, size=9.1, color=INK)

# The shared rule of interpretation, rather than a statistical/causal mediator.
rect(18, 153, 484, 57, '#EFF5F3')
rect(18, 153, 2.5, 57, TEAL)
text(34, 163, 'Evaluation-object separation', size=11.2, color=TEAL, bold=True)
text(34, 185, 'Do not collapse these judgments into one support measure.', size=9.1)
for x in (92, 260, 428):
    line([x, x], [143, 153], color=RULE, lw=.75)

# Main empirical expression: paired judgments, explicitly within one respondent.
text(18, 226, 'FOCAL QUESTION  /  RQ1', size=7.8, color=TEAL, bold=True)
text(18, 242, 'Evaluative coexistence', size=12.0, bold=True)
text(502, 246, 'Within the same respondent', size=8.6, color=MUTED, ha='right')

rect(18, 268, 213, 44, '#F6F0EC')
rect(289, 268, 213, 44, '#EDF5F2')
text(30, 275, 'DEPLOYMENT EVALUATION', size=7.4, color=WARM, bold=True)
text(30, 290, '\u201cBad idea\u201d', size=11.4, color=INK, bold=True)
text(301, 275, 'SAFEGUARD JUDGMENT', size=7.4, color=TEAL, bold=True)
text(301, 290, '\u201cMore acceptable\u201d', size=11.4, color=INK, bold=True)
line([231, 247], [290, 290], color=RULE, lw=.8)
line([273, 289], [290, 290], color=RULE, lw=.8)
ax.add_patch(Circle((260, 290), 12.5, facecolor='white', edgecolor=RULE, linewidth=.8))
icon('user-round',250,279,20,MUTED,lw=1.0)

# The interpretive payoff is focal; role associations remain subordinate.
text(260, 322, 'A favorable safeguard judgment alone cannot establish deployment endorsement.',
     size=9.2, ha='center', color=INK)
line([18, 502], [343, 343], color=RULE, lw=.7)
text(18, 353, 'CONTEXTUAL QUESTIONS', size=7.5, color=MUTED, bold=True)
text(18, 368, 'Joint public \u00d7 police role expectations', size=8.6, color=MUTED)
text(502, 353, 'RQ2  Deployment associations', size=8.4, color=MUTED, ha='right')
text(502, 368, 'RQ3  Safeguard associations', size=8.4, color=MUTED, ha='right')

# Fail fast if any text exceeds the canvas or if two separate labels overlap.
fig.canvas.draw()
renderer = fig.canvas.get_renderer()
boxes = [a.get_window_extent(renderer) for a in texts]
canvas = fig.bbox
for a, b in zip(texts, boxes):
    assert canvas.contains(b.x0, b.y0) and canvas.contains(b.x1, b.y1), a.get_text()
collisions = []
for i, b in enumerate(boxes):
    for j in range(i+1, len(boxes)):
        c = boxes[j]
        if min(b.x1, c.x1)-max(b.x0, c.x0) > .5 and min(b.y1, c.y1)-max(b.y0, c.y0) > .5:
            collisions.append((texts[i].get_text(), texts[j].get_text()))
assert not collisions, collisions

from audit_panel_alignment import require_matplotlib_panel_alignment
require_matplotlib_panel_alignment(fig, json_out=str(OUT / (STEM+'.alignment.json')), strict=True)
for extension in ('pdf', 'svg'):
    fig.savefig(OUT / f'{STEM}.{extension}')
license_text=(ASSETS/'LICENSE.txt').read_text(encoding='utf-8')
svg_path=OUT / f'{STEM}.svg'
svg_text=svg_path.read_text(encoding='utf-8')
svg_path.write_text(svg_text.replace('</svg>', '<metadata id="lucide-license">'+html.escape(license_text)+'</metadata>\n</svg>'),encoding='utf-8')
fig.savefig(OUT / f'{STEM}.png', dpi=350, metadata={'Source':'Lucide; https://lucide.dev', 'License':license_text})
writer=PdfWriter()
writer.append(PdfReader(BytesIO((OUT / f'{STEM}.pdf').read_bytes())))
writer.add_attachment('Lucide_LICENSE.txt',license_text.encode('utf-8'))
writer.add_metadata({'/Title':'Evaluation-object separation in public evaluation of police facial-recognition governance', '/Subject':'Conceptual framework. Icons adapted from Lucide under ISC; full copyright and license attached.'})
with (OUT / f'{STEM}.pdf').open('wb') as f:
    writer.write(f)
plt.close(fig)
pdf = pymupdf.open(OUT / f'{STEM}.pdf')
pdf[0].get_pixmap(matrix=pymupdf.Matrix(2.4, 2.4), alpha=False).save(OUT / f'{STEM}_preview.png')
preview_metadata=PngInfo()
preview_metadata.add_text('Source','Lucide; https://lucide.dev')
preview_metadata.add_text('License',license_text)
with PILImage.open(OUT / f'{STEM}_preview.png') as rendered:
    rendered.save(OUT / f'{STEM}_preview.png',pnginfo=preview_metadata)
assert len(pdf)==1
assert not pdf[0].get_images(), 'The framework should remain vector, without embedded raster images.'
for expected in ['Evaluation-object separation', 'Evaluative coexistence', 'RQ1', 'RQ2', 'RQ3']:
    assert expected in pdf[0].get_text(), expected
print(json.dumps({'pdf':str(OUT / f'{STEM}.pdf'), 'svg':str(OUT / f'{STEM}.svg'),
    'preview':str(OUT / f'{STEM}_preview.png'), 'size_pt':[W,H],
    'overlapping_labels':collisions, 'raster_images':0}, indent=2))


