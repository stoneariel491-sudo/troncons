@echo off
rem Epreuve J1, constat m2 : la recette du SOCLE (vcvars d'abord) sur la seule crate trc-noyaux.
set CUDA_PATH=~\dev\outils\cuda-13.1.2
set CARGO_TARGET_DIR=~\dev\cibles\troncons-epreuve-vcvars
set CARGO_INCREMENTAL=1
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul
set PATH=%CUDA_PATH%\bin;%PATH%
cargo build --release --offline -j 4 --manifest-path ~\dev\essais\troncons\epreuve-J1\clone\moteur\Cargo.toml -p trc-noyaux
exit /b %errorlevel%
