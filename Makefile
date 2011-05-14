# $Id: Makefile 54 2004-09-05 02:14:00Z connolly $

MKDIR=mkdir
GREP=grep

XSLTPROC=xsltproc
PYTHON=python
TWISTD=twistd
EPYDOC=epydoc
NEVOW=/home/connolly/src/Nevow

run: testchiro-db
	PYTHONPATH=$(NEVOW) $(TWISTD) -noy bottleapp.tac

testchiro-db: loadTables.py bottlesDB.sql testclinic.html
	$(PYTHON) loadTables.py testchiro-db bottlesDB.sql testclinic.html


bottlesDB.sql: bottlesDB.owl owl2sql.xsl
	$(XSLTPROC) --novalid -o $@ owl2sql.xsl bottlesDB.owl

bottlesDB.owl: bottlesDB.html grokDBSchema.xsl
	$(XSLTPROC) --novalid -o $@ grokDBSchema.xsl bottlesDB.html

MODULES=bottlesmarts.py loadTables.py
#@@hmm... what about bottleapp.tac ?

epydoc: $(MODULES)
	$(MKDIR) -p srcdoc
	PYTHONPATH=$(NEVOW) $(EPYDOC) --output srcdoc $(MODULES)

lookie:
	$(GREP) @@ *.py *.html *.tac

clean:
	$(RM) *.pyc testchiro-db bottlesDB.owl bottlesDB.sql *~

