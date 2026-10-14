"""Baishouwu NIR calibration using one fixed SPXY partition.

All spectral variables and responses come from the supplied dataset.
Preprocessing and variable-count/component tuning use calibration rows only.
UVE and MC-UVE use explicitly labelled reliability-ranked prefix variants.
"""
import os,sys,json,time,hashlib,warnings,inspect
from pathlib import Path
os.environ['OPENBLAS_NUM_THREADS']='1'; os.environ['OMP_NUM_THREADS']='1'
import numpy as np,pandas as pd,pywt
from scipy.signal import savgol_filter
from scipy.spatial.distance import cdist
from sklearn.model_selection import KFold
from sklearn.cross_decomposition import PLSRegression
from threadpoolctl import threadpool_limits
threadpool_limits(1)
SEED=20261006; MAXLV=10; B=100; METHODS=['Full','UVE','MC-UVE','RT','C-value','BSRS']
PRETS=['Raw','MSC','SNV','CWT','D1','D2']
CWT_KWARGS={'precision':10} if 'precision' in inspect.signature(pywt.cwt).parameters else {}
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'results/analysis'
warnings.filterwarnings('ignore',category=RuntimeWarning)

def pls_path(x,y,a=MAXLV):
 """Mean-centered PLS1 NIPALS, all coefficient paths; no variable scaling."""
 x=np.asarray(x,float); y=np.asarray(y,float); xm=x.mean(0); ym=y.mean()
 e=x-xm; f=y-ym; a=min(a,x.shape[1],len(y)-2)
 W=[]; P=[]; Q=[]; coefs=[]
 for h in range(a):
  w=e.T@f; norm=np.linalg.norm(w)
  if norm<1e-16:break
  w=w/norm; t=e@w; den=t@t
  if den<1e-18:break
  p=e.T@t/den; q=f@t/den
  W.append(w); P.append(p); Q.append(q)
  e=e-np.outer(t,p); f=f-t*q
  ww=np.column_stack(W); pp=np.column_stack(P)
  coefs.append(ww@np.linalg.pinv(pp.T@ww)@np.asarray(Q))
 if not coefs:coefs=[np.zeros(x.shape[1])]
 return np.column_stack(coefs),xm,ym

def predict_path(x,y,z,a=MAXLV):
 c,m,u=pls_path(x,y,a); return (z-m)@c+u

def fold_indices(n,k=5,seed=SEED):return list(KFold(k,shuffle=True,random_state=seed).split(np.arange(n)))

def cv_fixed(x,y,a=MAXLV,k=3,seed=SEED):
 pred=np.empty((len(y),min(a,x.shape[1],len(y)-2)))
 for tr,va in fold_indices(len(y),k,seed):
  q=predict_path(x[tr],y[tr],x[va],pred.shape[1]); pred[va]=q[:,np.minimum(np.arange(pred.shape[1]),q.shape[1]-1)]
 rm=np.sqrt(np.mean((pred-y[:,None])**2,0)); return rm,pred

def pret_pair(x,z,w,method):
 if method=='Raw':return x.copy(),z.copy()
 if method=='SNV':
  def snv(a):return (a-a.mean(1,keepdims=True))/np.maximum(a.std(1,ddof=1,keepdims=True),1e-12)
  return snv(x),snv(z)
 if method=='MSC':
  ref=x.mean(0); rr=ref-ref.mean(); den=rr@rr
  def msc(a):
   b=(a-a.mean(1,keepdims=True))@rr/den; b=np.where(abs(b)<1e-10,1e-10,b)
   aa=a.mean(1)-b*ref.mean(); return (a-aa[:,None])/b[:,None]
  return msc(x),msc(z)
 # Uniform interpolation is fitted to the measured wavelength grid alone.
 grid=np.linspace(w.min(),w.max(),len(w)); win=min(15,len(w)//2*2-1)
 def transform(a):
  u=np.array([np.interp(grid,w,row) for row in a])
  if method in ['D1','D2']:return savgol_filter(u,win,3,deriv=int(method[-1]),delta=float(grid[1]-grid[0]),axis=1,mode='mirror')
  pad=40; v=np.pad(u,((0,0),(pad,pad)),mode='reflect')
  # PyWavelets 1.8 fixes integration precision at 10 internally. Newer APIs
  # expose the option, so pass 10 explicitly to retain the same transform.
  return pywt.cwt(v,[10],'mexh',axis=1,**CWT_KWARGS)[0][0,:,pad:-pad]
 return transform(x),transform(z)

def rank_scores(x,y,method,seed=SEED,base_lv=5):
 rng=np.random.default_rng(seed); n,p=x.shape; a=min(base_lv,p,n-2)
 if method=='Full':return np.arange(p),np.ones(p),{}
 if method in ['BSRS','BSRS-nosign','BSRS-nosmooth','BSRS-noredund','MC-UVE']:
  noise=rng.normal(size=(n,p))*max(float(x.std()),1e-8)*1e-6
  xx=np.hstack([x,noise]) if method=='MC-UVE' else x
  co=[]
  for b in range(B):
   ids=rng.choice(n,max(a+3,int(np.ceil(.8*n))),replace=False)
   co.append(pls_path(xx[ids],y[ids],a)[0][:,-1])
  co=np.array(co); reliability=np.abs(co.mean(0))/np.maximum(co.std(0,ddof=1),1e-14)
  if method=='MC-UVE':
   s=reliability[:p]; threshold=float(np.quantile(reliability[p:],.99)); return np.argsort(-s,kind='stable'),s,{}
  sign=np.abs(np.mean(np.sign(co),axis=0)); s=np.log1p(reliability)
  if method!='BSRS-nosign':s*=sign
  if method!='BSRS-nosmooth':s=np.convolve(np.pad(s,2,mode='reflect'),np.ones(5)/5,mode='valid')
  if method=='BSRS-noredund':return np.argsort(-s,kind='stable'),s,{'sign_consistency':sign.tolist()}
  xc=x-x.mean(0); xc=xc/np.maximum(np.linalg.norm(xc,axis=0),1e-12)
  corr=np.abs(xc.T@xc); remaining=np.ones(p,bool); ranking=[]; redundancy=np.zeros(p)
  for j in range(p):
   merit=s/(1+2*redundancy**2); merit[~remaining]=-np.inf; idx=int(np.argmax(merit)); ranking.append(idx); remaining[idx]=False; redundancy=np.maximum(redundancy,corr[idx])
  return np.array(ranking),s,{'sign_consistency':sign.tolist(),'reliability':reliability.tolist(),'lambda':2,'block_window':5}
 if method=='UVE':
  noise=rng.normal(size=(n,p))*max(float(x.std()),1e-8)*1e-6; xx=np.hstack([x,noise]); co=[]
  for i in range(n):
   ids=np.arange(n)!=i; co.append(pls_path(xx[ids],y[ids],a)[0][:,-1])
  co=np.array(co); rel=np.abs(co.mean(0))/np.maximum(co.std(0,ddof=1),1e-14); s=rel[:p]; threshold=float(np.max(rel[p:])); return np.argsort(-s,kind='stable'),s,{}
 if method=='RT':
  obs=np.abs(pls_path(x,y,a)[0][:,-1]); exceed=np.zeros(p)
  for b in range(199):exceed+=np.abs(pls_path(x,rng.permutation(y),a)[0][:,-1])>=obs
  pv=(exceed+1)/200; s=-pv+obs/(max(obs.max(),1e-14))*1e-8
  return np.argsort(-s,kind='stable'),s,{'p_values':pv.tolist(),'permutations':199}
 if method=='C-value':
  # Exact C=pinv(F)r mechanism, with a documented reduced random design.
  m=2*p; F=np.zeros((m,p),float); errors=[]
  for b in range(m):
   sel=rng.choice(p,max(2,int(round(.7*p))),replace=False); F[b,sel]=1
   rm,_=cv_fixed(x[:,sel],y,min(a,len(sel)),3,seed+91); errors.append(rm.min())
  c=np.linalg.lstsq(F,np.asarray(errors),rcond=None)[0]; s=-c
  return np.argsort(-s,kind='stable'),s,{'design_rows':m,'inclusion_fraction':.7,'C_values':c.tolist()}
 raise ValueError(method)

def metric(y,q):
 e=q-y; sd=float(y.std(ddof=1)); return {'R2':float(1-(e@e)/np.sum((y-y.mean())**2)),'RMSE':float(np.sqrt(np.mean(e*e))),'MAE':float(np.mean(abs(e))),'bias':float(e.mean()),'RPD':sd/float(np.sqrt(np.mean(e*e))),'RPIQ':float(np.subtract(*np.percentile(y,[75,25])))/float(np.sqrt(np.mean(e*e)))}

def spxy_split(x, y, ncal):
 """Normalized joint raw spectral and response distances, followed by maximin selection."""
 dx=cdist(x,x,metric='euclidean'); dy=cdist(y[:,None],y[:,None],metric='euclidean')
 if not 2 <= ncal < len(y):raise ValueError('Invalid calibration subset size.')
 if dx.max()<=0 or dy.max()<=0:raise ValueError('SPXY requires varying spectra and responses.')
 distance=dx/dx.max()+dy/dy.max()
 a,b=np.unravel_index(np.argmax(distance),distance.shape)
 selected=[int(a),int(b)]; nearest=np.minimum(distance[a],distance[b]); nearest[selected]=-np.inf
 while len(selected)<ncal:
  j=int(np.argmax(nearest)); selected.append(j)
  nearest=np.minimum(nearest,distance[j]); nearest[selected]=-np.inf
 cal=np.sort(np.asarray(selected,dtype=int)); test=np.setdiff1d(np.arange(len(y)),cal)
 return cal,test,selected

def budgets(p):return sorted(set([k for k in [4,8,16,32,64,128,int(np.ceil(p*.5))] if k<p]))

def tune_selector(raw,y,w,pret,method,seed,base_lv=5):
 n,p=raw.shape; kk=[p] if method=='Full' else budgets(p)
 preds={k:np.empty((n,min(MAXLV,p,n-2))) for k in kk}; folds=fold_indices(n,5,seed); rankings=[]
 for fi,(tr,va) in enumerate(folds):
  x,z=pret_pair(raw[tr],raw[va],w,pret); rank,score,detail=rank_scores(x,y[tr],method,seed+1009*(fi+1),base_lv); rankings.append(rank)
  for k in kk:
   sel=rank[:k]; q=predict_path(x[:,sel],y[tr],z[:,sel],MAXLV); preds[k][va]=q[:,np.minimum(np.arange(preds[k].shape[1]),q.shape[1]-1)]
 curves=[]
 for k,q in preds.items():
  cap=min(MAXLV,k); rm=np.sqrt(np.mean((q-y[:,None])**2,axis=0))
  for lv in range(1,cap+1):curves.append((float(rm[lv-1]),k,lv))
 best=min(curves,key=lambda v:(v[0],v[1],v[2])); return {'RMSECV':best[0],'budget':best[1],'LV':best[2]},preds[best[1]][:,best[2]-1],curves,rankings

def main(input_path=None):
 from data_io import load_spectra
 t0=time.time(); OUT.mkdir(parents=True,exist_ok=True)
 source=Path(input_path) if input_path else ROOT/'inputs/baishouwu_spectra.mat'
 raw,w,y,input_audit=load_spectra(source,require_y=True)
 n=len(y); cal,test,selection_order=spxy_split(raw,y,int(round(.75*n)))
 np.savez_compressed(OUT/'clean_data.npz',X=raw,w=w,y=y,cal=cal,test=test)
 splitrecords=[]
 for role,ids in [('Calibration',cal),('Prediction',test)]:
  v=y[ids]; splitrecords.append({'set':role,'n':len(v),'min':float(v.min()),'max':float(v.max()),
   'mean':float(v.mean()),'sd':float(v.std(ddof=1)),'q25':float(np.percentile(v,25)),
   'median':float(np.median(v)),'q75':float(np.percentile(v,75))})
 pd.DataFrame(splitrecords).to_csv(OUT/'split_summary.csv',index=False)
 assignment=pd.DataFrame({'MAT_row':np.arange(n)+1,'reference_mg_g':y,
  'set':np.where(np.isin(np.arange(n),cal),'Calibration','Prediction')})
 ids_path=ROOT/'inputs/sample_ids.json'
 if ids_path.exists():
  ids=json.loads(ids_path.read_text(encoding='utf-8'))
  if len(ids)==n:assignment.insert(1,'source_sample_id',ids)
 if 'source_sample_id' not in assignment:
  assignment.insert(1,'source_sample_id',['Row'+str(j+1) for j in range(n)])
 assignment.to_csv(OUT/'sample_assignment.csv',index=False)
 (OUT/'input_data.json').write_text(json.dumps(input_audit,indent=2),encoding='utf-8')
 c,m,u=pls_path(raw[cal],y[cal],5)
 check=PLSRegression(n_components=5,scale=False).fit(raw[cal],y[cal])
 delta=float(np.max(abs((raw[test]-m)@c[:,-1]+u-check.predict(raw[test]).ravel())))
 print('PLS verification maximum difference',delta,flush=True); assert delta<1e-7
 precords=[];records=[];predrecords=[];info={};curves={};ablation=[];models={};pret_cv=[]
 for pret in PRETS:
  cfg,qcv,curve,ranks=tune_selector(raw[cal],y[cal],w,pret,'Full',SEED)
  x,z=pret_pair(raw[cal],raw[test],w,pret)
  qp=predict_path(x,y[cal],z,cfg['LV'])[:,-1];qc=predict_path(x,y[cal],x,cfg['LV'])[:,-1]
  mc=metric(y[cal],qc);mp=metric(y[test],qp)
  precords.append({'pretreatment':pret,'variables':len(w),**cfg,'RMSEC':mc['RMSE'],
   'R2c':mc['R2'],'R2p':mp['R2'],'RMSEP':mp['RMSE'],'RPD':mp['RPD']})
  pret_cv.append((cfg['RMSECV'],pret,cfg['LV']))
 bestcv,pret,base_lv=min(pret_cv)
 print('Selected preprocessing',pret,base_lv,flush=True)
 for method in METHODS:
  start=time.time(); print('Method',method,flush=True)
  cfg,qcv,curve,ranks=tune_selector(raw[cal],y[cal],w,pret,method,SEED,base_lv)
  x,z=pret_pair(raw[cal],raw[test],w,pret)
  rank,score,detail=rank_scores(x,y[cal],method,SEED+777,base_lv);sel=rank[:cfg['budget']]
  qp=predict_path(x[:,sel],y[cal],z[:,sel],cfg['LV'])[:,-1]
  qc=predict_path(x[:,sel],y[cal],x[:,sel],cfg['LV'])[:,-1]
  mc=metric(y[cal],qc);mp=metric(y[test],qp)
  row={'pretreatment':pret,'method':method,'variables':len(sel),'requested_LV':cfg['LV'],
   'LV':min(cfg['LV'],len(sel)),'RMSECV':cfg['RMSECV'],'R2c':mc['R2'],'RMSEC':mc['RMSE'],
   'R2p':mp['R2'],'RMSEP':mp['RMSE'],'MAE':mp['MAE'],'bias':mp['bias'],'RPD':mp['RPD'],
   'RPIQ':mp['RPIQ'],'seconds':time.time()-start}
  records.append(row)
  for role,ids,qs in [('Calibration',cal,qc),('Prediction',test,qp),('CalibrationCV',cal,qcv)]:
   predrecords.extend({'method':method,'pretreatment':pret,'MAT_row':int(idx+1),'set':role,
    'reference':float(y[idx]),'predicted':float(q),'error':float(q-y[idx])} for idx,q in zip(ids,qs))
  grid=np.linspace(w.min(),w.max(),len(w)) if pret in ['CWT','D1','D2'] else w
  finalcfg={**cfg,'requested_LV':cfg['LV'],'LV':min(cfg['LV'],len(sel))}
  coeff,xmean,ymean=pls_path(x[:,sel],y[cal],cfg['LV'])
  models[method]={'coef':coeff[:,-1],'xmean':xmean,'ymean':np.array(ymean),
   'indices':sel,'pretreatment':np.array(pret)}
  info[method]={'config':finalcfg,'selected_indices_zero_based':sel.tolist(),
   'selection_grid_nm':grid.tolist(),'selected_wavelengths_nm':grid[sel].tolist(),
   'working_grid':'uniform interpolated' if pret in ['CWT','D1','D2'] else 'original measured',
   'scores':score.tolist(),'detail':detail};curves[method]=curve
  foldselected=[r[:cfg['budget']] for r in ranks];freq=np.zeros(len(w))
  for r in foldselected:freq[r]+=1/len(ranks)
  info[method]['fold_selection_frequency']=freq.tolist();jacc=[]
  for a in range(5):
   for b in range(a+1,5):jacc.append(len(set(foldselected[a])&set(foldselected[b]))/len(set(foldselected[a])|set(foldselected[b])))
  row['mean_fold_Jaccard']=float(np.mean(jacc))
  print('done',method,'CV',round(cfg['RMSECV'],4),'prediction',round(mp['RMSE'],4),flush=True)
 for variant in ['BSRS-nosign','BSRS-nosmooth','BSRS-noredund']:
  cfg,qcv,curve,ranks=tune_selector(raw[cal],y[cal],w,pret,variant,SEED,base_lv)
  x,z=pret_pair(raw[cal],raw[test],w,pret)
  rank,s,d=rank_scores(x,y[cal],variant,SEED+777,base_lv);sel=rank[:cfg['budget']]
  qp=predict_path(x[:,sel],y[cal],z[:,sel],cfg['LV'])[:,-1]
  ablation.append({'variant':variant,'pretreatment':pret,'variables':len(sel),**cfg,
   'RMSEP':metric(y[test],qp)['RMSE'],'R2p':metric(y[test],qp)['R2']})
 pd.DataFrame(precords).to_csv(OUT/'preprocessing.csv',index=False)
 pd.DataFrame(records).to_csv(OUT/'variable_selection.csv',index=False)
 pd.DataFrame(predrecords).to_csv(OUT/'predictions.csv',index=False)
 pd.DataFrame(ablation).to_csv(OUT/'ablation.csv',index=False)
 (OUT/'selection_details.json').write_text(json.dumps(info,indent=2),encoding='utf-8')
 (OUT/'cv_curves.json').write_text(json.dumps(curves,indent=2),encoding='utf-8')
 selected=[]
 for method,v in info.items():
  for idx,wavelength in zip(v['selected_indices_zero_based'],v['selected_wavelengths_nm']):
   selected.append({'method':method,'working_grid_index_1based':idx+1,
    'wavelength_nm':wavelength,'grid':v['working_grid']})
 pd.DataFrame(selected).to_csv(OUT/'selected_wavelengths.csv',index=False)
 chosen=min(records,key=lambda r:(r['RMSECV'],r['variables'],r['LV']))['method']
 model_data={'raw_calibration':raw[cal],'wavelengths':w,'selected_method':np.array(chosen)}
 for method,model in models.items():
  for field,value in model.items():model_data[method+'__'+field]=value
 np.savez_compressed(OUT/'frozen_models.npz',**model_data)
 summary={'seed':SEED,'n':n,'ncal':len(cal),'npred':len(test),'variables':len(w),'max_LV':MAXLV,
  'folds':5,'stability_subsamples':B,'CWT_integration_precision':10,
  'coefficient_resampling':'80% without replacement','PLS_verification_max_abs_difference':delta,
  'elapsed_seconds':time.time()-t0,'versions':runtime_versions(),'primary_split':'SPXY',
  'distance_definition':'Euclidean distances in all raw spectral variables and in y, each divided by its dataset maximum, then added',
  'spxy_selection_order_rows':(np.array(selection_order)+1).tolist(),
  'chosen_preprocessing':pret,'base_LV':base_lv,'calibration_selected_method':chosen,
  'input_audit':input_audit,'methods':METHODS,'cal_rows':(cal+1).tolist(),'test_rows':(test+1).tolist()}
 signature_payload={'input':input_audit['sha256'],'cal':summary['cal_rows'],'test':summary['test_rows'],
  'pre':pret,'selected':chosen,'seed':SEED,'max_LV':MAXLV,'resamples':B,
  'models':[{field:round(float(r[field]),12) if isinstance(r[field],(float,np.floating)) else r[field]
   for field in ['method','pretreatment','variables','LV','RMSECV','RMSEP','R2p']} for r in records],
  'preprocessing':[{field:round(float(r[field]),12) if isinstance(r[field],(float,np.floating)) else r[field]
   for field in ['pretreatment','LV','RMSECV','RMSEP','R2p']} for r in precords],
  'ablation':[{field:round(float(r[field]),12) if isinstance(r[field],(float,np.floating)) else r[field]
   for field in ['variant','variables','LV','RMSECV','RMSEP','R2p']} for r in ablation]}
 signature=hashlib.sha256(json.dumps(signature_payload,sort_keys=True).encode()).hexdigest()
 summary['analysis_signature']=signature
 (OUT/'run_summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
 print('FINISHED',n,'samples',len(w),'variables',len(cal),'calibration',len(test),'prediction; chosen',chosen,flush=True)

def runtime_versions():
 import platform, scipy, sklearn, matplotlib
 return {'python':platform.python_version(),'numpy':np.__version__,'scipy':scipy.__version__,
  'scikit-learn':sklearn.__version__,'pandas':pd.__version__,'pywavelets_imported':pywt.__version__,
  'matplotlib':matplotlib.__version__}

if __name__=='__main__':
 import argparse
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--input',type=Path,default=ROOT/'inputs/baishouwu_spectra.mat')
 main(parser.parse_args().input)
