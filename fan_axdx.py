# -*- coding: utf-8 -*-
"""AX/DX 디지털트윈 중심 fan-in/out 구조 (입력→핵심→출력) + Agent 횡단."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle
from matplotlib import font_manager as fm

for f in ["NanumGothic.ttf","NanumGothicBold.ttf"]:
    fm.fontManager.addfont(f"/usr/share/fonts/truetype/nanum/{f}")
plt.rcParams["font.family"]="NanumGothic"; plt.rcParams["axes.unicode_minus"]=False

BLUE, GREEN, PURP, NAVY = "#2a5b8c", "#2e7d4f", "#7b52ab", "#1f3a5f"
fig, ax = plt.subplots(figsize=(16,9.3))
ax.set_axis_off(); ax.set_xlim(0,16); ax.set_ylim(0,9.3)

def inbox(cx,cy,tag,tagc,title,sub):
    w,h=3.7,1.5
    ax.add_patch(FancyBboxPatch((cx-w/2,cy-h/2),w,h,boxstyle="round,pad=0.04",
        fc="white",ec="#c4ccd4",lw=1.6,zorder=3))
    ax.add_patch(Rectangle((cx-w/2,cy-h/2),0.16,h,fc=tagc,zorder=4))
    ax.add_patch(FancyBboxPatch((cx-w/2+0.28,cy+h/2-0.5),0.95,0.42,
        boxstyle="round,pad=0.03",fc=tagc,ec="none",zorder=4))
    ax.text(cx-w/2+0.755,cy+h/2-0.29,tag,ha="center",va="center",color="white",
        fontsize=9,fontweight="bold",zorder=5)
    ax.text(cx+0.15,cy+0.18,title,ha="center",va="center",color=NAVY,
        fontsize=12.5,fontweight="bold",zorder=5)
    ax.text(cx+0.15,cy-0.42,sub,ha="center",va="center",color="#7a848e",
        fontsize=9.3,zorder=5)

ix=3.0; iy=[7.1,4.9,2.7]
inbox(ix,iy[0],"전략1",BLUE,"데이터베이스","축적 데이터 (도면·해석·실적)")
inbox(ix,iy[1],"전략2",BLUE,"Surrogate · ROM","실시간 시뮬레이션 모델")
inbox(ix,iy[2],"현장",PURP,"IoT · 센서 데이터","물리 자산 실시간 상태")

# center: 디지털트윈
cx,cy=8.3,4.9; cw,ch=3.2,2.7
ax.add_patch(FancyBboxPatch((cx-cw/2,cy-ch/2),cw,ch,boxstyle="round,pad=0.1",
    fc="#bcd4e6",ec=BLUE,lw=2.5,zorder=3))
ax.text(cx,cy+0.55,"전략3",ha="center",color=BLUE,fontsize=11,fontweight="bold",zorder=5)
ax.text(cx,cy-0.1,"디지털 트윈",ha="center",va="center",color=NAVY,
    fontsize=18,fontweight="bold",zorder=5)
ax.text(cx,cy-0.75,"가상 물리 모델",ha="center",va="center",color="#456",
    fontsize=10.5,zorder=5)

# fan-in arrows
for y in iy:
    ax.add_patch(FancyArrowPatch((ix+1.85,y),(cx-cw/2-0.05,cy+(y-cy)*0.28),
        arrowstyle="-|>",mutation_scale=20,lw=2.2,color="#8a96a2",
        connectionstyle="arc3,rad=0.0",zorder=2))

# fan-out outputs
oy=[6.7,4.9,3.1]; outs=[("지능 제어","즉각적인 판단"),("최적 운전·운영","에너지·신뢰성"),
                        ("빠른 검증·설계","개발기간(TTM) 단축")]
for y,(t,s) in zip(oy,outs):
    ax.add_patch(FancyArrowPatch((cx+cw/2+0.05,cy+(y-cy)*0.28),(11.7,y),
        arrowstyle="-|>",mutation_scale=20,lw=2.4,color=GREEN,zorder=2))
    ax.text(11.95,y+0.18,t,ha="left",va="center",color=NAVY,fontsize=13.5,
        fontweight="bold",zorder=5)
    ax.text(11.95,y-0.35,s,ha="left",va="center",color="#7a848e",fontsize=9.5,zorder=5)

# Agent band (전략4, 횡단)
ax.add_patch(FancyBboxPatch((0.7,0.5),14.6,1.0,boxstyle="round,pad=0.05",
    fc=GREEN,ec="none",zorder=3))
ax.text(8.0,1.0,"전략4 · AI Researcher (Agent) — 데이터 · 시뮬레이션 · 디지털트윈 전 과정에 적용",
    ha="center",va="center",color="white",fontsize=13,fontweight="bold",zorder=4)

ax.text(8,8.8,"디지털트윈 중심 가치 흐름  ·  입력 → 디지털트윈 → 성과",
    ha="center",fontsize=16,fontweight="bold")
plt.savefig("/home/user/similar-research-DB/fan_axdx.png",dpi=150,bbox_inches="tight")
print("saved")
