@echo off
rem Construit le banc du lot K (banc_k.exe) et l'image des noyaux seule, hors du depot.
rem CUDA 13.1.2 depaquete sans installation (SOCLE, section La machine).
rem Memes options de compilation des noyaux que build.rs : -O3, sm_89, sans fast-math.
rem Commentaires sans accents : cmd lit ce fichier dans la page de code OEM.
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul
set CUDA_PATH=~\dev\outils\cuda-13.1.2
set PATH=%CUDA_PATH%\bin;%PATH%
set SORTIE=~\dev\cibles\troncons-K\banc
if not exist %SORTIE% mkdir %SORTIE%
nvcc -O3 -std=c++17 -gencode arch=compute_89,code=[sm_89,compute_89] -Xptxas -v --fatbin -o %SORTIE%\noyaux.fatbin "%~dp0..\noyaux\noyaux.cu" || exit /b 1
nvcc -O3 -std=c++17 -gencode arch=compute_89,code=[sm_89,compute_89] -Xcompiler "/O2 /openmp /utf-8" -o %SORTIE%\banc_k.exe "%~dp0banc_k.cu" || exit /b 1
