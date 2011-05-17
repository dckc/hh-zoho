# Convert database schema from HTML to SQL via OWL

MKDIR=mkdir

XSLTPROC=xsltproc
PYTHON=python

DB=/tmp/dz.db
BAK=../hh-dabble-kaput/Dabble-2011-05-16-130809
U=dconnolly@hopeharborkc.com

all: sessions.xls clients.xls

save-idmaps:
	$(PYTHON) migrate_hh.py --save-idmap $(DB) client
	$(PYTHON) migrate_hh.py --save-idmap $(DB) session

visits.xls: $(DB)
	$(PYTHON) migrate_hh.py --make-visits-spreadsheet $(DB) $@

sessions.xls: $(DB)
	$(PYTHON) migrate_hh.py --make-sessions-spreadsheet $(DB) $@

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

