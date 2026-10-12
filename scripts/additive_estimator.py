from pathlib import Path
import sys,json,zipfile,xml.etree.ElementTree as ET
from config import ROOT as root, load
import numpy as np
import pandas as pd
import pyreadstat
from scipy.optimize import minimize,check_grad
from scipy.special import softmax,logsumexp
from scipy.stats import chi2
d,_=load()
roles=[f'FACEREC6_{a}_W99' for a in 'abcd']
controls=['F_AGECAT','F_GENDER','F_EDUCCAT','F_RACETHNMOD','F_PARTYSUM_FINAL','F_INC_TIER2','F_METRO','FACEREC1_W99']
y='FACEREC2_W99'
def fit(z,vs,weighted=True):
    z=z.dropna(subset=[y]+vs)
    specs=[(v,c) for v in vs for c in sorted(z[v].unique()) if c!=(2 if v in roles else min(z[v].unique()))]
    def design(frame):
        return np.column_stack([np.ones(len(frame))]+[(frame[v].to_numpy()==c).astype(float) for v,c in specs])
    X=design(z); n,p=X.shape
    w=z.WEIGHT_W99.to_numpy() if weighted else np.ones(n)
    w=w/w.mean(); Y=np.column_stack([z[y].eq(1),z[y].eq(3)]).astype(float)
    def probs(b,x=X): return softmax(np.column_stack([x@b.reshape(2,p).T,np.zeros(len(x))]),axis=1)
    def obj(b):
        eta=X@b.reshape(2,p).T
        return np.sum(w*(logsumexp(np.column_stack([eta,np.zeros(n)]),axis=1)-(Y*eta).sum(1)))
    def grad(b): return ((w[:,None]*(probs(b)[:,:2]-Y)).T@X).ravel()
    def hess(b):
        pr=probs(b)
        return np.block([[X.T@((w*pr[:,j]*((j==k)-pr[:,k]))[:,None]*X) for k in range(2)] for j in range(2)])
    res=minimize(obj,np.zeros(2*p),jac=grad,hess=hess,method='trust-exact',options={'gtol':1e-7,'maxiter':200})
    b=res.x
    initial_message=str(res.message)
    # Full Newton polishing for near-optimum trust-region roundoff stalls.
    for _ in range(5):
        if abs(grad(b)).max()<1e-7: break
        step=np.linalg.solve(hess(b),grad(b)); candidate=b-step
        if obj(candidate)>obj(b)+1e-8: break
        b=candidate
    if abs(grad(b)).max()<1e-7 and np.linalg.eigvalsh(hess(b)).min()>0:
        res.success=True
        res.message=initial_message+'; verified gradient <1e-7 and positive Hessian after Newton check'
    H=hess(b); Hi=np.linalg.inv(H)
    score=(w[:,None,None]*(Y-probs(b)[:,:2])[:,:,None]*X[:,None,:]).reshape(n,-1)
    V=Hi@(score.T@score)@Hi
    tests=[]; contrasts=[]
    for v in roles:
        ix=[i+1 for i,s in enumerate(specs) if s[0]==v]; ids=ix+[p+i for i in ix]
        W=float(b[ids]@np.linalg.solve(V[np.ix_(ids,ids)],b[ids]))
        tests.append({'variable':v,'Wald':W,'df':len(ids),'p':float(chi2.sf(W,len(ids)))})
        def standard(c):
            zz=z.copy();zz[v]=c; xx=design(zz); pr=probs(b,xx)
            mean=np.average(pr,weights=w,axis=0)
            G=np.zeros((3,2*p))
            for j in range(3):
                for k in range(2): G[j,k*p:(k+1)*p]=np.average((pr[:,j]*((j==k)-pr[:,k]))[:,None]*xx,weights=w,axis=0)
            return mean,G
        base,gb=standard(2)
        for c in [1,3]:
            mu,g=standard(c); delta=mu-base; G=g-gb
            se=np.sqrt(np.maximum(np.diag(G@V@G.T),0))
            contrasts.append({'variable':v,'level':c,'vs':2,'order':['good','unsure','bad'],'delta':delta.tolist(),'low':(delta-1.96*se).tolist(),'high':(delta+1.96*se).tolist()})
    order=np.argsort([t['p'] for t in tests]);prev=0
    for rank,i in enumerate(order):
        prev=max(prev,min(1,(4-rank)*tests[i]['p']));tests[i]['p_Holm']=prev
    return {'n':n,'weighted':weighted,'optimizer_success':bool(res.success),'message':str(res.message),'gradient_max':float(abs(grad(b)).max()),'hessian_min_eigenvalue':float(np.linalg.eigvalsh(H).min()),'gradient_check_at_zero':float(check_grad(obj,grad,np.zeros(2*p))),'tests':tests,'contrasts':contrasts,'coefficient_names':['Intercept']+[f'{v}={c}' for v,c in specs],'coefficients':b.tolist(),'covariance':V.tolist()}
