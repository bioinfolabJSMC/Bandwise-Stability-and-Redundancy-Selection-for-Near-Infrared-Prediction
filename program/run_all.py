"""Run the SPXY analysis, publication figures, result checks and Word generation."""
from pathlib import Path
import argparse
import subprocess
import sys
import time

def main():
    root=Path(__file__).resolve().parent
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,default=root/'inputs/baishouwu_spectra.mat')
    args=parser.parse_args();start=time.time()
    subprocess.run([sys.executable,str(root/'analysis.py'),'--input',str(args.input.resolve())],check=True,cwd=root)
    for name in ['plot_figures.py','verify_results.py','export_references.py','build_manuscript.py']:
        subprocess.run([sys.executable,str(root/name)],check=True,cwd=root)
    print(f'Completed in {time.time()-start:.1f} s. Results: {root / "results"}')

if __name__=='__main__':main()
