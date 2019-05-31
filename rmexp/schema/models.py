# -*- coding: utf-8 -*-
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, types, Text

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
    app = Column(String(32))
    client = Column(String(32))
    arrival = Column(Integer)
    finished = Column(Integer)
    reply = Column(Integer)
    utility = Column(types.Float)
    result = Column(String(8192))


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


class IMUSuppression(Base):
    """IMU suppression decision for each frame"""
    __tablename__ = 'IMUSuppression'
    id = Column(Integer, primary_key=True)
    name = Column(String(512), nullable=False)
    trace = Column(String(512), nullable=False)
    index = Column(String(32), nullable=False)
    suppression = Column(String(32))


class ResourceLatency(Base):
    """Resource (cpu, mem) -> latency"""
    __tablename__ = 'ResourceLatency'

    id = Column(Integer, primary_key=True)
    trace = Column(String(512), nullable=False)
    index = Column(String(32), nullable=False)
    cpu = Column(types.FLOAT(53), nullable=False)
    memory = Column(types.FLOAT(53), nullable=False)
    latency = Column(types.FLOAT(53))
    name = Column(String(512))
    num_worker = Column(Integer)


class AppProfile(Base):
    """Application Profile Table"""
    __tablename__ = 'Profile'
    id = Column(Integer, primary_key=True)
    exp = Column(String(512), nullable=False)
    name = Column(String(512), nullable=False)
    trace = Column(String(512), nullable=False)
    index = Column(String(32))
    speed = Column(String(8192))
    data_length = Column(String(8192))


class DataStat(Base):
    """Stats for dataset Table"""
    __tablename__ = 'DataStat'
    id = Column(Integer, primary_key=True)
    app = Column(String(512), nullable=False)
    trace = Column(String(512), nullable=False)
    value = Column(String(1000000))


class GTInst(Base):
    """Ground Truth Instructions."""
    __tablename__ = 'GTInst'
    id = Column(Integer, primary_key=True)
    app = Column(String(512), nullable=False)
    trace = Column(String(512), nullable=False)
    value = Column(String(16384))


class DutyCycleGT(Base):
    """IMU suppression decision for each frame"""
    __tablename__ = 'DutyCycleGT'
    id = Column(Integer, primary_key=True)
    name = Column(String(512), nullable=False)
    trace = Column(String(512), nullable=False)
    index = Column(String(32), nullable=False)
    active = Column(String(32))


class Sec6IntraApp(Base):
    """General experiment table."""
    __tablename__ = 'Sec6IntraApp'
    id = Column(Integer, primary_key=True)
    name = Column(String(512), nullable=False)
    index = Column(Integer)
    app = Column(String(32))
    client = Column(String(32))
    arrival = Column(Integer)
    finished = Column(Integer)
    reply = Column(Integer)
    utility = Column(types.Float)
    is_gt_active = Column(Integer)  # whether a frame is processed by cloudlet
    result = Column(String(512))  # processed result


class Trace(Base):
    """Trace information.
    Aggregated info with symbolic states and IMU data.
    """
    __tablename__ = 'Trace'
    id = Column(Integer, primary_key=True)
    name = Column(String(512), nullable=False)
    trace = Column(String(512), nullable=False)
    fid = Column(String(32), nullable=False)
    symbolic_state = Column(Text)
    rot_x = Column(types.FLOAT(53))
    rot_y = Column(types.FLOAT(53))
    rot_z = Column(types.FLOAT(53))
    acc_x = Column(types.FLOAT(53))
    acc_y = Column(types.FLOAT(53))
    acc_z = Column(types.FLOAT(53))
    sensor_timestamp = Column(types.DateTime)
    active = Column(String(32))
    instruction = Column(Text)
    height = Column(Integer)
    width = Column(Integer)
