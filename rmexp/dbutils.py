
from __future__ import absolute_import, division, print_function

import contextlib

from rmexp import config, schema
from sqlalchemy import Column, DateTime, Integer, String, create_engine
from sqlalchemy.engine.url import URL
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker


def get_session():
    Session = sessionmaker()
    Session.configure(bind=schema.engine)
    session = Session()
    return session


@contextlib.contextmanager
def session_scope(dry_run=True):
    """Provide a transactional scope around a series of session operations.
    To use:
    with session_scope() as sess:
        blah...
    """
    if dry_run:
        session = None
    else:
        session = get_session()

    try:
        yield session
        if session is not None:
            session.commit()
    except:
        if session is not None:
            session.rollback()
        raise
    finally:
        if session is not None:
            session.close()


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
    if sess is None:
        return None
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
