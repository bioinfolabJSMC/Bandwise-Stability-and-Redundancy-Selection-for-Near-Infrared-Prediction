"""Apply a frozen calibration model to new spectra on the same measured grid."""
from pathlib import Path
import argparse
import numpy as np
import pandas as pd
from analysis import pret_pair, METHODS
from data_io import load_spectra

def main():
    root=Path(__file__).resolve().parent
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,required=True,help='MAT file with X and wv; y is ignored.')
    parser.add_argument('--model',choices=METHODS,default=None,help='Default: the method selected by calibration RMSECV.')
    parser.add_argument('--models',type=Path,default=root/'results/analysis/frozen_models.npz')
    parser.add_argument('--output',type=Path,default=root/'results/new_predictions.csv')
    args=parser.parse_args()
    x,w,_,audit=load_spectra(args.input,require_y=False)
    models=np.load(args.models,allow_pickle=False)
    if w.shape!=models['wavelengths'].shape or not np.allclose(w,models['wavelengths'],rtol=0,atol=1e-6):
        raise ValueError('The measured wavelength grid differs from the frozen calibration model.')
    method=args.model or str(models['selected_method'])
    prefix=method+'__';pret=str(models[prefix+'pretreatment'])
    _,z=pret_pair(models['raw_calibration'],x,w,pret)
    q=(z[:,models[prefix+'indices']]-models[prefix+'xmean'])@models[prefix+'coef']+models[prefix+'ymean']
    args.output.parent.mkdir(parents=True,exist_ok=True)
    pd.DataFrame({'row':np.arange(len(q))+1,'model':method,'predicted_mg_g':q}).to_csv(args.output,index=False)
    print(f'{len(q)} {method} predictions written to {args.output}')

if __name__=='__main__':main()
