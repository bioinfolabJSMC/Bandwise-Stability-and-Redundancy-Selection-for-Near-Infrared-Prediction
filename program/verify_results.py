"""Verify SPXY membership, frozen predictions, reported metrics and figure files."""
from pathlib import Path
import json
import hashlib
import numpy as np
import pandas as pd
from PIL import Image
from sklearn.cross_decomposition import PLSRegression
from analysis import METHODS, PRETS, pret_pair

def main():
    root=Path(__file__).resolve().parent;out=root/'results/analysis';fig=root/'results/figures'
    data=np.load(out/'clean_data.npz');x=data['X'];w=data['w'];y=data['y'];cal=data['cal'];test=data['test']
    assert x.shape==(84,141) and len(w)==141 and np.all(np.diff(w)>0)
    assert len(cal)==63 and len(test)==21 and not np.intersect1d(cal,test).size
    assert len(np.union1d(cal,test))==84
    # Independently construct distances and the greedy partition without calling spxy_split.
    dx=np.linalg.norm(x[:,None,:]-x[None,:,:],axis=2);dy=np.abs(y[:,None]-y[None,:])
    distance=dx/dx.max()+dy/dy.max();a,b=np.unravel_index(np.argmax(distance),distance.shape)
    selected=[int(a),int(b)]
    while len(selected)<63:
        candidates=np.setdiff1d(np.arange(84),selected)
        scores=np.min(distance[np.ix_(candidates,selected)],axis=1)
        selected.append(int(candidates[np.argmax(scores)]))
    assert np.array_equal(np.sort(selected),cal)
    summary=json.loads((out/'run_summary.json').read_text(encoding='utf-8'))
    assert summary['primary_split']=='SPXY' and np.array_equal(np.array(summary['spxy_selection_order_rows'])-1,selected)
    pre=pd.read_csv(out/'preprocessing.csv');table=pd.read_csv(out/'variable_selection.csv')
    assert set(pre.pretreatment)==set(PRETS) and len(pre)==6
    assert set(table.method)==set(METHODS) and len(table)==6 and (table.LV<=table.variables).all()
    assert pre.sort_values(['RMSECV','pretreatment']).iloc[0].pretreatment==summary['chosen_preprocessing']
    chosen=table.sort_values(['RMSECV','variables','LV']).iloc[0].method
    assert chosen==summary['calibration_selected_method']
    models=np.load(out/'frozen_models.npz',allow_pickle=False)
    assert str(models['selected_method'])==chosen
    pred=pd.read_csv(out/'predictions.csv');max_solver_delta=0.
    for method in METHODS:
        prefix=method+'__';pret=str(models[prefix+'pretreatment']);sel=models[prefix+'indices']
        tx,z=pret_pair(models['raw_calibration'],x[test],w,pret)
        nlv=int(table.loc[table.method==method,'LV'].iloc[0])
        independent=PLSRegression(n_components=nlv,scale=False).fit(tx[:,sel],y[cal])
        for role,ids in [('Calibration',cal),('Prediction',test)]:
            g=pred[(pred.method==method)&(pred['set']==role)].sort_values('MAT_row')
            assert np.array_equal(g.MAT_row.to_numpy(),ids+1)
            _,zz=pret_pair(models['raw_calibration'],x[ids],w,pret)
            q=(zz[:,sel]-models[prefix+'xmean'])@models[prefix+'coef']+models[prefix+'ymean']
            assert np.allclose(q,g.predicted.to_numpy(),rtol=0,atol=1e-10)
            max_solver_delta=max(max_solver_delta,float(np.max(np.abs(independent.predict(zz[:,sel]).ravel()-q))))
            metric_name='RMSEC' if role=='Calibration' else 'RMSEP'
            assert abs(np.sqrt(np.mean((q-y[ids])**2))-table.loc[table.method==method,metric_name].iloc[0])<1e-10
        cv=pred[(pred.method==method)&(pred['set']=='CalibrationCV')]
        assert set(cv.MAT_row)==set(cal+1)
        assert abs(np.sqrt(np.mean(cv.error.to_numpy()**2))-table.loc[table.method==method,'RMSECV'].iloc[0])<1e-10
    assert max_solver_delta<1e-7
    figure_records=[]
    for stem in [*[f'Figure_{j}' for j in range(1,8)],*[f'Figure_S{j}' for j in range(1,5)]]:
        with Image.open(fig/(stem+'.png')) as im,Image.open(fig/(stem+'.tiff')) as ti:
            assert im.size==ti.size and all(abs(float(v)-300)<.1 for v in im.info['dpi'])
            assert all(abs(float(v)-300)<.1 for v in ti.info['dpi'])
            figure_records.append({'figure':stem,'pixels':list(im.size),'dpi':300,
                'png_sha256':hashlib.sha256((fig/(stem+'.png')).read_bytes()).hexdigest()})
    report={'status':'PASS','samples':84,'calibration':63,'prediction':21,'variables':141,
            'SPXY_independently_reproduced':True,'frozen_predictions_match':True,
            'PLS_independent_solver_max_difference':max_solver_delta,'calibration_selected_method':chosen,
            'methods':METHODS,'figures':figure_records}
    (out/'verification_report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('PASS: SPXY, calibration selection, frozen predictions, metrics and 11 publication figures.')

if __name__=='__main__':main()
