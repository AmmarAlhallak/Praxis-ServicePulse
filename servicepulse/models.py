"""Relationaler Servicebestand; Messwerte verbleiben ausschließlich in Parquet."""
from datetime import datetime
from sqlalchemy import String, Text, Date, DateTime, Integer, BigInteger, ForeignKey, CheckConstraint, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB

class Base(DeclarativeBase):
    pass

class Device(Base):
    __tablename__='devices'
    id: Mapped[str] = mapped_column(String(6),primary_key=True)
    name: Mapped[str] = mapped_column(String(150),default='')
    model: Mapped[str] = mapped_column(String(100),default='')
    location: Mapped[str] = mapped_column(String(200),default='')
    __table_args__=(CheckConstraint("id ~ '^[0-9]{6}$'",name='device_identifier'),)

class Category(Base):
    __tablename__='categories'
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(150),unique=True)

class Source(Base):
    __tablename__='sources'
    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(30))
    name: Mapped[str] = mapped_column(Text)
    sha256: Mapped[str | None] = mapped_column(String(64),unique=True)
    details: Mapped[dict] = mapped_column(JSONB,default=dict)

class Report(Base):
    __tablename__='service_reports'
    id: Mapped[int] = mapped_column(primary_key=True)
    device_id: Mapped[str] = mapped_column(ForeignKey('devices.id'),index=True)
    category_id: Mapped[int] = mapped_column(ForeignKey('categories.id'))
    source_id: Mapped[int] = mapped_column(ForeignKey('sources.id'))
    service_date: Mapped[datetime | None] = mapped_column(Date,index=True)
    description: Mapped[str] = mapped_column(Text,default='')
    component: Mapped[str] = mapped_column(Text,default='')
    status: Mapped[str] = mapped_column(String(30),default='offen')
    notes: Mapped[str] = mapped_column(Text,default='')
    origin: Mapped[str] = mapped_column(String(20))
    source_sheet: Mapped[str | None] = mapped_column(Text)
    source_row: Mapped[int | None] = mapped_column(Integer)
    original: Mapped[dict | None] = mapped_column(JSONB)
    import_key: Mapped[str] = mapped_column(String(200),unique=True)
    version: Mapped[int] = mapped_column(Integer,default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),server_default=func.now())
    __mapper_args__={'version_id_col':version}
    __table_args__=(CheckConstraint("origin IN ('research','manual')",name='report_origin'),
                   CheckConstraint("status IN ('offen','in Bearbeitung','abgeschlossen','nicht angegeben')",name='report_status'),
                   CheckConstraint("origin <> 'research' OR (original IS NOT NULL AND source_row IS NOT NULL AND source_sheet IS NOT NULL)",name='historical_provenance'))

class Action(Base):
    __tablename__='service_actions'
    id: Mapped[int] = mapped_column(primary_key=True)
    report_id: Mapped[int] = mapped_column(ForeignKey('service_reports.id'),unique=True)
    text: Mapped[str] = mapped_column(Text,default='')

class MeasurementFile(Base):
    __tablename__='measurement_files'
    id: Mapped[int] = mapped_column(primary_key=True)
    device_id: Mapped[str] = mapped_column(ForeignKey('devices.id'),index=True)
    source_id: Mapped[int] = mapped_column(ForeignKey('sources.id'))
    path: Mapped[str] = mapped_column(Text,unique=True)
    sha256: Mapped[str] = mapped_column(String(64),index=True)
    kind: Mapped[str] = mapped_column(String(10))
    model: Mapped[str] = mapped_column(Text)
    rows: Mapped[int] = mapped_column(BigInteger)
    columns: Mapped[str] = mapped_column(Text)
    first_time: Mapped[datetime | None] = mapped_column(DateTime)
    last_time: Mapped[datetime | None] = mapped_column(DateTime)
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    mtime_ns: Mapped[int] = mapped_column(BigInteger)
    __table_args__=(CheckConstraint("kind IN ('temp','events')",name='file_kind'),)

class Audit(Base):
    __tablename__='audit_log'
    id: Mapped[int] = mapped_column(primary_key=True)
    report_id: Mapped[int] = mapped_column(ForeignKey('service_reports.id'),index=True)
    version: Mapped[int] = mapped_column(Integer)
    actor: Mapped[str] = mapped_column(Text)
    reason: Mapped[str] = mapped_column(Text)
    before: Mapped[dict | None] = mapped_column(JSONB)
    after: Mapped[dict] = mapped_column(JSONB)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),server_default=func.now())
    __table_args__=(UniqueConstraint('report_id','version'),)
