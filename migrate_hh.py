
import sqlite3
import os
from contextlib import contextmanager
import csv
from urllib2 import urlopen
from urllib import urlencode
import getpass
import json
import StringIO
import re


def main(argv):
    username, backup_dir = argv[1:3]
    def pw_cb():
        return getpass.getpass('Password for %s: ' % username)

    hz = HH_Zoho(username, pw_cb, backup_dir)

    # This worked to test API key/ticket usage.
    #print json.dumps(hz.form_fields(hz.app, 'group'), sort_keys=True, indent=4)

    # but I'm getting an HTTP 500 error when I try delete.
    #hz.truncate('group')

    hz.load_groups()
    print json.dumps(hz._group, sort_keys=True, indent=4)

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
        ans = urlopen(url % dict(format='json',
                                 applicationName=app,
                                 formName=form,
                                 apikey=self._apikey,
                                 ticket=self._ticket))
        return json.loads(ans.read())


    def csv_write(self, app, form, data,
                  url='http://creator.zoho.com/api/csv/write'):
        ans = urlopen(url,
                      urlencode(dict(apikey=self._apikey,
                                     ticket=self._ticket,
                                     applicationName=app,
                                     CSVString=(("%s,%s,Add\n" %(app, form))
                                                + data))))
        return ans.read().split('<br>')


    def delete(self, app, form, criteria, reloperator,
               url='http://creator.zoho.com/api/%(format)s/%(applicationName)s/%(formName)s/delete/'):
        # shared user mode not supported
        ans = urlopen(url % {'format': 'json',
                             'applicationName': app,
                             'formName': form},
                     urlencode(dict(apikey=self._apikey,
                                    ticket=self._ticket,
                                    criteria=criteria,
                                    reloperator=reloperator)))
        details = json.loads(ans.read())
        print >>sys.stderr, "@@delete details", details
        if details['formname'][0]['operation'][2]['status'] != 'Success':
            raise ValueError, details
        return details


class HH_Zoho(ZohoAPI):
    app = 'hope-harbor'

    def __init__(self, login_id, password_cb, backup_dir):
        self._dir = backup_dir
        self._group = {}  # id_dabble -> zoho ID
        ZohoAPI.__init__(self, login_id, password_cb)

    def load_groups(self, basename="Group.csv"):
        gr = csv.DictReader(open(os.path.join(self._dir, basename)))
        columns_in = gr.next()
        bufwr = StringIO.StringIO()
        columns_out = ['Name', 'rate', 'id_dabble']
        gw = csv.DictWriter(bufwr, columns_out)
        gw.writerow(dict(zip(columns_out, columns_out)))

        for group in gr:
            gw.writerow(dict(Name=group['Name'],
                             rate=group['rate'][len('USD $'):],
                             id_dabble=group['ID']))
        data = bufwr.getvalue()
        #print >>sys.stderr, "data:\n", data
        lines = self.csv_write(self.app, "group", bufwr.getvalue())
        # Success,[ID = 765721000000034047 , ... id_dabble = 109653 , rate = 20]
        for l in lines:
            if l.startswith("Success,"):
                m = re.search(r'\[ID = (\d+) ,', l)
                if not m:
                    raise ValueError, l
                ID = int(m.group(1))
                m = re.search(r'id_dabble = (\d+) ,', l)
                if not m:
                    raise ValueError, l
                id_dabble = int(m.group(1))
                self._group[id_dabble] = ID

    def truncate(self, form):
        self.delete(self.app, form, 'ID > 0', 'AND')


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
