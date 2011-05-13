
import sqlite3
import os
from contextlib import contextmanager
import csv
from urllib2 import urlopen
from urllib import urlencode
import getpass

def main(argv):
    u = argv[1]
    def pw_cb():
        return getpass.getpass('Password for %s: ' % u)
    print zoho_api_ticket(u, pw_cb)


def main_import_csv(argv):
    db, fn = argv[1:3]
    table = os.path.basename(fn)[:-len(".csv")]
    conn = sqlite3.connect(db)
    with transaction(conn) as work:
        import_csv(work, fn, table)


def zoho_api_ticket(login_id, password_cb,
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
