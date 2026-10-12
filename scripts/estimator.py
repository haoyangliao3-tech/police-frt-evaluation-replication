"""Approved exploratory extension; preserves all previous analysis outputs."""
from pathlib import Path
import sys, json, itertools
from config import ROOT
import numpy as np
import pyreadstat
from scipy.optimize import minimize
from scipy.special import softmax, logsumexp, expit, logit
from scipy.stats import chi2, norm
roles=[f'FACEREC6_{a}_W99' for a in 'abcd']; public,police=roles[2:]
controls=['F_AGECAT','F_GENDER','F_EDUCCAT','F_RACETHNMOD','F_PARTYSUM_FINAL','F_INC_TIER2','F_METRO','FACEREC1_W99']
y='FACEREC2_W99'; safeguards=[f'FACEREC8_{a}_W99' for a in 'abc']
def holm(items):
    prev=0
    for rank,i in enumerate(sorted(range(len(items)),key=lambda i:items[i]['p'])):
        prev=max(prev,min(1,(len(items)-rank)*items[i]['p']));items[i]['p_Holm']=prev
def interval(mu,se):
    if 0<mu<1:
        lo,hi=expit(logit(mu)+np.array([-1,1])*1.96*se/(mu*(1-mu)))
    else: return [None,None]  # An empty/full cell does not justify a zero-width CI.
    return [float(lo),float(hi)]
def fit(z,outcome,vs,interaction=True,order=None):
    order=order or ([1,3,2] if outcome==y else [1,2,3])
    z=z.dropna(subset=[outcome]+vs).copy()
    specs=[(v,c) for v in vs for c in sorted(z[v].unique()) if c!=(2 if v in roles else min(z[v].unique()))]
    pairs=list(itertools.product([1,3],repeat=2)) if interaction else []
    def design(frame):
        return np.column_stack([np.ones(len(frame))]+[frame[v].eq(c).to_numpy(float) for v,c in specs]+[(frame[public].eq(a)&frame[police].eq(b)).to_numpy(float) for a,b in pairs])
    X=design(z);n,p=X.shape;w=z.WEIGHT_W99.to_numpy();w=w/w.mean()
    Y=np.column_stack([z[outcome].eq(c) for c in order[:2]]).astype(float)
    def probs(b,x=X):return softmax(np.column_stack([x@b.reshape(2,p).T,np.zeros(len(x))]),axis=1)
    def obj(b):
        eta=X@b.reshape(2,p).T
        return float(np.sum(w*(logsumexp(np.column_stack([eta,np.zeros(n)]),axis=1)-(Y*eta).sum(1))))
    def grad(b):return ((w[:,None]*(probs(b)[:,:2]-Y)).T@X).ravel()
    def hess(b):
        pr=probs(b)
        return np.block([[X.T@((w*pr[:,j]*((j==k)-pr[:,k]))[:,None]*X) for k in range(2)] for j in range(2)])
    res=minimize(obj,np.zeros(2*p),jac=grad,hess=hess,method='trust-exact',options={'gtol':1e-7,'maxiter':300});b=res.x
    for _ in range(8):
        if abs(grad(b)).max()<1e-7:break
        candidate=b-np.linalg.solve(hess(b),grad(b))
        if obj(candidate)>obj(b)+1e-8:break
        b=candidate
    H=hess(b);Hi=np.linalg.inv(H)
    score=(w[:,None,None]*(Y-probs(b)[:,:2])[:,:,None]*X[:,None,:]).reshape(n,-1)
    V=Hi@(score.T@score)@Hi;V=(V+V.T)/2
    influence=score@Hi
    diag={'optimizer_message':str(res.message),'gradient_max':float(abs(grad(b)).max()),'hessian_min_eigenvalue':float(np.linalg.eigvalsh(H).min()),'hessian_condition':float(np.linalg.cond(H)),'design_rank':int(np.linalg.matrix_rank(X)),'design_columns':p,'max_abs_coefficient':float(abs(b).max()),'largest_approx_case_deletion_coefficient_change':float(abs(influence).max())}
    assert diag['gradient_max']<1e-6 and diag['hessian_min_eigenvalue']>0 and diag['design_rank']==p
    # Independent optimizer/prediction check, not independent software validation.
    alt=minimize(obj,np.zeros(2*p),jac=grad,method='BFGS',options={'gtol':1e-6,'maxiter':1000})
    diag['BFGS_success']=bool(alt.success);diag['BFGS_max_prediction_difference']=float(abs(probs(b)-probs(alt.x)).max())
    assert diag['BFGS_max_prediction_difference']<1e-4
    # Finite-difference directional derivative checks of the analytic Hessian.
    rng=np.random.default_rng(20260922);v=rng.normal(size=2*p);v/=np.linalg.norm(v);eps=1e-5
    diag['hessian_directional_max_error']=float(abs((grad(b+eps*v)-grad(b-eps*v))/(2*eps)-H@v).max())
    result={'n':n,'order':order,'interaction':interaction,'diagnostics':diag,'coefficient_names':['Intercept']+[f'{v}={c}' for v,c in specs]+[f'Public={a}:Police={b}' for a,b in pairs],'coefficients':b.tolist(),'covariance':V.tolist(),'weighted_negative_loglikelihood':obj(b),'configurations':[],'public_major_minus_minor':[],'probability_difference_in_differences':[]}
    if interaction:
        ids=list(range(p-4,p))+list(range(2*p-4,2*p));stat=float(b[ids]@np.linalg.solve(V[np.ix_(ids,ids)],b[ids]))
        result['interaction_test']={'Wald':stat,'df':8,'p':float(chi2.sf(stat,8))}
    cache={};max_probability_influence=0;influence_index=None
    for a,c in itertools.product([1,2,3],repeat=2):
        zz=z.copy();zz[public]=a;zz[police]=c;xx=design(zz);pr=probs(b,xx);mu=np.average(pr,weights=w,axis=0);G=np.zeros((3,2*p))
        for j in range(3):
            for k in range(2):G[j,k*p:(k+1)*p]=np.average((pr[:,j]*((j==k)-pr[:,k]))[:,None]*xx,weights=w,axis=0)
        se=np.sqrt(np.maximum(np.diag(G@V@G.T),0));cache[a,c]=(mu,G)
        case_probability_change=influence@G.T
        loc=np.unravel_index(np.argmax(abs(case_probability_change)),case_probability_change.shape)
        if abs(case_probability_change[loc])>max_probability_influence:
            max_probability_influence=float(abs(case_probability_change[loc]));influence_index=int(z.index[loc[0]])
        fd=(np.average(probs(b+eps*v,xx),weights=w,axis=0)-np.average(probs(b-eps*v,xx),weights=w,axis=0))/(2*eps)
        assert np.max(abs(fd-G@v))<1e-6
        assert abs(mu.sum()-1)<1e-10
        observed=z.loc[z[public].eq(a)&z[police].eq(c)]
        unsupported=[]
        for var in vs:
            if var in [public,police]:continue
            absent=set(z[var].unique())-set(observed[var].unique())
            if absent:unsupported.append({'variable':var,'absent_levels':sorted(absent)})
        result['configurations'].append({'public':a,'police':c,'observed_n':len(observed),'probabilities':mu.tolist(),'se':se.tolist(),'ci95':[interval(m,s) for m,s in zip(mu,se)],'absent_covariate_levels':unsupported})
    delta_cache={}
    for c in [1,2,3]:
        mu=cache[1,c][0]-cache[2,c][0];G=cache[1,c][1]-cache[2,c][1];se=np.sqrt(np.maximum(np.diag(G@V@G.T),0));delta_cache[c]=(mu,G)
        result['public_major_minus_minor'].append({'police':c,'difference':mu.tolist(),'ci95':np.column_stack([mu-1.96*se,mu+1.96*se]).tolist()})
    for c in [1,3]:
        mu=delta_cache[c][0]-delta_cache[2][0];G=delta_cache[c][1]-delta_cache[2][1];se=np.sqrt(np.maximum(np.diag(G@V@G.T),0))
        for j in range(3):result['probability_difference_in_differences'].append({'police_level':c,'police_reference':2,'outcome_code':order[j],'difference':float(mu[j]),'ci95':[float(mu[j]-1.96*se[j]),float(mu[j]+1.96*se[j])],'p':float(2*norm.sf(abs(mu[j]/se[j])))})
    result['diagnostics']['largest_approx_case_probability_change']=max_probability_influence
    result['diagnostics']['influence_row_index']=influence_index
    return result

def proportion(z,indicator):
    w=z.WEIGHT_W99.to_numpy();a=np.asarray(indicator,float);mu=float(np.average(a,weights=w));se=float(np.sqrt(np.sum(w*w*(a-mu)**2))/w.sum())
    return {'n':len(z),'numerator_n':int(a.sum()),'proportion':mu,'se':se,'ci95':interval(mu,se)}

