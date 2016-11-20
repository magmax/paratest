import os
import sqlite3
import logging


logger = logging.getLogger('paratest')


class Persistence(object):
    def __init__(self, db_path, projectname):
        self.create = not os.path.exists(db_path)
        self.projectname = projectname
        self.db_path = db_path
        self.execution = None

    def initialize(self):
        con = sqlite3.connect(self.db_path)
        if self.create:
            with con:
                logger.info("Creating persistence file")
                con.execute(
                    "create table executions"
                    "(id integer primary key, source varchar, "
                    "timestamp date default (datetime('now','localtime')))"
                )
                con.execute(
                    "create table testtime"
                    "(id integer primary key, source varchar, test varchar, "
                    "duration float, execution int, "
                    "FOREIGN KEY(execution) "
                    "REFERENCES executions(id) on delete cascade)"
                )
            self.create = False
        with con:
            c = con.execute(
                "select id from executions where source=? "
                "order by id desc limit 5, 1",
                (self.projectname, )
            )
            f = c.fetchone()
            deprecated_executions = f[0] if f else None
            if deprecated_executions is not None:
                con.execute(
                    "delete from executions "
                    "where id <= ? and source=?",
                    (deprecated_executions, self.projectname)
                )
                con.execute(
                    "delete from testtime "
                    "where execution <= ? and source=?",
                    (deprecated_executions, self.projectname)
                )
            con.execute("insert into executions(source) values (?)",
                        (self.projectname, ))
            c = con.execute("select max(id) from executions where source=?",
                            (self.projectname, ))
            self.execution = c.fetchone()[0]
        con.close()

    def get_priority(self, test):
        con = sqlite3.connect(self.db_path)
        try:
            cursor = con.execute(
                'select avg(duration) from testtime where source=? and test=?',
                (self.projectname, test)
            )
            return -1 * int(cursor.fetchone()[0] or 0)
        finally:
            con.close()

    def add(self, test, duration):
        con = sqlite3.connect(self.db_path)
        with con:
            con.execute(
                'insert into testtime'
                '(source, test, duration, execution) values(?, ?, ?, ?)',
                (self.projectname, test, duration, self.execution)
            )
        con.close()

    def show(self):
        if not os.path.exists(self.db_path):
            print("No database was found")
            return
        con = sqlite3.connect(self.db_path)
        for item in con.execute('select distinct source from testtime'):
            projectname = item[0]
            for test in con.execute(
                    'select test, avg(duration) from testtime where source=? '
                    'group by test order by avg(duration) desc',
                    (projectname,)
            ):
                print('    %.2f: %s' % (test[1], test[0]))

        con.close()
