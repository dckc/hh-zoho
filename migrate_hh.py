
from contextlib import contextmanager
from urllib import urlencode
from urllib2 import urlopen
import StringIO
import csv
import getpass
import json
import os
import pprint
import re
import sqlite3
import sys

from lxml import etree
import xlwt


def main(argv):
    if '--prepare-db' in argv:
        db, bak = argv[2:4]
        prepare_db(db, bak)
    elif '--load-basics' in argv:
        db, username, backup_dir = argv[2:5]

        conn = sqlite3.connect(db)
        def pw_cb():
            return getpass.getpass('Password for %s: ' % username)

        hz = HH_Zoho(conn, username, pw_cb, backup_dir)

        hz.load_basics()

    elif '--truncate-clients' in argv:
        hz = HH_Zoho(None, None, None, None)  # assume we have a ticket
        hz.truncate('client')

    elif '--make-clients-spreadsheet' in argv:
        db, out = argv[2:4]
        make_clients_spreadsheet(db, out)
        

def prepare_db(db, bak, init='hh_data.sql', fixup='hh_fixup.sql'):
    conn = sqlite3.connect(db)

    print >> sys.stderr, 'running script:', init
    conn.executescript(open(init).read())

    for table in ('Batch', 'Office', 'Progressnote',
                  'Client', 'Group', 'Officer',
                  'Session', 'Visit'):
        with transaction(conn) as work:
            print >> sys.stderr, "importing: ", table
            import_csv(work, os.path.join(bak, '%s.csv' % table), table)

    print >> sys.stderr, 'running script:', fixup
    conn.executescript(open(fixup).read())


class ZohoAPI(object):
    def __init__(self, login_id, password_cb):
        # violates the "constructors never fail" M3 convention
        self._ticket = self._get_ticket(login_id, password_cb)
        self._apikey = self._get_apikey()

    def _get_ticket(self, login_id, password_cb,
                    ticket_file=',zoho_ticket',
                    api_addr='https://accounts.zoho.com/login',
                    servicename='ZohoCreator'):
        # cf https://api.creator.zoho.com/Creator-API-Prerequisites-Generate-a-Ticket.html
        try:
            body = open(ticket_file).read()
        except IOError:
            params = {'LOGIN_ID': login_id,
                      'PASSWORD': password_cb(),
                      'FROM_AGENT': 'true',
                      'servicename': servicename,
                      'submit': 'Generate Ticket'}
            print >> sys.stderr, 'getting ticket...'
            ans = urlopen(api_addr, urlencode(params))
            body = ans.read()
            open(ticket_file, "w").write(body)
        return [v for n, v in
                [parts for parts in
                 [l.split('=', 1) for l in body.split('\n')]
                 if len(parts) == 2]
                if n == 'TICKET'][0]

    def _get_apikey(self,
                    api_key_file=',zoho_api_key'):
        return open(api_key_file).read().strip()

    def form_fields(self, app, form,
                    url='http://creator.zoho.com/api/%(format)s/%(applicationName)s/%(formName)s/fields/apikey=%(apikey)s&ticket=%(ticket)s'):
        # This worked to test API key/ticket usage.
        # print json.dumps(hz.form_fields(hz.app, 'group'),
        #                  sort_keys=True, indent=4)

        print >> sys.stderr, 'getting form fields...'
        ans = urlopen(url % dict(format='json',
                                 applicationName=app,
                                 formName=form,
                                 apikey=self._apikey,
                                 ticket=self._ticket))
        return json.loads(ans.read())

    def add_records(self, app, form, columns, rows, chunk_size=200):
        done = 0
        out = []
        while done < len(rows):
            print >> sys.stderr, '%s: %d of %d' % (form, done, len(rows))
            chunk = self._add_records(app, form, columns,
                                      rows[done:done + chunk_size])
            print >> sys.stderr, 'added %d in %s.' % (len(chunk), form)
            out.extend(chunk)
            done += chunk_size
        return out

    def _add_records(self, app, form, columns, rows,
                    url='http://creator.zoho.com/api/xml/write'):
        e = etree.Element('ZohoCreator')
        sub = etree.SubElement
        e_app = sub(sub(e, 'applicationlist'), 'application', name=app)
        e_form = sub(sub(e_app, 'formlist'), 'form', name=form)
        for row in rows:
            e_add = sub(e_form, 'add')
            for n in columns:
                # watch out for:
                # File "apihelpers.pxi", line 1242, in lxml.etree._utf8 (src/lxml/lxml.etree.c:19848)
                # ValueError: All strings must be XML compatible: Unicode or ASCII, no NULL bytes
                sub(sub(e_add, 'field', name=n), 'value').text = row[n]
        print >> sys.stderr, 'add...', form, columns, rows[0]
        #print >>sys.stderr, etree.tostring(e, pretty_print=True)
        ans = urlopen(url,
                      urlencode(dict(apikey=self._apikey,
                                     ticket=self._ticket,
                                     XMLString=etree.tostring(e))))
        doc = etree.parse(ans)
        #print >> sys.stderr, etree.tostring(doc, pretty_print=True)
        for err in doc.xpath('//response/result/form'
                             '/add[status/text() != "Success"]'):
            print >> sys.stderr, etree.tostring(err, pretty_print=True)
        return doc.xpath('//response/result/form'
                         '/add[status/text()="Success"]/values')

    def csv_write(self, app, form, data,
                  url='http://creator.zoho.com/api/csv/write'):
        print >> sys.stderr, 'api/csv/write...'
        ans = urlopen(url,
                      urlencode(dict(apikey=self._apikey,
                                     ticket=self._ticket,
                                     applicationName=app,
                                     CSVString=(("%s,%s,Add\n" % (app, form))
                                                + data))))
        return ans.read().split('<br>')

    def delete(self, app, form, criteria, reloperator,
                   url='http://creator.zoho.com/api/xml/write'):
        e = etree.Element('ZohoCreator')
        sub = etree.SubElement
        e_app = sub(sub(e, 'applicationlist'), 'application', name=app)
        e_form = sub(sub(e_app, 'formlist'), 'form', name=form)
        e_crit = sub(sub(e_form, 'delete'), 'criteria')
        first = True
        for n, op, v in criteria:
            if not first:
                sub(e_crit, 'reloperator').text = reloperator
            sub(e_crit, 'field', name=n, compOperator=op, value=v)

        print >> sys.stderr, 'delete %s...' % form
        ans = urlopen(url,
                     urlencode(dict(apikey=self._apikey,
                                    ticket=self._ticket,
                                    XMLString=etree.tostring(e))))
        return ans.read()


class HH_Zoho(ZohoAPI):
    app = 'hope-harbor'

    def __init__(self, conn, login_id, password_cb, backup_dir):
        self._dir = backup_dir
        self._conn = conn
        ZohoAPI.__init__(self, login_id, password_cb)

    def load_basics(self):
        self.load_offices()
        self.load_officers()
        self.load_groups()

    def load_groups(self, basename="Group.csv"):
        def fixup(tr):
            return [dict(rec, id_dabble=rec['ID'],
                         # "USD $20" => "20"
                         rate=rec['rate'][len('USD $'):])
                    for rec in tr]

        self._load_table(basename, 'group',
                         ('Name', 'rate', 'Eval', 'id_dabble'),
                         fixup)
        
    def _load_table(self, basename, form, columns_out, fixup):
        tr = self._csv_reader(basename)
        tr.next()
        self.truncate(form)

        results = self.add_records(self.app, form, columns_out, fixup(tr))

        idmap = []
        for e_vals in results:
            id_zoho = e_vals.xpath('field[@name="ID"]/value/text()')[0]
            id_dabble = e_vals.xpath('field[@name="id_dabble"]/value/text()')[0]
            idmap.append((form, int(id_dabble), id_zoho))
        with transaction(self._conn) as work:
            work.executemany('''insert into id_map(t, did, zid)
                                values(?, ?, ?)''',
                             idmap)
            print >> sys.stderr, 'id_map: %d x %s' % (work.rowcount, form)

    def _csv_reader(self, basename):
        return csv.DictReader(open(os.path.join(self._dir, basename)))

    def truncate(self, form):
        return self.delete(self.app, form,
                           [('ID', 'GreaterThan', '0')], 'AND')

    def load_offices(self, basename="Office.csv"):
        def fixup(tr):
            return [dict(rec, id_dabble=rec['ID'],
                         address=rec['address'].replace('\x0b', ''))
                    for rec in tr]

        self._load_table(basename, 'office',
                         ('Name', 'fax', 'notes', 'address', 'id_dabble'),
                         fixup)

    def load_officers(self, basename="Officer.csv"):
        idmap = self._idmap('office')

        def fixup(tr):
            return [dict(rec, id_dabble=rec['ID'],
                         office=idmap.get(rec['office'], ''))
                    for rec in tr
                    if rec['Name']]

        self._load_table(basename, 'officer',
                         ('Name', "email", "office", "id_dabble"),
                         fixup)

    def _idmap(self, form):
        with transaction(self._conn) as q:
            q.execute("select did, zid from id_map where t=?", (form,))
            idmap=q.fetchall()
        return dict([(str(k), v) for k, v in idmap])

    def load_clients(self, basename="Client.csv"):
        # dead code?
        idmap = self._idmap('officer')
        def fixup(tr):
            return [dict(rec, id_dabble=rec['ID'],
                         officer=idmap.get(rec['officer'], None))
                    for rec in tr]

        self._load_table(basename, 'client',
                         ("Name", "Ins", "Approval", "DX", "Note",
                          "Officer", "DOB", "address", "phone",
                          "batch", "id_dabble"),
                         fixup)

    def load_sessions(self, basename="Session.csv"):
        idmap = self._idmap('group')
        def fixup(tr):
            return [dict(rec, id_dabble=rec['ID'],
                         group_id=idmap.get(rec['group'], ''),
                         date_field=rec['date'])
                    for rec in tr
                    if rec['group'] and rec['date']]

        self._load_table(basename, 'session',
                         ("date_field", "Group", "Time", "Therapist",
                          'id_dabble'),
                         fixup)


def make_clients_spreadsheet(db, out='clients.xls'):
    conn = sqlite3.connect(db)
        
    with transaction(conn) as q:
        q.execute('''select m.zid as officer, c.*
                     from clients c
                     join current_clients cc
                       on cc.id = c.id
                     left join id_map m
                       on m.t = 'officer' and m.did = c.officer
                     order by c.name''')
        wb = xlwt.Workbook()
        ws = wb.add_sheet('Clients')
        col = 0
        # prevent 18 digit IDs from turning into floats
        intfmt = xlwt.easyxf(num_format_str='0')
        for coldesc in q.description:
            ws.write(0, col, coldesc[0])
            col += 1
        rownum = 1
        for row in q.fetchall():
            col = 0
            for v in row:
                if type(v) in (type(1), type(1L)):
                    ws.write(rownum, col, v, intfmt)
                else:
                    ws.write(rownum, col, v)
                col += 1
            rownum += 1
    wb.save(out)


def import_csv(trx, fn, table, colsize=500):
    '''Import data from a comma-separated file into a table.

    1st line contains column names; '_' is substituted for spaces.
    '''
    rows = csv.reader(open(fn))
    colnames = [n.replace(' ', '_').upper()
                for n in rows.next()]
    trx.execute(_create_ddl(table, colnames, colsize))
    trx.executemany(_insert_dml(table, colnames),
                    [dict(zip(colnames,
                              [cell.decode('utf-8') for cell in row]))
                     for row in rows])


def _create_ddl(table, colnames, colsize):
    '''
    >>> _create_ddl('item', ('id', 'size', 'price'), 50)
    'create table "item" ("id" varchar2(50), "size" varchar2(50), "price" varchar2(50))'
    '''
    return 'create table "%s" (%s)' % (
        table, ', '.join(['"%s" varchar2(%d)' % (n, colsize)
                          for n in colnames]))


def _insert_dml(table, colnames):
    '''
    >>> _insert_dml('item', ('id', 'size', 'price'))
    'insert into "item" ("id", "size", "price") values (:id, :size, :price)'
    '''
    return 'insert into "%s" (%s) values (%s)' % (
        table,
        ', '.join(['"%s"' % n for n in colnames]),
        ', '.join([':' + n
                   for n in colnames]))


@contextmanager
def transaction(conn):
    '''Return an Oracle database cursor manager.

    :param conn: an Oracle connection
    '''
    c = conn.cursor()
    try:
        yield c
    except sqlite3.Error:
        conn.rollback()
        raise
    else:
        conn.commit()
    finally:
        c.close()


if __name__ == '__main__':
    import sys
    main(sys.argv)
