# -*- coding: utf-8 -*-
from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
import const

engine = create_engine(
    const.MYSQL_URI
)
meta = MetaData(engine)
Base = declarative_base(metadata=meta)
