# -*- coding: utf-8 -*-
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, types

from rmexp.schema import Base


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
    """General experiment table."""
    __tablename__ = 'LegoLatency'
    id = Column(Integer, primary_key=True)
    name = Column(String(512), nullable=False)
    index = Column(String(32))
    val = Column(Integer)
    date = Column(DateTime, default=datetime.utcnow)
    # FLOAT(53) will magically turn into MYSQL Double data type
    capture = Column(types.FLOAT(53))
    arrival = Column(types.FLOAT(53))
    finished = Column(types.FLOAT(53))


class SS(Base):
    """Symbolic State."""
    __tablename__ = 'SS'
    id = Column(Integer, primary_key=True)
    name = Column(String(512), nullable=False)
    val = Column(String(8192))
    trace = Column(String(512), nullable=False)
    index = Column(String(32))


class IMU(Base):
    """IMU data for each frame"""
    __tablename__ = 'IMU'
    id = Column(Integer, primary_key=True)
    name = Column(String(512), nullable=False)
    trace = Column(String(512), nullable=False)
    index = Column(String(32), nullable=False)

    sensor_timestamp = Column(types.DateTime)

    rot_x = Column(types.FLOAT(53))
    rot_y = Column(types.FLOAT(53))
    rot_z = Column(types.FLOAT(53))
    acc_x = Column(types.FLOAT(53))
    acc_y = Column(types.FLOAT(53))
    acc_z = Column(types.FLOAT(53))
    

class ResourceLatency(Base):
    """Resource (cpu, mem) -> latency"""
    __tablename__ = 'ResourceLatency'

    id = Column(Integer, primary_key=True)
    trace = Column(String(512), nullable=False)
    index = Column(String(32), nullable=False)
    cpu = Column(Integer, nullable=False)
    memory = Column(Integer, nullable=False)
    latency = Column(types.FLOAT(53))