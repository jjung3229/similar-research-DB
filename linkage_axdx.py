# -*- coding: utf-8 -*-
"""AX/DX 추진 연계 상세도 — 세부 항목(노드) 단위 실제 연결 관계."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
from matplotlib import font_manager as fm
import numpy as np

for f in ["NanumGothic.ttf","NanumGothicBold.ttf"]:
    fm.fontManager.addfont(f"/usr/share/fonts/truetype/nanum/{f}")
plt.rcParams["font.family"]="NanumGothic"; plt.rcParams["axes.unicode_minus"]=False

DXC, AXC = "#1f4e79", "#2e7d4f"
C_DB, C_SIM, C_DT, C_AI, C_PIPE = "#1f6fae", "#2e8b8b", "#8a6d3b", "#2e7d4f", "#d98324"
C_FB = "#c0504d"  # feedback

# columns: x, color, title, ybot, ytop
COLS = {
 "DB":(3.8, DXC,"전략1. 데이터베이스", 3.0, 9.6),
 "SIM":(9.9, DXC,"전략2. 시뮬레이션 가속", 2.8, 9.9),
 "DT":(16.0, DXC,"전략3. 디지털트윈", 1.5, 9.9),
 "AI":(22.1, AXC,"전략4. AI Researcher", 3.0, 9.3),
}
# nodes: key -> (col, y, label, fill)
NF = {"DB":"#dbe7f3","SIM":"#dbe7f3","DT":"#dbe7f3","AI":"#dcefe2"}
N = {
 "DB.PRD":("DB",8.7,"생산실적\n센서·영상"),
 "DB.RND":("DB",7.1,"연구데이터\nR&D hi-way"),
 "DB.ROM":("DB",5.5,"ROM\n해석데이터 자산"),
 "DB.UNS":("DB",3.9,"비정형\nOCR·VLM"),
 "SIM.CFD":("SIM",9.2,"유체 GPU CFD"),
 "SIM.STR":("SIM",7.8,"구조 SimSolid·FE"),
 "SIM.VIB":("SIM",6.4,"선박진동 JAX·ACMS"),
 "SIM.DEF":("SIM",5.0,"변형 예측·제어"),
 "SIM.COS":("SIM",3.6,"1D-3D Co-sim"),
 "DT.EQ":("DT",9.2,"장비DT\nAIP·LIB·압축기"),
 "DT.AMN":("DT",7.8,"암모니아 안전실증"),
 "DT.USV":("DT",6.4,"USV 자율운항"),
 "DT.EPS":("DT",5.0,"전기추진 LBTS"),
 "DT.CHS":("DT",3.6,"AI CHS 화물제어"),
 "DT.MFG":("DT",2.2,"생산공정 가상검증"),
 "AI.AIP":("AI",8.6,"AIP Agent\n선급 검증"),
 "AI.CMA":("AI",7.0,"공통활용 Agent"),
 "AI.LBA":("AI",5.4,"연구소별 Agent"),
 "AI.STO":("AI",3.8,"Agent 스토어\n·오케스트레이션"),
}
NW, NH = 1.7, 0.52
def cx(k): return COLS[N[k][0]][0]
def cy(k): return N[k][1]

# edges: (src, dst, label, color, mode, rad, style, lpos)
E = [
 ("DB.UNS","DB.RND","검색데이터셋화", C_DB,"v",0.0,"-",None),
 ("DB.ROM","SIM.CFD","ROM·해석자산 재사용", C_DB,"h",0.05,"-",None),
 ("SIM.CFD","DT.AMN","CFD 실시간 안전설계", C_SIM,"h",0.02,"-",None),
 ("SIM.CFD","DT.USV","실-simulation 해석검증", C_SIM,"h",-0.18,"-",(13.0,7.15)),
 ("SIM.COS","DT.EQ","1D-3D 통합 DT", C_SIM,"h",0.30,"-",(13.3,5.3)),
 ("SIM.STR","AI.AIP","선급 검증체계", C_SIM,"arc",-0.26,"-",(19.6,10.5)),
 ("DB.RND","AI.CMA","학습데이터 기반", C_DB,"arc",-0.30,"-",(15.0,11.4)),
 ("DB.RND","AI.LBA","", C_DB,"arc",-0.40,"-",None),
 ("AI.AIP","AI.STO","",C_AI,"v",0.0,"-",None),
 ("AI.CMA","AI.STO","스토어 등록·오케스트레이션",C_AI,"v",0.0,"-",None),
 ("AI.LBA","AI.STO","",C_AI,"v",0.0,"-",None),
 ("DT.EQ","DB.RND","시뮬·DT 데이터 연계('28)", C_FB,"arc",0.34,"--",(12.3,12.3)),
 ("AI.CMA","DB.RND","환류: 규정·지식 데이터셋", C_FB,"arc",0.46,"--",(8.5,13.2)),
]

fig, ax = plt.subplots(figsize=(26,15))
ax.set_axis_off(); ax.set_xlim(0,26.5); ax.set_ylim(0,14.8)

# containers + titles
for k,(x,col,title,yb,yt) in COLS.items():
    ax.add_patch(FancyBboxPatch((x-2.15,yb),4.3,yt-yb,boxstyle="round,pad=0.08",
        fc="#fbfcfe",ec=col,lw=1.8,ls=(0,(6,4)),zorder=0))
    ax.text(x,yt+0.35,title,ha="center",fontsize=14,fontweight="bold",color=col,zorder=2)

def node(k):
    x,y=cx(k),cy(k); lab=N[k][2]; col=COLS[N[k][0]][1]
    ax.add_patch(FancyBboxPatch((x-NW,y-NH),2*NW,2*NH,boxstyle="round,pad=0.04",
        fc=NF[N[k][0]],ec=col,lw=1.6,zorder=3))
    ax.text(x,y,lab,ha="center",va="center",fontsize=9.3,color="#1a1a1a",zorder=4,
        linespacing=1.05)
for k in N: node(k)

def edge(s,d,label,color,mode,rad,style,lpos=None):
    if mode=="h":
        if cx(d)>cx(s): p1=(cx(s)+NW,cy(s)); p2=(cx(d)-NW,cy(d))
        else: p1=(cx(s)-NW,cy(s)); p2=(cx(d)+NW,cy(d))
    elif mode=="v":
        if cy(d)<cy(s): p1=(cx(s),cy(s)-NH); p2=(cx(d),cy(d)+NH)
        else: p1=(cx(s),cy(s)+NH); p2=(cx(d),cy(d)-NH)
    else:  # arc over the top
        p1=(cx(s),cy(s)+NH); p2=(cx(d),cy(d)+NH)
    lw=2.3 if style=="-" else 2.0
    ax.add_patch(FancyArrowPatch(p1,p2,arrowstyle="-|>",mutation_scale=18,lw=lw,
        color=color,linestyle=style,connectionstyle=f"arc3,rad={rad}",zorder=2,alpha=0.9))
    if label:
        if lpos: m=lpos
        else:
            p1=np.array(p1,float); p2=np.array(p2,float)
            d_=p2-p1; L=np.linalg.norm(d_)+1e-9; nrm=np.array([-d_[1],d_[0]])/L
            m=(p1+p2)/2 + nrm*(rad*L*0.6)
        ax.text(m[0],m[1],label,ha="center",va="center",fontsize=8.6,color=color,
            fontweight="bold",zorder=6,
            bbox=dict(boxstyle="round,pad=0.18",fc="white",ec=color,lw=0.6,alpha=0.95))
for e in E: edge(*e)

# ---- data pipeline (bottom, feeds DB.PRD) ----
PY=0.9
ax.add_patch(FancyBboxPatch((0.6,0.3),10.6,1.5,boxstyle="round,pad=0.06",
    fc="#fff7ef",ec=C_PIPE,lw=1.6,ls=(0,(5,4)),zorder=0))
ax.text(0.85,1.55,"데이터 파이프라인 (AWS)",color="#a85f12",fontsize=10.5,
    fontweight="bold",zorder=1)
chain=[("Device",1.7),("IoT Core",3.1),("MSK",4.5),("Kafka\nConnect",5.9),
       ("S3",7.2),("Redshift",8.6),("RDS",10.0)]
for i,(t,x) in enumerate(chain):
    ax.add_patch(FancyBboxPatch((x-0.62,PY-0.32),1.24,0.64,boxstyle="round,pad=0.03",
        fc="#fdecd9",ec=C_PIPE,lw=1.2,zorder=3))
    ax.text(x,PY,t,ha="center",va="center",fontsize=7.5,color="#6b3d09",zorder=4,linespacing=0.9)
    if i>0: ax.add_patch(FancyArrowPatch((chain[i-1][1]+0.64,PY),(x-0.64,PY),
        arrowstyle="-|>",mutation_scale=11,lw=1.4,color=C_PIPE,zorder=2))
ax.add_patch(FancyArrowPatch((3.8,1.85),(3.8,cy("DB.PRD")-NH),arrowstyle="-|>",
    mutation_scale=18,lw=2.2,color=C_PIPE,zorder=2))
ax.text(4.0,2.45,"센서·영상\n자동수집",fontsize=8.2,color="#a85f12",fontweight="bold",zorder=4)

# ---- 미연계 강조 노트 ----
ax.text(9.9,1.3,"※ 선박진동·변형 해석은 자체 설계에 적용 — 디지털트윈 직접 연계 아님",
    ha="center",fontsize=9.5,color="#888",style="italic",zorder=5)

# ---- legend ----
lx,ly=18.7,2.4
ax.add_patch(FancyBboxPatch((lx,ly-1.8),7.2,2.0,boxstyle="round,pad=0.06",
    fc="white",ec="#999",lw=1,zorder=8))
def lkey(yy,color,style,txt):
    ax.add_patch(FancyArrowPatch((lx+0.3,yy),(lx+1.1,yy),arrowstyle="-|>",
        mutation_scale=14,lw=2.2,color=color,linestyle=style,zorder=9))
    ax.text(lx+1.35,yy,txt,va="center",fontsize=9,zorder=9)
lkey(ly-0.3,C_DB,"-","데이터 제공/학습 (전략1→)")
lkey(ly-0.75,C_SIM,"-","해석 결과 활용 (전략2→)")
lkey(ly-1.2,C_AI,"-","Agent 구성 (전략4 내부)")
lkey(ly-1.65,C_FB,"--","환류·데이터 연계 (피드백)")

ax.set_title("HD한국조선해양 미래기술연구원 · AX/DX 추진 연계 상세도 (세부 항목 단위)",
    fontsize=18,fontweight="bold",pad=12)
plt.savefig("/home/user/similar-research-DB/linkage_axdx.png",dpi=150,bbox_inches="tight")
print("saved")
