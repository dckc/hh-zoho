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

