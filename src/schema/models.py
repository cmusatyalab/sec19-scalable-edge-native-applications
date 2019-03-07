# -*- coding: utf-8 -*-
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String

from . import Base


class Exp(Base):
    """General experiment table."""
    __tablename__ = 'Exp'
    id = Column(Integer, primary_key=True)
    key = Column(String(512), nullable=False)
    val = Column(String(512))
    date = Column(DateTime, default=datetime.utcnow)


class ExpLatency(Base):
    """General experiment table."""
    __tablename__ = 'ExpLatency'
    id = Column(Integer, primary_key=True)
    name = Column(String(512), nullable=False)
    index = Column(Integer)
    val = Column(Integer)
    date = Column(DateTime, default=datetime.utcnow)


class LegoLatency(Base):
    __tablename__ = 'LegoLatency'
    id = Column(Integer, primary_key=True)
    key = Column(String(512), nullable=False)
    val = Column(String(512))
    date = Column(DateTime, default=datetime.utcnow)
