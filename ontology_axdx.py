# -*- coding: utf-8 -*-
"""HD한국조선해양 미래기술연구원 AX/DX 추진 로드맵 온톨로지.
4대 전략(DX:1~3, AX:4) + 세부 도메인 + 데이터 파이프라인 통합 관계도."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, Circle, FancyBboxPatch
from matplotlib import font_manager as fm
import numpy as np

for f in ["NanumGothic.ttf","NanumGothicBold.ttf"]:
    fm.fontManager.addfont(f"/usr/share/fonts/truetype/nanum/{f}")
plt.rcParams["font.family"] = "NanumGothic"
plt.rcParams["axes.unicode_minus"] = False

# ---- color by family ----
PILL = {"dx": "#1f4e79", "ax": "#2e7d4f"}          # pillar fills
FILL = {"sim":"#dbe7f3","dt":"#dbe7f3","db":"#dbe7f3","pipe":"#fdecd9",
        "ai":"#dcefe2","tech":"#efe6f7"}
ECOL = {"sim":"#2f5d8a","dt":"#2f5d8a","db":"#2f5d8a","pipe":"#d98324",
        "ai":"#3a7d3a","tech":"#7b52ab"}
SUBCOL = "#d24a6e"

# id -> (label, family, kind, pos)   kind: pillar|class ; pillar uses dx/ax via fam2
N = {
 # ---- 4 strategy pillars ----
 "S1": ("전략1\n데이터베이스 구축","db","pillar",(-6.2, 2.0)),
 "S2": ("전략2\n시뮬레이션 가속화","sim","pillar",(-1.0, 2.4)),
 "S3": ("전략3\n디지털트윈 구현","dt","pillar",(3.6, 2.4)),
 "S4": ("전략4\nAI Researcher","ai","pillar",(7.4, 4.4)),
 # ---- 전략2 시뮬레이션 세부 ----
 "SF": ("유체흐름\nGPU CFD","sim","class",(-3.0,0.0)),
 "SS": ("구조안전\nSimSolid·FE","sim","class",(-0.7,-0.3)),
 "SV": ("선박진동\nJAX·ACMS","sim","class",(1.3,0.2)),
 "SD": ("변형제어\n예측모델","sim","class",(2.6,1.3)),
 "GPU":("연산자원\nGPU·HPC","tech","class",(-2.8,4.0)),
 "ROM":("ROM\n해석데이터자산","tech","class",(-0.1,4.3)),
 # ---- 전략3 디지털트윈 세부 ----
 "DEQ":("장비DT\nAIP·LIB·압축기","dt","class",(5.8,0.6)),
 "CHS":("AI CHS\n화물제어","dt","class",(3.7,-0.7)),
 "EPS":("전기추진\nLBTS","dt","class",(2.0,-1.5)),
 "AMN":("암모니아\n안전실증","dt","class",(4.6,-1.8)),
 "USV":("USV\n자율운항","dt","class",(6.6,1.4)),
 "MFG":("생산공정\n가상검증DT","dt","class",(6.1,-0.7)),
 "COS":("1D-3D\nCo-sim","tech","class",(3.1,4.1)),
 # ---- 전략1 DB 세부 ----
 "PRD":("생산실적\n센서·영상","db","class",(-8.8,3.6)),
 "RND":("연구데이터\n도면·해석","db","class",(-9.0,1.2)),
 "HW": ("R&D hi-way\n플랫폼","db","class",(-6.4,-0.4)),
 "OCR":("OCR\n텍스트화","tech","class",(-9.2,-0.9)),
 "VLM":("VLM\n비정형검색","tech","class",(-8.6,-2.5)),
 # ---- 데이터 파이프라인 (AWS) ----
 "SRC":("데이터소스\nDevice","pipe","class",(-6.2,-3.7)),
 "STR":("스트리밍\nIoT·MSK","pipe","class",(-4.4,-4.5)),
 "ING":("수집\nKafka Connect","pipe","class",(-2.4,-4.9)),
 "CAC":("캐시\nRedis","pipe","class",(-3.6,-2.9)),
 "LAK":("데이터레이크\nS3","pipe","class",(-0.3,-4.7)),
 "NOS":("NoSQL\nDynamoDB","pipe","class",(-1.1,-3.0)),
 "CAT":("카탈로그\nGlue","pipe","class",(0.9,-3.2)),
 "WH": ("웨어하우스\nRedshift","pipe","class",(1.7,-4.7)),
 "MRT":("데이터마트\nRDS","pipe","class",(3.7,-4.1)),
 "ORC":("오케스트레이션\nAirflow","pipe","class",(3.3,-5.7)),
 # ---- 전략4 AX 세부 ----
 "CMA":("공통활용\nAgent","ai","class",(5.6,5.9)),
 "LBA":("연구소별\nAgent","ai","class",(7.9,6.1)),
 "AST":("Agent\n스토어","ai","class",(9.2,4.3)),
 "ORF":("오케스트레이션\n프레임워크","ai","class",(9.0,2.6)),
 "LLM":("파운데이션\n모델 LLM","tech","class",(5.0,3.0)),
}
PILLFAM = {"S1":"dx","S2":"dx","S3":"dx","S4":"ax"}

# ---- object properties (labeled) ----
OBJ = [
 # cross-pillar (DX flow + AX loop)
 ("S1","S2","해석데이터·ROM"),("S2","S1","해석결과 축적"),
 ("S2","S3","물리·GPU모델"),("S3","S2","실측 보정"),("S3","S1","운영데이터"),
 ("S1","S4","학습데이터 기반"),("S3","S4","활용"),("S4","S1","환류"),
 ("S2","HW","데이터연계"),("S3","HW","데이터연계"),
 # enabling
 ("GPU","S2","가속"),("ROM","S1","자산화"),("COS","S3","통합"),
 ("LLM","S4","검색·추론"),("OCR","RND","텍스트화"),("VLM","RND","비정형검색"),
 ("AST","CMA","게시·수집"),("ORF","AST","Agent간 협업"),
 # data pipeline flow
 ("SRC","STR","스트리밍"),("STR","ING","수집"),("ING","LAK","적재"),
 ("ING","NOS","적재"),("STR","CAC","캐시"),("LAK","WH","변환"),
 ("CAT","LAK","카탈로그"),("WH","MRT","집계"),("ORC","WH","ETL"),("ORC","MRT","스케줄"),
 ("SRC","PRD","현장수집"),("MRT","HW","서빙"),
]
# ---- subClassOf (membership / taxonomy) ----
SUB = [
 ("SF","S2"),("SS","S2"),("SV","S2"),("SD","S2"),
 ("DEQ","S3"),("CHS","S3"),("EPS","S3"),("AMN","S3"),("USV","S3"),("MFG","S3"),
 ("PRD","S1"),("RND","S1"),("HW","S1"),
 ("LAK","S1"),("WH","S1"),("MRT","S1"),("NOS","S1"),("CAC","S1"),
 ("CMA","S4"),("LBA","S4"),("AST","S4"),
]

pos = {k:v[3] for k,v in N.items()}
fig, ax = plt.subplots(figsize=(23,15.5))
ax.set_axis_off(); ax.set_aspect("equal")
ax.set_xlim(-10.2,10.6); ax.set_ylim(-7.0,7.8)

R_P, R_C, SCALE = 0.70, 0.54, 36.0
def draw_edge(u,v,color,style,label=None,rad=0.13,lw=1.1):
    p1,p2 = np.array(pos[u],float), np.array(pos[v],float)
    ra = R_P if N[u][2]=="pillar" else R_C
    rb = R_P if N[v][2]=="pillar" else R_C
    ax.add_patch(FancyArrowPatch(p1,p2,connectionstyle=f"arc3,rad={rad}",
        arrowstyle="-|>",mutation_scale=10,lw=lw,color=color,linestyle=style,
        shrinkA=ra*SCALE,shrinkB=rb*SCALE,zorder=1,alpha=0.8))
    if label:
        d=p2-p1; L=np.linalg.norm(d)+1e-9; nrm=np.array([-d[1],d[0]])/L
        m=(p1+p2)/2+nrm*(rad*L*0.5)+nrm*0.12
        ax.text(m[0],m[1],label,fontsize=6.0,color=color,ha="center",va="center",
            zorder=4,bbox=dict(boxstyle="round,pad=0.06",fc="white",ec="none",alpha=0.6))

for u,v,l in OBJ:
    draw_edge(u,v,ECOL[N[u][1]],"-",l,rad=0.13,lw=1.15)
for u,v in SUB:
    draw_edge(u,v,SUBCOL,"--",None,rad=-0.09,lw=1.3)

for n,(label,fam,kind,p) in N.items():
    x,y=p
    if kind=="pillar":
        ax.add_patch(Circle((x,y),R_P,facecolor=PILL[PILLFAM[n]],edgecolor="#0d2c47",
            lw=2.2,zorder=3))
        ax.text(x,y,label,fontsize=8.6,color="white",ha="center",va="center",
            zorder=5,fontweight="bold",linespacing=1.05)
    else:
        ax.add_patch(Circle((x,y),R_C,facecolor=FILL[fam],edgecolor=ECOL[fam],
            lw=1.5,linestyle="--",zorder=3))
        ax.text(x,y,label,fontsize=5.7,color="#1a1a1a",ha="center",va="center",
            zorder=5,linespacing=1.0)

# ---- paradigm banner (top) ----
def banner(x,txt,fc,ec):
    ax.add_patch(FancyBboxPatch((x-1.9,7.0),3.8,0.7,boxstyle="round,pad=0.05",
        fc=fc,ec=ec,lw=1.4,zorder=6))
    ax.text(x,7.35,txt,fontsize=8.5,ha="center",va="center",zorder=7,fontweight="bold")
banner(-4.5,"AS-IS  기다리고 확인하던 R&D","#f2dede","#c0504d")
banner(1.5,"TO-BE  빠르게 실험·즉시 반영 R&D","#e2efda","#4f9a4f")
ax.annotate("",xy=(-1.0,7.35),xytext=(-2.6,7.35),
    arrowprops=dict(arrowstyle="-|>",color="#4f9a4f",lw=2.5),zorder=7)
ax.text(-1.8,7.72,"패러다임 전환 · AI는 전제",fontsize=8,ha="center",color="#555",zorder=7)

# ---- DX / AX group boxes ----
ax.add_patch(FancyBboxPatch((-10.0,-6.6),16.3,9.6,boxstyle="round,pad=0.1",
    fc="none",ec="#1f4e79",lw=1.6,ls=(0,(6,4)),zorder=0))
ax.text(-9.7,2.7,"DX 추진전략",fontsize=12,color="#1f4e79",fontweight="bold",zorder=2)
ax.add_patch(FancyBboxPatch((4.2,2.0),6.2,4.6,boxstyle="round,pad=0.1",
    fc="none",ec="#2e7d4f",lw=1.6,ls=(0,(6,4)),zorder=0))
ax.text(9.9,6.4,"AX 추진전략",fontsize=12,color="#2e7d4f",fontweight="bold",
    ha="right",zorder=2)

# ---- legend ----
lx,ly=5.7,-4.2
ax.add_patch(FancyBboxPatch((lx,ly-2.2),4.7,2.45,boxstyle="round,pad=0.05",
    fc="white",ec="#999",lw=1,zorder=8))
ax.add_patch(Circle((lx+0.35,ly-0.25),0.2,fc=PILL["dx"],ec="#0d2c47",zorder=9))
ax.text(lx+0.7,ly-0.25,"DX 핵심전략 (1~3)",fontsize=8.5,va="center",zorder=9)
ax.add_patch(Circle((lx+0.35,ly-0.8),0.2,fc=PILL["ax"],ec="#0d2c47",zorder=9))
ax.text(lx+0.7,ly-0.8,"AX 핵심전략 (4)",fontsize=8.5,va="center",zorder=9)
ax.add_patch(Circle((lx+0.35,ly-1.35),0.2,fc=FILL["pipe"],ec=ECOL["pipe"],ls="--",zorder=9))
ax.text(lx+0.7,ly-1.35,"세부 클래스 (도메인·파이프라인)",fontsize=8.5,va="center",zorder=9)
ax.annotate("",xy=(lx+0.55,ly-1.85),xytext=(lx+0.15,ly-1.85),
    arrowprops=dict(arrowstyle="-|>",color="#555"),zorder=9)
ax.text(lx+0.7,ly-1.85,"Object Property (관계)",fontsize=8.5,va="center",zorder=9)
ax.annotate("",xy=(lx+0.55,ly-2.35),xytext=(lx+0.15,ly-2.35),
    arrowprops=dict(arrowstyle="-|>",color=SUBCOL,ls="--"),zorder=9)
ax.text(lx+0.7,ly-2.35,"SubClassOf (계층)",fontsize=8.5,va="center",zorder=9)

ax.set_title("HD한국조선해양 미래기술연구원  ·  AX/DX 추진 로드맵 온톨로지",
    fontsize=17,fontweight="bold",pad=10)
plt.savefig("/home/user/similar-research-DB/ontology_axdx.png",dpi=150,bbox_inches="tight")
print("saved")
