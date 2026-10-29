@echo off
rem Construit traceur.exe contre les DLL officielles de llama.cpp b11515 (binaires CUDA 12.4).
rem   - en-têtes : sources officielles du même commit (3d65c90d0, licence MIT), dossier SRC ;
rem   - bibliothèques d'importation : tirées des exports des DLL (dumpbin /exports -> .def -> lib),
rem     parce que le paquet binaire ne livre pas de .lib ;
rem   - sortie : dossier OUT (hors dépôt).
rem Usage : construire.bat  (variables SRC, DLL, OUT modifiables ci-dessous)
setlocal enabledelayedexpansion
set SRC=~\dev\lectures\troncons\gpt-oss\llama.cpp-b11515
set DLL=~\dev\modeles\llama.cpp-b11515
set OUT=~\dev\essais\troncons\gpt-oss\construction
set ICI=%~dp0
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul || exit /b 1
if not exist "%OUT%" mkdir "%OUT%"
cd /d "%OUT%"
for %%N in (llama ggml ggml-base) do (
  dumpbin /nologo /exports "%DLL%\%%N.dll" > %%N.exports.txt || exit /b 1
  python -I "%ICI%faire_def.py" %%N.exports.txt %%N.dll %%N.def || exit /b 1
  lib /nologo /def:%%N.def /machine:x64 /out:%%N.lib || exit /b 1
)
cl /nologo /std:c++17 /O2 /EHsc /utf-8 /W3 ^
  /I"%SRC%\include" /I"%SRC%\ggml\include" ^
  "%ICI%traceur.cpp" /Fe:traceur.exe /link llama.lib ggml.lib ggml-base.lib || exit /b 1
echo construit : %OUT%\traceur.exe
