import math, matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams.update({"font.family":"serif","font.size":8})
def wil(k,n,z=1.96):
    p=k/n; d=1+z*z/n; c=(p+z*z/(2*n))/d; h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
    return max(0,c-h),min(1,c+h)
cls=["C0","N0","I-N","I-C","I-B","N-I"]
K={"S0":[0,0,1,8,35,43],"S1":[0,0,0,0,0,32],"S2":[0,0,0,0,0,20]}
fig,ax=plt.subplots(figsize=(3.5,2.4))
for j,(s,h) in enumerate(zip(K,["","//","xx"])):
    y=[k/60 for k in K[s]]; ci=[wil(k,60) for k in K[s]]
    ax.bar([i+j*0.27 for i in range(6)],y,0.27,yerr=[[a-c[0] for a,c in zip(y,ci)],[c[1]-a for a,c in zip(y,ci)]],
           label=s,capsize=1.5,hatch=h,color=["0.25","0.6","0.85"][j],edgecolor="k",linewidth=0.4,error_kw={"lw":0.6})
ax.set_xticks([i+0.27 for i in range(6)]);ax.set_xticklabels(cls);ax.set_ylabel("wrong-target rate");ax.legend(fontsize=7,frameon=False)
fig.tight_layout();fig.savefig("figs/fig_injection.png",dpi=300)
d=["0","0.25","0.5","1","2","none"]
rep=[1,1,1,0.02,0,0]; real=[1,1,1,0.11,0,0]
lo=[0.68,0.68,0.68,0.02,0,0]; hi=[1,1,1,0.44,0.35,0.35]
fig,ax=plt.subplots(figsize=(3.5,2.2)); x=range(6)
ax.plot(x,rep,"-o",c="k",ms=3,label="replay (n=100)")
ax.errorbar([i+0.05 for i in x],real,yerr=[[r-l for r,l in zip(real,lo)],[h-r for r,h in zip(real,hi)]],fmt="s--",c="0.4",ms=3,lw=0.8,capsize=2,label="real (n=10, 95% CI)")
ax.plot(x,[0]*6,":",c="0.6",label="starttime / pidfd (both runs)")
ax.set_xticks(list(x));ax.set_xticklabels(d);ax.set_xlabel(r"recycle delay (multiples of $L$)");ax.set_ylabel("naive misfire rate");ax.legend(fontsize=6.5,frameon=False,loc="center left")
fig.tight_layout();fig.savefig("figs/fig_pidreuse.png",dpi=300)
