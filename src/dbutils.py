
from __future__ import absolute_import, division, print_function


class Connector(object):
    def __init__(self):
        self._engine = None
        return super(Connector, self).__init__()


class MYSQLConnector(object):
    def __init__(self):
        return super(MYSQLConnector, self).__init__()


def main():
    import sqlalchemy as db
    engine = db.create_engine('dialect+driver://user:pass@host:port/db')


if __name__ == '__main__':
    main()
