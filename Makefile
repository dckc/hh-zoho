# Convert database schema from HTML to SQL via OWL
#
# 1. make
#    to load unlinked data
# 2. log in and run fixup.link_officers etc.
#

MKDIR=mkdir

XSLTPROC=xsltproc
PYTHON=python

DB=/tmp/dz.db
BAK=../hh-dabble-kaput/Dabble-2011-05-16-130809
U=dconnolly@hopeharborkc.com

start: load-basics load-visits

load-idmaps: ,client_idmap.csv ,session_idmap.csv
	$(PYTHON) migrate_hh.py --load-idmap $(DB) session ,session_idmap.csv
	$(PYTHON) migrate_hh.py --load-idmap $(DB) client ,client_idmap.csv

visits.xls: $(DB)
	$(PYTHON) migrate_hh.py --make-visits-spreadsheet $(DB) $@

sessions.xls: $(DB)
	$(PYTHON) migrate_hh.py --make-sessions-spreadsheet $(DB) $@

clients.xls: $(DB)
	$(PYTHON) migrate_hh.py --make-clients-spreadsheet $(DB) $@

load-visits: $(DB) zoho-api-key
	$(PYTHON) migrate_hh.py --load-visits $(DB) $(U)

load-basics: $(DB) zoho-api-key
	$(PYTHON) migrate_hh.py --load-basics $(DB) $(U)

$(DB): $(BAK)/Visit.csv hh_data.sql
	$(PYTHON) migrate_hh.py --prepare-db $(DB) $(BAK)


hh_data.sql: hh_data.owl owl2sql.xsl
	$(XSLTPROC) --novalid -o $@ owl2sql.xsl hh_data.owl

hh_data.owl: hh_data.html grokDBSchema.xsl
	$(XSLTPROC) --novalid -o $@ grokDBSchema.xsl hh_data.html

clean:
	$(RM) *~ *.pyc testchiro-db hh_data.owl hh_data.sql $(DB)

