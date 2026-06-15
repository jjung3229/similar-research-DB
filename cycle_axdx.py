# -*- coding: utf-8 -*-
"""AX/DX 4대 추진축 — 순환 구조 + 중앙 Agent 허브 (한눈에 이해형 UI)."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Ellipse, Polygon, FancyBboxPatch, FancyArrowPatch
from matplotlib import font_manager as fm
import numpy as np

for f in ["NanumGothic.ttf","NanumGothicBold.ttf"]:
    fm.fontManager.addfont(f"/usr/share/fonts/truetype/nanum/{f}")
plt.rcParams["font.family"]="NanumGothic"; plt.rcParams["axes.unicode_minus"]=False

BLUE, GREEN, PURP = "#2a5b8c", "#2e7d4f", "#7b52ab"
fig, ax = plt.subplots(figsize=(12.5,12))
ax.set_axis_off(); ax.set_aspect("equal"); ax.set_xlim(0,12); ax.set_ylim(0,12)

C = np.array([6.0,5.8]); RORB=3.75; RP=1.55; RH=1.5
def at(deg): return C + RORB*np.array([np.cos(np.radians(deg)),np.sin(np.radians(deg))])
P_DB, P_SIM, P_DT = at(150), at(30), at(270)

# ---- icons (white line art) ----
def ic_db(c):
    x,y=c; w,h=0.95,0.32
    for dy in (0.36,0.04,-0.28):
        ax.add_patch(Ellipse((x,y+dy),w,h,fill=False,ec="white",lw=2.2,zorder=6))
    ax.plot([x-w/2,x-w/2],[y-0.28,y+0.36],color="white",lw=2.2,zorder=6)
    ax.plot([x+w/2,x+w/2],[y-0.28,y+0.36],color="white",lw=2.2,zorder=6)
def ic_ff(c):  # fast-forward = 가속
    x,y=c
    ax.add_patch(Polygon([[x-0.5,y-0.42],[x-0.5,y+0.42],[x-0.02,y]],fc="white",zorder=6))
    ax.add_patch(Polygon([[x-0.02,y-0.42],[x-0.02,y+0.42],[x+0.46,y]],fc="white",zorder=6))
def ic_twin(c):  # 디지털 트윈 = 쌍
    x,y=c
    ax.add_patch(FancyBboxPatch((x-0.5,y-0.1),0.6,0.6,boxstyle="round,pad=0.02",
        fill=False,ec="white",lw=2.2,zorder=6))
    ax.add_patch(FancyBboxPatch((x-0.1,y-0.5),0.6,0.6,boxstyle="round,pad=0.02",
        fill=False,ec="white",lw=2.2,zorder=7))
def ic_net(c):  # Agent = 네트워크
    x,y=c
    pts=[(x,y+0.5),(x-0.5,y-0.05),(x+0.5,y-0.05),(x,y-0.5)]
    for p in pts:
        ax.plot([x,p[0]],[y,p[1]],color="white",lw=2,zorder=6)
        ax.add_patch(Circle(p,0.12,fc="white",zorder=7))
    ax.add_patch(Circle((x,y),0.17,fc="white",zorder=7))

def pillar(c,color,title,sub,iconfn):
    ax.add_patch(Circle(c,RP,fc=color,ec="white",lw=3,zorder=5))
    iconfn(c+np.array([0,0.55]))
    ax.text(c[0],c[1]-0.45,title,ha="center",va="center",color="white",
        fontsize=14.5,fontweight="bold",zorder=8)
    ax.text(c[0],c[1]-0.95,sub,ha="center",va="center",color="white",
        fontsize=9.8,zorder=8,alpha=0.95)

# ---- cycle arrows (clockwise, bulge outward) ----
def cyc(p1,p2,label,lcol="#5a6b7a",badge=False):
    u=(p2-p1)/np.linalg.norm(p2-p1)
    a=p1+u*RP; b=p2-u*RP
    ax.add_patch(FancyArrowPatch(a,b,arrowstyle="-|>",mutation_scale=26,lw=3.2,
        color="#9aa7b3",connectionstyle="arc3,rad=0.22",zorder=2))
    # label position pushed outward from center
    mid=(p1+p2)/2; out=(mid-C); out=out/np.linalg.norm(out)
    lp=mid+out*1.25
    if badge:
        ax.add_patch(FancyBboxPatch((lp[0]-1.15,lp[1]-0.32),2.3,0.64,
            boxstyle="round,pad=0.05",fc=PURP,ec="white",lw=2,zorder=9))
        ax.text(lp[0],lp[1],label,ha="center",va="center",color="white",
            fontsize=11.5,fontweight="bold",zorder=10)
    else:
        ax.text(lp[0],lp[1],label,ha="center",va="center",color=lcol,
            fontsize=11.5,fontweight="bold",zorder=9,
            bbox=dict(boxstyle="round,pad=0.2",fc="white",ec="#cdd6df",lw=1))

cyc(P_DB,P_SIM,"학습 데이터")
cyc(P_SIM,P_DT,"Surrogate · ROM",badge=True)
cyc(P_DT,P_DB,"운영데이터 환류")

# ---- center hub: AI Researcher (Agent) ----
for P in (P_DB,P_SIM,P_DT):
    u=(P-C)/np.linalg.norm(P-C)
    ax.add_patch(FancyArrowPatch(C+u*RH, P-u*RP, arrowstyle="-|>",mutation_scale=15,
        lw=1.8,color=GREEN,linestyle=(0,(4,3)),zorder=3,alpha=0.85))
ax.add_patch(Circle(C,RH,fc=GREEN,ec="white",lw=3,zorder=5))
ic_net(C+np.array([0,0.5]))
ax.text(C[0],C[1]-0.4,"AI Researcher",ha="center",va="center",color="white",
    fontsize=13.5,fontweight="bold",zorder=8)
ax.text(C[0],C[1]-0.85,"Agent · 전 축 적용",ha="center",va="center",color="white",
    fontsize=10,zorder=8,alpha=0.95)

pillar(P_DB,BLUE,"데이터베이스","데이터 수집·축적",ic_db)
pillar(P_SIM,BLUE,"시뮬레이션 가속화","고속 해석",ic_ff)
pillar(P_DT,BLUE,"디지털트윈","실시간 가상모델",ic_twin)

ax.text(6,11.4,"AX/DX 4대 추진축 — 데이터·시뮬레이션·디지털트윈 순환 + AI Researcher",
    ha="center",fontsize=16,fontweight="bold")
plt.savefig("/home/user/similar-research-DB/cycle_axdx.png",dpi=150,bbox_inches="tight")
print("saved")
