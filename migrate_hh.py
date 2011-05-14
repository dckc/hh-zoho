
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


def main(argv):
    username, backup_dir = argv[1:3]
    def pw_cb():
        return getpass.getpass('Password for %s: ' % username)

    hz = HH_Zoho(username, pw_cb, backup_dir)

    # This worked to test API key/ticket usage.
    #print json.dumps(hz.form_fields(hz.app, 'group'), sort_keys=True, indent=4)

    # but I'm getting an HTTP 500 error when I try delete.
    print hz.load_groups()
    pprint.pprint(hz._group)
    #hz.load_all()

def main_import_csv(argv):
    db, fn = argv[1:3]
    table = os.path.basename(fn)[:-len(".csv")]
    conn = sqlite3.connect(db)
    with transaction(conn) as work:
        import_csv(work, fn, table)


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
            print >>sys.stderr, 'getting ticket...'
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
        print >>sys.stderr, 'getting form fields...'
        ans = urlopen(url % dict(format='json',
                                 applicationName=app,
                                 formName=form,
                                 apikey=self._apikey,
                                 ticket=self._ticket))
        return json.loads(ans.read())


    def add_records(self, app, form, columns, rows,
                    url='http://creator.zoho.com/api/xml/write'):
        e = etree.Element('ZohoCreator')
        sub = etree.SubElement
        e_app = sub(sub(e, 'applicationlist'), 'application', name=app)
        e_form = sub(sub(e_app, 'formlist'), 'form', name=form)
        for row in rows:
            e_add = sub(e_form, 'add')
            for n in columns:
                sub(sub(e_add, 'field', name=n), 'value').text = row[n]
        print >>sys.stderr, 'add...'
        #print >>sys.stderr, etree.tostring(e, pretty_print=True)
        ans = urlopen(url,
                      urlencode(dict(apikey=self._apikey,
                                     ticket=self._ticket,
                                     XMLString=etree.tostring(e))))
        return etree.parse(ans)

        
    def csv_write(self, app, form, data,
                  url='http://creator.zoho.com/api/csv/write'):
        print >>sys.stderr, 'api/csv/write...'
        ans = urlopen(url,
                      urlencode(dict(apikey=self._apikey,
                                     ticket=self._ticket,
                                     applicationName=app,
                                     CSVString=(("%s,%s,Add\n" %(app, form))
                                                + data))))
        return ans.read().split('<br>')


    def delete(self, app, form, criteria, reloperator,
                   url='http://creator.zoho.com/api/xml/write'
                   ):
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

        print >>sys.stderr, 'delete...'
        ans = urlopen(url,
                     urlencode(dict(apikey=self._apikey,
                                    ticket=self._ticket,
                                    XMLString=etree.tostring(e))))
        return ans.read()


class HH_Zoho(ZohoAPI):
    app = 'hope-harbor'

    def __init__(self, login_id, password_cb, backup_dir):
        self._dir = backup_dir
        self._group = {}  # id_dabble -> zoho ID
        self._office = {}
        self._officer = {}
        self._client = {}
        self._session = {}
        ZohoAPI.__init__(self, login_id, password_cb)

    def load_all(self):
        self.load_groups()
        self.load_offices()
        self.load_officers()

    def load_groups(self, basename="Group.csv"):
        self.truncate('group')
        tr = self._csv_reader(basename)

        rows = [dict(rec, id_dabble=rec['ID'],
                     # "USD $20" => "20"
                     rate=rec['rate'][len('USD $'):])
                for rec in tr]
        doc = self.add_records(self.app, 'group',
                               ('Name', 'rate', 'Eval', 'id_dabble'),
                               rows)
        idmap = self._group
        for e_vals in doc.xpath('//response/result/form'
                                '/add[status/text()="Success"]/values'):
            id_zoho = e_vals.xpath('field[@name="ID"]/value/text()')[0]
            id_dabble = e_vals.xpath('field[@name="id_dabble"]/value/text()')[0]
            idmap[id_dabble] = id_zoho

    def _csv_reader(self, basename):
        return csv.DictReader(open(os.path.join(self._dir, basename)))

    def _load_records(self, form, bufwr, idmap):
        data = bufwr.getvalue()
        print >> sys.stderr, "data for: ", form
        print >> sys.stderr, data
        lines = self.csv_write(self.app, form, data)
        print >>sys.stderr, lines
        # Success,[ID = 765721000000034047 , ... id_dabble = 109653 , rate = 20]
        for l in lines:
            if l.startswith("Success,"):
                m = re.search(r'\[ID = (\d+) ,', l)
                if not m:
                    raise ValueError, l
                ID = m.group(1)
                m = re.search(r'id_dabble = (\d+) ,', l)
                if not m:
                    raise ValueError, l
                id_dabble = m.group(1)
                idmap[id_dabble] = ID
        print >> sys.stderr, "map for", form
        sys.stderr.write(pprint.pformat(idmap))

    def truncate(self, form):
        return self.delete(self.app, form,
                           [('ID', 'GreaterThan', '0')], 'AND')

    def load_offices(self, basename="Office.csv"):
        tr, tw, bufwr = csv_d2z(self._dir, basename,
                                ['Name', 'fax', 'notes', 'address',
                                 'id_dabble'])
        for rec in tr:
            tw.writerow(dict(rec, id_dabble=rec['ID'],
                             # Zoho can't handle newlines in CSV import :-/
                             notes=rec['notes'].replace('\n', ' '),
                             address=rec['address'].replace('\n', ' ')))
        self._load_records('office', bufwr, self._office)

    def load_officers(self, basename="Officer.csv"):
        tr, tw, buf = csv_d2z(self._dir, basename,
                              ['Name', "email","office","id_dabble"])
        for rec in tr:
            if not rec['Name']:  # bogus record
                continue
            tw.writerow(dict(rec, id_dabble=rec['ID'],
                             office=(rec['office'] and  # skip blank office
                                     self._office[rec['office']])))
        self._load_records('officer', buf, self._officer)

    def load_clients(self, basename="Session.csv"):
        tr, tw, buf = csv_d2z(self._dir, basename,
                              ["Name", "Ins", "Approval", "DX", "Note",
                               "officer", "DOB", "address", "phone",
                               "batch", "id_dabble"])
        for rec in tr:
            tw.writerow(dict(rec, id_dabble=rec['ID'],
                             officer=self._officer[rec['officer']]))
        self._load_records('client', buf, self._client)

    def load_sessions(self, basename="Session.csv"):
        tr, tw, buf = csv_d2z(self._dir, basename,
                              ["date","group","Time","Therapist"])
        for rec in tr:
            tw.writerow(dict(rec, id_dabble=rec['ID'],
                             group=self._group(rec['group'])))
        self._load_records('session', buf, self._session)
        

def csv_d2z(dirpath, basename, columns_out):
    dr = csv.DictReader(open(os.path.join(dirpath, basename)))
    columns_in = dr.next()
    bufwr = StringIO.StringIO()
    dw = csv.DictWriter(bufwr, columns_out, extrasaction='ignore')
    dw.writerow(dict(zip(columns_out, columns_out)))
    return dr, dw, bufwr


def import_csv(trx, fn, table, colsize=500):
    '''Import data from a comma-separated file into a table.

    1st line contains column names; '_' is substituted for spaces.
    '''
    rows = csv.reader(open(fn))
    colnames = [n.replace(' ', '_').upper()
                for n in rows.next()]
    trx.execute(_create_ddl(table, colnames, colsize))
    trx.executemany(_insert_dml(table, colnames),
                    [dict(zip(colnames, row))
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
    return 'insert into "%s" (%s) values (%s)' %(
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
