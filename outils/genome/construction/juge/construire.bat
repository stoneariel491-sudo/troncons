@echo off
rem Juge de la construction : construit depuis main (arbre du depot) le moteur, juge et genome-capture
rem dans la cible du juge, par la recette du SOCLE (vcvars64.bat, CUDA_PATH, nvcc en tete du PATH).
rem Usage : construire.bat  (journal : sortie standard)
set CUDA_PATH=~\dev\outils\cuda-13.1.2
set CARGO_TARGET_DIR=~\dev\cibles\troncons-juge
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul
set PATH=%CUDA_PATH%\bin;%PATH%
where cl.exe
where nvcc.exe
cargo build --release --offline -j 4 --manifest-path ~\dev\active\troncons\moteur\Cargo.toml --bins
if errorlevel 1 exit /b %errorlevel%
cargo build --release --offline -j 4 --manifest-path ~\dev\active\troncons\outils\genome\eclaireur\capture\Cargo.toml
exit /b %errorlevel%
