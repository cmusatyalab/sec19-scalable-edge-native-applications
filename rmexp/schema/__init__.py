# -*- coding: utf-8 -*-
from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from rmexp import config

engine = create_engine(
    config.DB_URI
)
meta = MetaData(engine)
Base = declarative_base(metadata=meta)
