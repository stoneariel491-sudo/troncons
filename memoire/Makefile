# Construction des mémoires de troncons, Tome I et Tome II (pour qui a make ; sinon ./construire.sh,
# qui vérifie en plus les journaux : références, citations, figures, doublons de biber).
.PHONY: tout en fr donnees tome2 tome2-en tome2-fr donnees-tome2 propre
tout: donnees en fr tome2
donnees:
	python -I -X utf8 outils/donnees_figures.py
	python -I -X utf8 outils/calculs_entropie.py
	python -I -X utf8 outils/annexes.py
en: donnees
	cd en && latexmk -r ../latexmkrc troncons-memoire-en.tex
fr: donnees
	cd fr && latexmk -r ../latexmkrc troncons-memoire-fr.tex
donnees-tome2:
	python -I -X utf8 outils/tome2_format.py
	python -I -X utf8 outils/tome2_chemin_noyaux.py
	python -I -X utf8 outils/tome2_reference_cache.py
	python -I -X utf8 outils/tome2_resultats.py
	python -I -X utf8 outils/tome2_annexes.py
tome2: tome2-en tome2-fr
tome2-en: donnees-tome2
	cd tome2/en && latexmk -r ../../latexmkrc troncons-tome2-en.tex
tome2-fr: donnees-tome2
	cd tome2/fr && latexmk -r ../../latexmkrc troncons-tome2-fr.tex
propre:
	cd en && latexmk -r ../latexmkrc -C troncons-memoire-en.tex
	cd fr && latexmk -r ../latexmkrc -C troncons-memoire-fr.tex
	cd tome2/en && latexmk -r ../../latexmkrc -C troncons-tome2-en.tex
	cd tome2/fr && latexmk -r ../../latexmkrc -C troncons-tome2-fr.tex
