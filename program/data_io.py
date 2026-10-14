"""Read the Baishouwu spectra and preserve paired sample and variable values."""
from pathlib import Path
import hashlib
import numpy as np
from scipy.io import loadmat

def load_spectra(path, require_y=True):
    path=Path(path)
    if not path.is_file():raise FileNotFoundError(path)
    data=loadmat(path)
    if any(k not in data for k in ['X','wv']):raise ValueError('MAT file must contain X and wv.')
    x=np.asarray(data['X'],dtype=float);w=np.asarray(data['wv'],dtype=float).ravel()
    if x.ndim!=2:raise ValueError('X must be a two-dimensional spectral matrix.')
    if x.shape[1]!=len(w):
        if x.shape[0]==len(w):x=x.T
        else:raise ValueError('X dimensions do not match wv.')
    if not np.all(np.isfinite(x)) or not np.all(np.isfinite(w)) or np.any(w<=0):
        raise ValueError('Spectra must be finite and wavelengths must be positive.')
    order=np.argsort(w,kind='stable');x=x[:,order];w=w[order]
    if len(w)!=141 or np.any(np.diff(w)<=0):raise ValueError('This protocol requires 141 distinct spectral variables.')
    y=None
    if require_y:
        if 'y' not in data:raise ValueError('Calibration input must contain y.')
        y=np.asarray(data['y'],dtype=float).ravel()
        if len(y)!=len(x) or not np.all(np.isfinite(y)):raise ValueError('y must be finite and match the sample rows.')
        if len(y)!=84:raise ValueError('This study protocol requires 84 samples.')
        if np.ptp(y)<=0:raise ValueError('Reference values must vary.')
    audit={'samples':len(x),'variables':len(w),'range_nm':[float(w.min()),float(w.max())],
           'ascending_reordered':bool(np.any(order!=np.arange(len(w)))),
           'duplicate_complete_spectra':int(len(x)-len(np.unique(x,axis=0))),
           'file':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    return x,w,y,audit
