# -*- coding: utf-8 -*-
"""AX/DX 추진 온톨로지 (4개 축 + 데이터 파이프라인) 시각화."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, Circle, FancyBboxPatch
from matplotlib import font_manager as fm
import networkx as nx
import numpy as np

# ---- Korean font ----
FONT = "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf"
fm.fontManager.addfont(FONT)
fm.fontManager.addfont("/usr/share/fonts/truetype/nanum/NanumGothic.ttf")
plt.rcParams["font.family"] = "NanumGothic"
plt.rcParams["axes.unicode_minus"] = False

# domain palette
COL = {
    "pillar": "#1f4e79",   # core pillars (solid)
    "sim":    "#e8f4e8",   # 시뮬레이션 family
    "dt":     "#e3f2f5",   # 디지털트윈 family
    "data":   "#fdecd9",   # 데이터/파이프라인 family
    "ai":     "#efe6f7",   # agentic/AI family
    "org":    "#eeeeee",   # 조직/사람
}
EDGE_COL = {"sim": "#3a7d3a", "dt": "#2f8f9d", "data": "#d98324", "ai": "#7b52ab", "org": "#888888"}

# ---- Nodes: id -> (label, domain, kind) ; kind: pillar|class ----
N = {
    # 4 pillars (core)
    "SIM":   ("sim:시뮬레이션가속", "sim", "pillar"),
    "DT":    ("dt:디지털트윈", "dt", "pillar"),
    "DB":    ("data:데이터베이스", "data", "pillar"),
    "AGT":   ("ai:AgenticResearcher", "ai", "pillar"),
    # simulation family
    "AMODEL":("sim:해석모델", "sim", "class"),
    "SURR":  ("sim:대리·축소모델", "sim", "class"),
    "HPC":   ("sim:연산자원(HPC)", "sim", "class"),
    "SRES":  ("sim:해석결과", "sim", "class"),
    # digital twin family
    "SENS":  ("dt:센서데이터", "dt", "class"),
    "GEO":   ("dt:형상·3D모델", "dt", "class"),
    "SCEN":  ("dt:운영시나리오", "dt", "class"),
    # data pipeline family (from AWS arch)
    "SRC":   ("data:데이터소스(Device)", "data", "class"),
    "STRM":  ("data:스트리밍(IoT·MSK)", "data", "class"),
    "ING":   ("data:수집(KafkaConnect)", "data", "class"),
    "LAKE":  ("data:데이터레이크(S3)", "data", "class"),
    "WH":    ("data:웨어하우스(Redshift)", "data", "class"),
    "MART":  ("data:데이터마트(RDS)", "data", "class"),
    "NOSQL": ("data:NoSQL(DynamoDB)", "data", "class"),
    "CACHE": ("data:캐시(Redis)", "data", "class"),
    "CAT":   ("data:카탈로그(Glue)", "data", "class"),
    "ORCH":  ("data:오케스트레이션(Airflow)", "data", "class"),
    # agentic / ai family
    "LLM":   ("ai:파운데이션모델(LLM)", "ai", "class"),
    "KG":    ("ai:지식그래프", "ai", "class"),
    # org
    "RES":   ("org:연구자", "org", "class"),
    "PROJ":  ("org:연구과제", "org", "class"),
}

# ---- Object properties (directed, labeled) ----
OBJ = [
    # data pipeline flow
    ("SRC","STRM","스트리밍전송"), ("STRM","ING","수집"), ("ING","LAKE","적재"),
    ("ING","NOSQL","적재"), ("STRM","CACHE","실시간캐시"), ("LAKE","WH","변환적재"),
    ("CAT","LAKE","메타데이터기술"), ("CAT","WH","메타데이터기술"),
    ("WH","MART","집계제공"), ("ORCH","MART","파이프라인스케줄"), ("ORCH","WH","ETL제어"),
    # simulation
    ("SIM","SRES","생성"), ("SRES","LAKE","저장"), ("DB","SURR","학습데이터제공"),
    ("SURR","SIM","가속"), ("SIM","HPC","연산활용"), ("SIM","DT","물리모델제공"),
    # digital twin
    ("DT","SIM","모델보정"), ("SENS","DT","상태반영"), ("DT","GEO","형상보유"),
    ("DT","SCEN","시나리오해석"), ("SRC","SENS","센서수집"),
    # agentic
    ("AGT","DB","질의·탐색"), ("AGT","SIM","자동해석"), ("AGT","DT","시나리오운용"),
    ("AGT","LLM","추론활용"), ("AGT","KG","지식구축"), ("KG","DB","인덱싱"),
    # org
    ("RES","PROJ","수행"), ("PROJ","AGT","활용"), ("AGT","RES","연구지원"),
]

# ---- SubClassOf (taxonomy) ----
SUB = [
    ("LAKE","DB"), ("WH","DB"), ("MART","DB"), ("NOSQL","DB"), ("CACHE","DB"),
    ("SURR","AMODEL"), ("SRES","DB"), ("SENS","DB"),
    ("SURR","LLM"),  # 대리모델도 AI모델의 일종
]

# ---- Manual layout (semantic clusters) ----
pos = {
    # pillars (spine)
    "DB":(0,0), "SIM":(-3.5,0.8), "DT":(3.5,0.8), "AGT":(0,3.5),
    # simulation family (left)
    "AMODEL":(-5.9,0.2), "SURR":(-4.9,2.1), "HPC":(-5.6,-1.5), "SRES":(-2.3,-1.7),
    # digital twin family (right)
    "SENS":(3.2,-1.5), "GEO":(5.9,0.3), "SCEN":(5.3,2.4),
    # data pipeline (bottom)
    "SRC":(-4.6,-3.9), "STRM":(-2.9,-4.4), "ING":(-1.0,-4.5), "CACHE":(-2.1,-2.7),
    "LAKE":(0.7,-3.6), "NOSQL":(1.7,-2.2), "WH":(2.7,-4.0), "CAT":(1.0,-5.2),
    "MART":(4.4,-2.9), "ORCH":(4.8,-4.7),
    # ai / org (top)
    "LLM":(2.3,4.5), "KG":(-1.9,2.9), "RES":(-3.8,4.3), "PROJ":(-1.9,4.7),
}

fig, ax = plt.subplots(figsize=(19,13))
ax.set_axis_off()
ax.set_aspect("equal")
ax.set_xlim(-7.2,7.2); ax.set_ylim(-6.2,5.6)

R_PILLAR, R_CLASS = 0.62, 0.46

def draw_edge(u,v,color,style,label=None,rad=0.12,lw=1.2):
    p1,p2 = np.array(pos[u],float), np.array(pos[v],float)
    sa = R_PILLAR if N[u][2]=="pillar" else R_CLASS
    sb = R_PILLAR if N[v][2]=="pillar" else R_CLASS
    # convert data-unit shrink to points approx (fig ~equal aspect)
    arr = FancyArrowPatch(p1,p2, connectionstyle=f"arc3,rad={rad}",
                          arrowstyle="-|>", mutation_scale=11,
                          lw=lw, color=color, linestyle=style,
                          shrinkA=sa*34, shrinkB=sb*34, zorder=1, alpha=0.85)
    ax.add_patch(arr)
    if label:
        d = p2-p1; L=np.linalg.norm(d)+1e-9
        nrm = np.array([-d[1],d[0]])/L
        mid = (p1+p2)/2 + nrm*(rad*L*0.5) + nrm*0.10
        ax.text(mid[0],mid[1],label,fontsize=6.2,color=color,ha="center",va="center",
                zorder=4, alpha=0.95,
                bbox=dict(boxstyle="round,pad=0.08",fc="white",ec="none",alpha=0.55))

for u,v,l in OBJ:
    draw_edge(u,v,EDGE_COL[N[u][1]],"-",l,rad=0.14,lw=1.1)
for u,v in SUB:
    draw_edge(u,v,"#d24a6e","--",None,rad=-0.10,lw=1.4)

for n,(label,dom,kind) in N.items():
    x,y = pos[n]
    disp = label.replace(":", ":\n", 1)
    if kind=="pillar":
        ax.add_patch(Circle((x,y),R_PILLAR,facecolor=COL["pillar"],edgecolor="#0d2c47",
                            lw=2.2,zorder=3))
        ax.text(x,y,disp,fontsize=8.6,color="white",ha="center",va="center",
                zorder=5,fontweight="bold",linespacing=1.1)
    else:
        ax.add_patch(Circle((x,y),R_CLASS,facecolor=COL[dom],edgecolor=EDGE_COL[dom],
                            lw=1.6,linestyle="--",zorder=3))
        ax.text(x,y,disp,fontsize=6.0,color="#222",ha="center",va="center",
                zorder=5,linespacing=1.0)

# legend (bottom-left)
lx,ly = -7.0, -3.2
ax.add_patch(FancyBboxPatch((lx-0.15,ly-2.05),4.4,2.25,boxstyle="round,pad=0.05",
            fc="white",ec="#999",lw=1,zorder=6))
ax.add_patch(Circle((lx+0.3,ly-0.25),0.18,facecolor=COL["pillar"],ec="#0d2c47",zorder=7))
ax.text(lx+0.65,ly-0.25,"핵심 클래스 (4대 추진축)",fontsize=8.5,va="center",zorder=7)
ax.add_patch(Circle((lx+0.3,ly-0.8),0.18,facecolor="#eef6ee",ec="#3a7d3a",ls="--",zorder=7))
ax.text(lx+0.65,ly-0.8,"온톨로지 클래스",fontsize=8.5,va="center",zorder=7)
ax.annotate("",xy=(lx+0.5,ly-1.35),xytext=(lx+0.1,ly-1.35),
            arrowprops=dict(arrowstyle="-|>",color="#555"),zorder=7)
ax.text(lx+0.65,ly-1.35,"Object Property (관계)",fontsize=8.5,va="center",zorder=7)
ax.annotate("",xy=(lx+0.5,ly-1.85),xytext=(lx+0.1,ly-1.85),
            arrowprops=dict(arrowstyle="-|>",color="#d24a6e",ls="--"),zorder=7)
ax.text(lx+0.65,ly-1.85,"SubClassOf (계층)",fontsize=8.5,va="center",zorder=7)

ax.set_title("AX·DX 추진 온톨로지 — 4대 축 + 데이터 파이프라인 통합도",
             fontsize=16,fontweight="bold",pad=12)
plt.savefig("/home/user/similar-research-DB/ontology_axdx.png",dpi=150,bbox_inches="tight")
print("saved")
