# -*- coding: utf-8 -*-
"""HD한국조선해양 미래기술연구원 AX/DX 추진 파이프라인 (흐름도)."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
from matplotlib import font_manager as fm

for f in ["NanumGothic.ttf","NanumGothicBold.ttf"]:
    fm.fontManager.addfont(f"/usr/share/fonts/truetype/nanum/{f}")
plt.rcParams["font.family"] = "NanumGothic"
plt.rcParams["axes.unicode_minus"] = False

DXC, AXC, TOC, PIPE = "#1f4e79", "#2e7d4f", "#c0504d", "#d98324"

fig, ax = plt.subplots(figsize=(24,12.5))
ax.set_axis_off(); ax.set_xlim(0,24); ax.set_ylim(0,13)

def block(cx, cy, w, h, title, bullets, fc, tc="white", bc=None, fs=12):
    bc = bc or fc
    ax.add_patch(FancyBboxPatch((cx-w/2, cy-h/2), w, h, boxstyle="round,pad=0.06",
        fc=fc, ec=bc, lw=2, zorder=3, mutation_aspect=0.9))
    ax.text(cx, cy+h/2-0.35, title, ha="center", va="top", color=tc,
        fontsize=fs, fontweight="bold", zorder=4)
    if bullets:
        ax.text(cx, cy+h/2-0.95, "\n".join("· "+b for b in bullets), ha="center",
            va="top", color=tc, fontsize=9.2, zorder=4, linespacing=1.5)

def smallbox(cx, cy, w, h, txt, fc, ec, tc="#222", fs=8.5):
    ax.add_patch(FancyBboxPatch((cx-w/2, cy-h/2), w, h, boxstyle="round,pad=0.04",
        fc=fc, ec=ec, lw=1.4, zorder=3))
    ax.text(cx, cy, txt, ha="center", va="center", color=tc, fontsize=fs, zorder=4,
        linespacing=1.0)

def arrow(p1, p2, color, lw=2.4, rad=0.0, label=None, ls="-", fs=10):
    ax.add_patch(FancyArrowPatch(p1, p2, arrowstyle="-|>", mutation_scale=22,
        lw=lw, color=color, connectionstyle=f"arc3,rad={rad}", zorder=2, linestyle=ls))
    if label:
        mx, my = (p1[0]+p2[0])/2, (p1[1]+p2[1])/2
        ax.text(mx, my+0.28, label, ha="center", va="bottom", color=color,
            fontsize=fs, fontweight="bold", zorder=5,
            bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.85))

# ===== Title =====
ax.text(12, 12.5, "HD한국조선해양 미래기술연구원 · AX/DX 추진 파이프라인",
    ha="center", fontsize=20, fontweight="bold")

# ===== Paradigm banner =====
smallbox(4.0, 11.4, 5.2, 0.7, "AS-IS  기다리고 확인하던 R&D", "#f2dede", "#c0504d", "#7a2b29", 11)
arrow((6.8,11.4),(8.2,11.4), "#4f9a4f", 3, label="패러다임 전환 · AI는 전제", fs=10.5)
smallbox(11.5, 11.4, 5.6, 0.7, "TO-BE  빠르게 실험·즉시 반영하는 R&D", "#e2efda", "#4f9a4f", "#2e5e2e", 11)

# ===== Main strategy flow (4 blocks) =====
W, H, CY = 4.0, 4.2, 7.0
xs = [2.6, 7.4, 12.2, 17.0]
block(xs[0], CY, W, H, "전략1. 데이터베이스",
    ["생산실적 (센서·영상)","연구데이터 (도면·해석)","R&D hi-way 플랫폼","OCR·VLM 비정형 검색"], DXC)
block(xs[1], CY, W, H, "전략2. 시뮬레이션 가속",
    ["유체 GPU CFD","구조 SimSolid·FE","선박진동 JAX·ACMS","변형 예측·제어","GPU·ROM 자산화"], DXC)
block(xs[2], CY, W, H, "전략3. 디지털트윈",
    ["장비DT (AIP·LIB·압축기)","AI CHS · 전기추진","암모니아 · USV","생산공정 가상검증","1D-3D Co-sim"], DXC)
block(xs[3], CY, W, H, "전략4. AI Researcher",
    ["공통활용 Agent","연구소별 Agent","Agent 스토어","오케스트레이션 FW","LLM 기반 검색·추론"], AXC)

# forward arrows
arrow((xs[0]+W/2, CY),(xs[1]-W/2, CY), DXC, 2.6, label="데이터·ROM 제공")
arrow((xs[1]+W/2, CY),(xs[2]-W/2, CY), DXC, 2.6, label="물리·GPU 모델")
arrow((xs[2]+W/2, CY),(xs[3]-W/2, CY), AXC, 2.6, label="활용")
# 전략2 <-> 전략3 보정 (return, below)
arrow((xs[2]-W/2, CY-1.2),(xs[1]+W/2, CY-1.2), "#7f9ab5", 1.6, rad=0.0, label="실측 보정", fs=8.5)

# DX / AX zone labels
ax.text(xs[0]-W/2, CY+H/2+0.35, "DX 추진전략", color=DXC, fontsize=13, fontweight="bold")
ax.text(xs[3]+W/2, CY+H/2+0.35, "AX 추진전략", color=AXC, fontsize=13, fontweight="bold", ha="right")

# ===== TO-BE outcome (right) =====
block(21.4, CY, 4.0, 4.2, "TO-BE 성과",
    ["검증시간 8배 단축","수집 공수 20% 절감","연구원 1명이 3명 성과","협업 연구 생태계"], TOC, bc="#7a2b29")
arrow((xs[3]+W/2, CY),(21.4-2.0, CY), TOC, 2.6, label="생산성")

# ===== 환류 feedback loop (top arc, 전략4 -> 전략1) =====
ax.add_patch(FancyArrowPatch((xs[3], CY+H/2),(xs[0], CY+H/2), arrowstyle="-|>",
    mutation_scale=24, lw=2.6, color=AXC, connectionstyle="arc3,rad=-0.16",
    zorder=2, linestyle=(0,(7,4))))
ax.text((xs[0]+xs[3])/2, CY+H/2+1.45, "환류  (자동화·연구 지원 → DX 재투입)",
    ha="center", color=AXC, fontsize=11, fontweight="bold",
    bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.85))

# ===== Data pipeline (bottom) feeding 전략1 =====
PY = 2.0
ax.add_patch(FancyBboxPatch((0.6, 0.6), 16.6, 2.9, boxstyle="round,pad=0.1",
    fc="#fff7ef", ec=PIPE, lw=1.8, ls=(0,(6,4)), zorder=0))
ax.text(0.9, 3.25, "데이터 파이프라인  (전략1 구현 · AWS)", color="#a85f12",
    fontsize=12, fontweight="bold", zorder=1)
chain = [("Device\n차량·설비",1.9),("IoT Core",3.6),("MSK\n(Raw)",5.3),
         ("Kafka\nConnect",7.0),("S3\n데이터레이크",8.9),("Glue\n카탈로그",10.7),
         ("Redshift\n웨어하우스",12.6),("Airflow\n오케스트레이션",14.6),("RDS\n데이터마트",16.4)]
for i,(t,x) in enumerate(chain):
    smallbox(x, PY, 1.55, 0.95, t, "#fdecd9", PIPE, "#6b3d09", 8.2)
    if i>0:
        px = chain[i-1][1]
        arrow((px+0.78, PY),(x-0.78, PY), PIPE, 1.7)
# side stores
smallbox(8.9, 0.95, 1.55, 0.55, "DynamoDB", "#fdecd9", PIPE, "#6b3d09", 8)
smallbox(7.0, 0.95, 1.4, 0.55, "Redis", "#fdecd9", PIPE, "#6b3d09", 8)
arrow((7.0,PY-0.48),(7.0,0.95+0.28), PIPE, 1.3)
arrow((7.78,PY),(8.9,0.95+0.28), PIPE, 1.3, rad=-0.1)
# up into 전략1
arrow((2.6, 3.55),(2.6, CY-H/2), PIPE, 2.6, label="R&D hi-way 적재")

plt.savefig("/home/user/similar-research-DB/pipeline_axdx.png", dpi=150, bbox_inches="tight")
print("saved")
