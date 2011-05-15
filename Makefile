# Convert database schema from HTML to SQL via OWL

MKDIR=mkdir

XSLTPROC=xsltproc
PYTHON=python

DB=/tmp/dz.db
BAK=Dabble-2011-05-11-024407/
U=dconnolly@hopeharborkc.com

clients.xls: $(DB)
	$(PYTHON) migrate_hh.py --make-clients-spreadsheet $(DB) $@

$(DB): $(BAK)/Visit.csv hh_data.sql
	$(PYTHON) migrate_hh.py --prepare-db $(DB) $(BAK)
	$(PYTHON) migrate_hh.py --load-basics $(DB) $(U) $(BAK)


hh_data.sql: hh_data.owl owl2sql.xsl
	$(XSLTPROC) --novalid -o $@ owl2sql.xsl hh_data.owl

hh_data.owl: hh_data.html grokDBSchema.xsl
	$(XSLTPROC) --novalid -o $@ grokDBSchema.xsl hh_data.html

clean:
	$(RM) *~ *.pyc testchiro-db hh_data.owl hh_data.sql $(DB)

