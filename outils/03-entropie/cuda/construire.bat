@echo off
rem Construit rans_v4.exe (second chemin du decodeur) et dispersion.exe (reassemblage des
rem flux de classe), CUDA, sm_89, hors du depot.
rem CUDA 13.1.2 depaquete sans installation (SOCLE, section La machine).
rem Commentaires sans accents : cmd lit ce fichier dans la page de code OEM.
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul
set CUDA_PATH=~\dev\outils\cuda-13.1.2
set PATH=%CUDA_PATH%\bin;%PATH%
if not exist ~\dev\essais\troncons\entropie\cuda mkdir ~\dev\essais\troncons\entropie\cuda
nvcc -O3 -arch=sm_89 -o ~\dev\essais\troncons\entropie\cuda\rans_v4.exe "%~dp0rans_v4.cu"
nvcc -O3 -arch=sm_89 -o ~\dev\essais\troncons\entropie\cuda\dispersion.exe "%~dp0dispersion.cu"
