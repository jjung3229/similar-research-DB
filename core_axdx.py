# -*- coding: utf-8 -*-
"""AX/DX 핵심 흐름 — 미니멀 버전."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
from matplotlib import font_manager as fm

for f in ["NanumGothic.ttf","NanumGothicBold.ttf"]:
    fm.fontManager.addfont(f"/usr/share/fonts/truetype/nanum/{f}")
plt.rcParams["font.family"]="NanumGothic"; plt.rcParams["axes.unicode_minus"]=False

BLUE, PURP, GREEN = "#2a5b8c", "#7b52ab", "#2e7d4f"

fig, ax = plt.subplots(figsize=(20,9))
ax.set_axis_off(); ax.set_xlim(0,20); ax.set_ylim(0,9)

def box(cx, title, sub, fc):
    w,h,cy = 3.6,2.4,6.2
    ax.add_patch(FancyBboxPatch((cx-w/2,cy-h/2),w,h,boxstyle="round,pad=0.1",
        fc=fc,ec="none",zorder=3))
    ax.text(cx,cy+0.35,title,ha="center",va="center",color="white",
        fontsize=15,fontweight="bold",zorder=4)
    ax.text(cx,cy-0.5,sub,ha="center",va="center",color="white",
        fontsize=10.5,zorder=4,alpha=0.95)
    return cx

def flow(x1,x2,label):
    ax.add_patch(FancyArrowPatch((x1+1.8,6.2),(x2-1.8,6.2),arrowstyle="-|>",
        mutation_scale=26,lw=3,color="#9aa7b3",zorder=2))
    ax.text((x1+x2)/2,6.75,label,ha="center",color="#5a6b7a",fontsize=11,
        fontweight="bold",zorder=4)

xs=[2.6,7.0,11.4,15.8]
box(xs[0],"데이터베이스","데이터 수집·축적",BLUE)
box(xs[1],"시뮬레이션 가속화","고속 해석",BLUE)
box(xs[2],"Surrogate·ROM","대리·축소모델",PURP)
box(xs[3],"디지털트윈","실시간 가상모델",BLUE)
flow(xs[0],xs[1],"데이터")
flow(xs[1],xs[2],"생성")
flow(xs[2],xs[3],"연계")

# Agent 계층 (전 과정 횡단)
ax.add_patch(FancyBboxPatch((1.0,1.4),16.8,1.5,boxstyle="round,pad=0.1",
    fc=GREEN,ec="none",zorder=3))
ax.text(9.4,2.15,"AI Researcher · Agent — 전 과정에 적용",ha="center",va="center",
    color="white",fontsize=14,fontweight="bold",zorder=4)
for cx in xs:
    ax.add_patch(FancyArrowPatch((cx,2.9),(cx,5.0),arrowstyle="-|>",
        mutation_scale=18,lw=2,color=GREEN,linestyle=(0,(3,3)),zorder=2,alpha=0.8))

ax.text(10,8.4,"AX/DX 핵심 흐름",ha="center",fontsize=20,fontweight="bold")
plt.savefig("/home/user/similar-research-DB/core_axdx.png",dpi=150,bbox_inches="tight")
print("saved")
