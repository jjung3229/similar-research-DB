# -*- coding: utf-8 -*-
"""AX/DX 기술 연계도 — 기술 메커니즘 관점.
데이터 → 시뮬레이션 가속(surrogate/ROM 생성) → 디지털트윈, Agent는 전 영역 횡단 적용."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
from matplotlib import font_manager as fm

for f in ["NanumGothic.ttf","NanumGothicBold.ttf"]:
    fm.fontManager.addfont(f"/usr/share/fonts/truetype/nanum/{f}")
plt.rcParams["font.family"]="NanumGothic"; plt.rcParams["axes.unicode_minus"]=False

DXC, AXC, ART, FB = "#1f4e79", "#2e7d4f", "#7b52ab", "#c0504d"

fig, ax = plt.subplots(figsize=(22,13))
ax.set_axis_off(); ax.set_xlim(0,22); ax.set_ylim(0,13)
ax.text(11,12.7,"HD한국조선해양 미래기술연구원 · AX/DX 기술 연계도 (기술 메커니즘 관점)",
    ha="center",fontsize=18,fontweight="bold")

def block(cx,cy,w,h,title,bullets,fc,tc="white",bc=None,ft=13,fb=9.6):
    bc=bc or fc
    ax.add_patch(FancyBboxPatch((cx-w/2,cy-h/2),w,h,boxstyle="round,pad=0.06",
        fc=fc,ec=bc,lw=2,zorder=3))
    ax.text(cx,cy+h/2-0.3,title,ha="center",va="top",color=tc,fontsize=ft,
        fontweight="bold",zorder=4)
    if bullets:
        ax.text(cx,cy+h/2-0.95,"\n".join("· "+b for b in bullets),ha="center",va="top",
            color=tc,fontsize=fb,zorder=4,linespacing=1.5)

def arrow(p1,p2,color,lw=2.6,rad=0.0,label=None,ls="-",fs=10.5,lpos=None):
    ax.add_patch(FancyArrowPatch(p1,p2,arrowstyle="-|>",mutation_scale=22,lw=lw,
        color=color,connectionstyle=f"arc3,rad={rad}",zorder=2,linestyle=ls))
    if label:
        m=lpos or ((p1[0]+p2[0])/2,(p1[1]+p2[1])/2+0.3)
        ax.text(m[0],m[1],label,ha="center",va="center",color=color,fontsize=fs,
            fontweight="bold",zorder=6,
            bbox=dict(boxstyle="round,pad=0.18",fc="white",ec=color,lw=0.6,alpha=0.95))

# ===== main technology flow (top) =====
CY,H = 8.3,3.7
block(2.7,CY,3.6,H,"전략1. 데이터베이스",
    ["생산·운항·연구 데이터","R&D hi-way 플랫폼","OCR·VLM 비정형 검색"],DXC)
block(7.7,CY,4.0,H,"전략2. 시뮬레이션 가속화",
    ["유체 GPU CFD","구조 SimSolid·FE","선박진동 JAX·ACMS","변형 예측·제어"],DXC)
# artifact node (surrogate/ROM) — 강조
ax.add_patch(FancyBboxPatch((11.5,CY-1.5),2.9,3.0,boxstyle="round,pad=0.06",
    fc="#efe6f7",ec=ART,lw=2.4,zorder=3))
ax.text(12.95,CY+1.05,"Surrogate · ROM",ha="center",va="top",color=ART,
    fontsize=12.5,fontweight="bold",zorder=4)
ax.text(12.95,CY+0.25,"축소·대리모델\n(고속 대체모델)\n해석 데이터로 학습",ha="center",va="top",
    color="#4a2f6b",fontsize=9.4,zorder=4,linespacing=1.4)
ax.text(12.95,CY+1.75,"◆ 핵심 산출물",ha="center",color=ART,fontsize=9,
    fontweight="bold",zorder=4)
block(17.6,CY,4.2,H,"전략3. 디지털트윈",
    ["장비 DT (AIP·LIB·압축기)","시스템 (CHS·전기추진·암모니아)","선박 USV 자율운항","생산공정 가상검증"],DXC)

ax.text(0.9,CY+H/2+0.45,"DX 추진전략",color=DXC,fontsize=13,fontweight="bold")

# flow arrows
arrow((2.7+1.8,CY),(7.7-2.0,CY),DXC,2.6,label="학습·검증\n데이터")
arrow((7.7+2.0,CY),(11.5,CY),DXC,2.6,label="고속해석으로\n생성")
arrow((14.4,CY),(17.6-2.1,CY),ART,2.8,label="실시간 모델\n연계")
# ROM 자산화 -> DB (저장, dashed)
arrow((11.5+0.2,CY-1.5),(2.7,CY-H/2),"#9a7bbf",1.8,rad=-0.18,ls=(0,(5,4)),
    label="ROM 자산화·저장",fs=9,lpos=(6.6,5.7))
# 환류 (DT -> DB, top arc)
ax.add_patch(FancyArrowPatch((17.6,CY+H/2),(2.7,CY+H/2),arrowstyle="-|>",
    mutation_scale=24,lw=2.4,color=FB,connectionstyle="arc3,rad=-0.20",
    zorder=2,linestyle=(0,(7,4))))
ax.text(10.15,CY+H/2+1.35,"실측·운영 데이터 환류 (DT → 데이터베이스 재축적)",
    ha="center",color=FB,fontsize=10.5,fontweight="bold",
    bbox=dict(boxstyle="round,pad=0.2",fc="white",ec="none",alpha=0.9))

# ===== Agent layer (cross-cutting, bottom) =====
ax.add_patch(FancyBboxPatch((0.7,1.0),19.1,3.3,boxstyle="round,pad=0.08",
    fc="#eef6f0",ec=AXC,lw=2,ls=(0,(6,4)),zorder=0))
ax.text(1.05,4.05,"전략4. AI Researcher — Agent 계층  (전 영역 횡단 적용)",
    color=AXC,fontsize=13,fontweight="bold",zorder=1)
ay=2.4
def agent(cx,w,txt):
    ax.add_patch(FancyBboxPatch((cx-w/2,ay-0.55),w,1.1,boxstyle="round,pad=0.04",
        fc="#dcefe2",ec=AXC,lw=1.6,zorder=3))
    ax.text(cx,ay,txt,ha="center",va="center",color="#1d4d33",fontsize=10,
        fontweight="bold",zorder=4,linespacing=1.0)
agent(2.7,3.0,"데이터 Agent")
agent(7.7,3.4,"해석 Agent")
agent(12.95,3.2,"Agent 스토어\n·오케스트레이션")
agent(17.6,3.2,"디지털트윈 Agent")

# up-arrows: agent -> each strategy (적용)
for cx,lab in [(2.7,"수집·검색 자동화"),(7.7,"해석 자동수행·설계탐색"),(17.6,"시나리오 운용·진단")]:
    arrow((cx,ay+0.55),(cx,CY-H/2),AXC,2.2,ls=(0,(4,3)),label=lab,fs=9,
        lpos=(cx,(ay+0.55+CY-H/2)/2))
# store manages agents
for cx in [2.7,7.7,17.6]:
    ax.add_patch(FancyArrowPatch((12.95+(-1.6 if cx<12.95 else 1.6),ay),
        (cx+(1.5 if cx<12.95 else -1.6),ay),arrowstyle="-",lw=1.2,color="#7aae90",
        connectionstyle="arc3,rad=0.0",zorder=1,linestyle=(0,(2,2))))

ax.text(10.25,0.55,"※ Agent는 각 세부요소(유체·구조·장비·시스템 등) 단위로 개별 적용 — 공통활용 / 연구소별 Agent",
    ha="center",fontsize=9.5,color="#666",style="italic")

plt.savefig("/home/user/similar-research-DB/tech_axdx.png",dpi=150,bbox_inches="tight")
print("saved")
