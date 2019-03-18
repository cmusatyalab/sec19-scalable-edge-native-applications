
from __future__ import absolute_import, division, print_function

from sqlalchemy import create_engine
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.engine.url import URL
from rmexp import config

engine = create_engine(config.DB_URI)


def get_session():
    Session = sessionmaker()
    Session.configure(bind=engine)
    session = Session()
    return session


def get_or_create(session, model, defaults=None, **kwargs):
    """
    Get or create a model instance while preserving integrity.
    """

    record = session.query(model).filter_by(**kwargs).first()
    if record is not None:
        return record, False
    else:
        if defaults is not None:
            kwargs.update(defaults)
        try:
            with session.begin_nested():
                instance = model(**kwargs)
                session.add(instance)
                return instance, True
        except IntegrityError:
            return session.query(model).filter_by(**kwargs).one(), False


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
