@echo off
rem Construit banc-chemin (lot E) en release, cible propre au lot, -j 4 (cinq lots compilent en
rem meme temps). Argument 1 (facultatif) :
rem   (rien)   : l'espace de travail commun (moteur\Cargo.toml), dans vcvars64 ;
rem   "miroir" : l'espace prive du lot E (hors depot), quand l'espace commun est casse ;
rem   "e2"     : l'espace mesures\moteur\E\miroir (banc E2), sur un instantane du depot au commit
rem              courant (git archive HEAD moteur) pour les crates des autres lots, jamais sur leur
rem              arbre de travail en cours d'edition ; ne touche pas moteur\Cargo.lock (lot O).
rem              Sans vcvars : le build.rs de trc-noyaux (lot K) echoue quand cl.exe est deja dans
rem              le PATH (guillemets de Command::arg passes a cmd) ; les deux build.rs appellent
rem              vcvars eux-memes quand cl.exe est absent.
rem Commentaires sans accents : cmd lit ce fichier dans la page de code OEM.
set CUDA_PATH=~\dev\outils\cuda-13.1.2
set CARGO_TARGET_DIR=~\dev\cibles\troncons-E
set CARGO_INCREMENTAL=1
set INSTANTANE=~\dev\cibles\troncons-E\instantane
if "%1"=="e2" goto e2
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul
set PATH=%CUDA_PATH%\bin;%PATH%
if "%1"=="miroir" (
  cargo build --release --offline -j 4 --manifest-path ~\dev\cibles\troncons-E\miroir\banc\Cargo.toml
) else (
  cargo build --release --offline -j 4 --manifest-path %~dp0..\..\..\moteur\Cargo.toml -p banc-chemin
)
exit /b %errorlevel%
:e2
if exist %INSTANTANE% rmdir /s /q %INSTANTANE%
mkdir %INSTANTANE%
git -C %~dp0..\..\.. archive --format=tar HEAD moteur | tar -x -C %INSTANTANE%
git -C %~dp0..\..\.. rev-parse HEAD > %INSTANTANE%\COMMIT.txt
cargo build --release --offline -j 4 --manifest-path %~dp0miroir\Cargo.toml
exit /b %errorlevel%
