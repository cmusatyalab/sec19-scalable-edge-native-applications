
from __future__ import absolute_import, division, print_function

from sqlalchemy import create_engine
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.engine.url import URL
from rmexp import config
from rmexp import schema


def get_session():
    Session = sessionmaker()
    Session.configure(bind=schema.engine)
    session = Session()
    return session


def insert(sess, model, vals_dict):
    """
    Insert a record
    """
    create_dict = {}
    create_dict.update(vals_dict)
    record = model(**create_dict)
    sess.add(record)


def get_or_create(session, model, **kwargs):
    """
    Get or create a model instance while preserving integrity.
    """

    record = session.query(model).filter_by(**kwargs).first()
    if record is not None:
        return record, False
    else:
        with session.begin_nested():
            instance = model(**kwargs)
            session.add(instance)
            return instance, True


def insert_or_update_one(sess, model, keys_dict, vals_dict):
    record = sess.query(model).filter_by(**keys_dict).one_or_none()
    if record is not None:
        sess.query(model).filter_by(**keys_dict).update(vals_dict)
    else:
        create_dict = {}
        create_dict.update(keys_dict)
        create_dict.update(vals_dict)
        record = model(**create_dict)
        sess.add(record)
    return record


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
