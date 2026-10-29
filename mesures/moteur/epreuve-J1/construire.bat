@echo off
rem Epreuve J1 : construit troncons depuis un clone propre, cible propre au juge, -j 4.
set CUDA_PATH=~\dev\outils\cuda-13.1.2
set CARGO_TARGET_DIR=~\dev\cibles\troncons-epreuve
set CARGO_INCREMENTAL=1
rem Sans vcvars : le build.rs de trc-noyaux echoue quand cl.exe est deja dans le PATH
rem (constat de l epreuve, recette du lot E) ; il appelle vcvars lui-meme.
set PATH=%CUDA_PATH%\bin;%PATH%
cargo build --release --offline -j 4 --manifest-path ~\dev\essais\troncons\epreuve-J1\clone\moteur\Cargo.toml -p troncons -p trc-juge
exit /b %errorlevel%
