@echo off
rem Ronde de corrections J1, constat m2 : la recette du SOCLE (vcvars64.bat d abord) sur trc-noyaux,
rem arbre de travail du depot, cible a part. Usage : construire-avec-vcvars.bat [sans]
set CUDA_PATH=~\dev\outils\cuda-13.1.2
set CARGO_INCREMENTAL=1
if "%1"=="sans" goto sans
set CARGO_TARGET_DIR=~\dev\cibles\troncons-O-vcvars
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul
goto suite
:sans
set CARGO_TARGET_DIR=~\dev\cibles\troncons-O-sans-vcvars
:suite
set PATH=%CUDA_PATH%\bin;%PATH%
where cl.exe
cargo build --release --offline -j 4 --manifest-path ~\dev\active\troncons\moteur\Cargo.toml -p trc-noyaux
exit /b %errorlevel%
