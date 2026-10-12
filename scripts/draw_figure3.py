"""Preserve the joint grid and colour scale; foreground the reverse denominator.

Quantitative grid. Three heatmaps retain full 3x3 joint responses; the lower
reading key distinguishes the core reverse conditional from joint and forward
quantities. Source observations are not filtered for drawing.
"""
import json
import numpy as np
import matplotlib as mpl
mpl.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from config import ROOT, OUT
from audit_panel_alignment import require_matplotlib_panel_alignment

mpl.rcParams.update({'font.family':'sans-serif','font.sans-serif':['Arial','Helvetica','DejaVu Sans'],
    'font.size':8,'pdf.fonttype':42,'svg.fonttype':'none','axes.spines.top':False,'axes.spines.right':False})
INK='#20313e';MUTED='#566b7b';ACCENT='#b36a36'
FIG=ROOT/'figures';FIG.mkdir(exist_ok=True)
joint=[r for r in json.loads((OUT/'joint_estimates_with_intervals.json').read_text()) if r['group']=='All']
comp=json.loads((OUT/'favorable_deployment_composition.json').read_text())['items']
fig,axes=plt.subplots(1,3,figsize=(7.4,4.7))
fig.subplots_adjust(left=.105,right=.974,top=.85,bottom=.43,wspace=.19)
for j,(ax,row,title) in enumerate(zip(axes,joint,['Opt-out','Notification','Officer training'])):
    cells={(c['overall'],c['safeguard']):c for c in row['all_9_cells']}
    # The prior display used values rounded to one decimal. Preserve its cells.
    matrix=np.array([[round(100*cells[a,b]['proportion'],1) for a in [1,2,3]] for b in [1,2,3]])
    ax.imshow(matrix,cmap='Blues',vmin=0,vmax=40,aspect='equal',interpolation='nearest')
    ax.set_xticks([0,1,2],['Good','Bad','Not sure'],fontsize=7.2)
    ax.set_yticks([0,1,2],['More','Less','No difference'],fontsize=7.2)
    if j: ax.set_yticklabels([])
    for r in range(3):
        for c in range(3):
            ax.text(c,r,f'{matrix[r,c]:.1f}',ha='center',va='center',fontsize=8.1,
                weight='bold' if (r,c)==(0,1) else 'normal',color='white' if matrix[r,c]>24 else INK)
    ax.add_patch(Rectangle((.5,-.5),1,1,fill=False,edgecolor=ACCENT,linewidth=2.1))
    ax.set_xticks(np.arange(-.5,3,1),minor=True);ax.set_yticks(np.arange(-.5,3,1),minor=True)
    ax.grid(which='minor',color='white',linewidth=1.1);ax.tick_params(which='both',length=0)
    ax.text(-.14,1.12,chr(97+j),transform=ax.transAxes,weight='bold',fontsize=8.5,color=INK,va='bottom')
    ax.set_title(f"{title}\nBoth-item-valid n = {row['joint']['n']:,}",loc='left',weight='bold',fontsize=8.2,pad=8,color=INK)
fig.text(.54,.372,'Outlined cell: Bad idea + More acceptable; shared joint-percentage scale: 0-40%',ha='center',fontsize=7.4,color=MUTED)
fig.text(.105,.329,'Core result: Bad idea among More acceptable',fontsize=9,weight='bold',color=INK)
fig.text(.03,.243,'Reverse\nconditional',fontsize=7.5,va='top',color=INK)
centres=[.31,.60,.88]
for centre,title in zip(centres,['Opt-out','Notification','Officer training']):
    fig.text(centre,.281,title,ha='center',fontsize=7.8,color=INK)
for centre,row,item in zip(centres,joint,comp):
    r=next(c for c in item['deployment_composition'] if c['code']==2);lo,hi=r['ci95']
    fig.text(centre,.243,f"{100*r['proportion']:.2f}%  ({100*lo:.2f}-{100*hi:.2f})",ha='center',va='top',fontsize=8.2,weight='bold',color=INK)
    fig.text(centre,.205,f"More acceptable n = {item['favorable_n']:,}",ha='center',va='top',fontsize=7.2,color=MUTED)
fig.text(.105,.162,'Working pointwise 95% intervals in parentheses; counts are unweighted.',fontsize=7.3,color=MUTED)
fig.text(.03,.109,'Joint\nBad + More',fontsize=7.3,va='top',color=MUTED)
fig.text(.03,.049,'Forward\nMore among Bad',fontsize=7.3,va='top',color=MUTED)
for centre,row in zip(centres,joint):
    a,b=row['joint'],row['conditional']
    fig.text(centre,.109,f"{100*a['proportion']:.2f}%  /  valid n = {a['n']:,}",ha='center',va='top',fontsize=7.4,color=MUTED)
    fig.text(centre,.049,f"{100*b['proportion']:.2f}%  /  Bad idea n = {b['n']:,}",ha='center',va='top',fontsize=7.4,color=MUTED)
fig.canvas.draw()
stem=FIG/'Figure_3_Joint_and_Conditional_Targeted_20261011'
require_matplotlib_panel_alignment(fig,json_out=str(stem)+'.alignment.json',overlay_svg=str(stem)+'.alignment.svg',strict=True,require_panel_labels=True)
for suffix,kwargs in [('.pdf',{}),('.svg',{}),('.png',{'dpi':350}),('.tiff',{'dpi':600})]:
    fig.savefig(str(stem)+suffix,facecolor='white',**kwargs)
plt.close(fig)
