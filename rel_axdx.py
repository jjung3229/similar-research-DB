# -*- coding: utf-8 -*-
"""미래기술연구원 AX/DX 4전략 연계 관계도 (자료 기준, 관계 중심)."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle
from matplotlib import font_manager as fm

for f in ["NanumGothic.ttf","NanumGothicBold.ttf"]:
    fm.fontManager.addfont(f"/usr/share/fonts/truetype/nanum/{f}")
plt.rcParams["font.family"]="NanumGothic"; plt.rcParams["axes.unicode_minus"]=False

BLUE, GREEN, PURP, NAVY = "#2a5b8c", "#2e7d4f", "#7b52ab", "#1f3a5f"
GRAY="#8a96a2"
fig, ax = plt.subplots(figsize=(18.5,10))
ax.set_axis_off(); ax.set_xlim(0,18.5); ax.set_ylim(0,10)

NY=6.3; NW,NH=3.0,2.0
def node(cx,tag,tagc,title,sub):
    ax.add_patch(FancyBboxPatch((cx-NW/2,NY-NH/2),NW,NH,boxstyle="round,pad=0.05",
        fc="white",ec=tagc,lw=2,zorder=4))
    ax.add_patch(FancyBboxPatch((cx-NW/2+0.16,NY+NH/2-0.58),0.95,0.42,
        boxstyle="round,pad=0.03",fc=tagc,ec="none",zorder=5))
    ax.text(cx-NW/2+0.635,NY+NH/2-0.37,tag,ha="center",va="center",color="white",
        fontsize=9.5,fontweight="bold",zorder=6)
    ax.text(cx,NY+0.28,title,ha="center",va="center",color=NAVY,fontsize=12.5,
        fontweight="bold",zorder=6)
    ax.text(cx,NY-0.5,sub,ha="center",va="center",color="#6b7680",fontsize=9.2,
        zorder=6,linespacing=1.3)

X1,X2,X3,X4 = 2.6,6.7,11.7,16.0
# DX / AX containers
ax.add_patch(FancyBboxPatch((0.6,4.5),12.8,4.1,boxstyle="round,pad=0.05",
    fc="#f3f7fb",ec=BLUE,lw=1.6,ls=(0,(6,4)),zorder=0))
ax.text(0.85,8.35,"DX 추진전략",color=BLUE,fontsize=12.5,fontweight="bold",zorder=1)
ax.add_patch(FancyBboxPatch((14.2,4.5),3.7,4.1,boxstyle="round,pad=0.05",
    fc="#f1f7f3",ec=GREEN,lw=1.6,ls=(0,(6,4)),zorder=0))
ax.text(17.7,8.35,"AX 추진전략",color=GREEN,fontsize=12.5,fontweight="bold",
    ha="right",zorder=1)

node(X1,"전략1",BLUE,"데이터베이스","생산·운항·연구 데이터\nR&D hi-way 플랫폼")
node(X2,"전략2",BLUE,"시뮬레이션 가속화","GPU 고속해석\n유체·구조·진동·변형")
node(X3,"전략3",BLUE,"디지털트윈","장비·시스템·선박·생산\n가상 물리 모델")
node(X4,"전략4",GREEN,"AI Researcher","공통·연구소별 Agent\nAgent 스토어")

def arr(x1,x2,y,color,lw=2.6,rad=0.0,ls="-"):
    ax.add_patch(FancyArrowPatch((x1,y),(x2,y),arrowstyle="-|>",mutation_scale=22,
        lw=lw,color=color,connectionstyle=f"arc3,rad={rad}",zorder=3,linestyle=ls))
def lbl(x,y,t,color,fs=10.5,ec=None):
    ax.text(x,y,t,ha="center",va="center",color=color,fontsize=fs,fontweight="bold",
        zorder=7,bbox=dict(boxstyle="round,pad=0.2",fc="white",ec=ec or "#d5dbe1",lw=1))

# 전략1 -> 전략2
arr(X1+NW/2, X2-NW/2, NY, GRAY)
lbl((X1+X2)/2, NY+0.62, "해석·학습 데이터", BLUE, 9.8)
# 전략2 -> 전략3  (Surrogate·ROM 뱃지를 화살표 위에)
arr(X2+NW/2, X3-NW/2, NY, GRAY)
bx=(X2+X3)/2
ax.add_patch(FancyBboxPatch((bx-1.0,NY-0.32),2.0,0.64,boxstyle="round,pad=0.04",
    fc=PURP,ec="white",lw=2,zorder=6))
ax.text(bx,NY,"Surrogate·ROM",ha="center",va="center",color="white",fontsize=10.5,
    fontweight="bold",zorder=7)
ax.text(bx,NY+0.62,"실시간 모델 연계",ha="center",color=PURP,fontsize=9.5,
    fontweight="bold",zorder=7)
# 전략3 <-> 전략4 : 활용 / 환류
arr(X3+NW/2, X4-NW/2, NY+0.42, GREEN, 2.6)
lbl((X3+X4)/2, NY+0.95, "활용", GREEN, 11, GREEN)
arr(X4-NW/2, X3+NW/2, NY-0.42, GREEN, 2.2, ls=(0,(6,3)))
lbl((X3+X4)/2, NY-0.95, "환류", GREEN, 11, GREEN)

# Agent 전 축 적용 (전략4 -> 전략1,2 하단 점선 호)
for xt in (X1,X2):
    ax.add_patch(FancyArrowPatch((X4,NY-NH/2),(xt,NY-NH/2),arrowstyle="-|>",
        mutation_scale=15,lw=1.7,color=GREEN,linestyle=(0,(4,3)),
        connectionstyle="arc3,rad=0.16",zorder=2,alpha=0.75))
ax.text(8.0,3.0,"전략4 Agent는 데이터·시뮬레이션·디지털트윈 각 부분요소에 적용 (활용 ↔ 환류)",
    ha="center",color=GREEN,fontsize=10.5,fontweight="bold",zorder=7,
    bbox=dict(boxstyle="round,pad=0.25",fc="#f1f7f3",ec=GREEN,lw=1.2))

ax.text(9.2,9.4,"미래기술연구원 AX/DX · 4대 전략 연계 관계도",ha="center",
    fontsize=17,fontweight="bold")
ax.text(9.2,8.95,"AS-IS 기다리고 확인하던 R&D  →  TO-BE 빠르게 실험·즉시 반영하는 R&D",
    ha="center",fontsize=10.5,color="#777")
plt.savefig("/home/user/similar-research-DB/rel_axdx.png",dpi=150,bbox_inches="tight")
print("saved")
