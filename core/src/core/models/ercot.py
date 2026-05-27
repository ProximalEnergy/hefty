"""SQLAlchemy ERCOT schema models."""

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base


##### START ERCOT SCHEMA #####
# NOTE: Every model in the ERCOT schema must specify
# `__table_args__ = {"schema": "ercot"}`.
class DME(Base):
    __tablename__ = "dmes"

    dme_id: Mapped[int] = mapped_column(primary_key=True)
    name_short: Mapped[str] = mapped_column(unique=True)
    name_long: Mapped[str | None]

    __table_args__ = {"schema": "ercot"}


class QSE(Base):
    __tablename__ = "qses"

    qse_id: Mapped[int] = mapped_column(primary_key=True)
    name_short: Mapped[str] = mapped_column(unique=True)
    name_long: Mapped[str | None]

    __table_args__ = {"schema": "ercot"}


class Resource(Base):
    __tablename__ = "resources"

    resource_id: Mapped[int] = mapped_column(primary_key=True)
    name_gen: Mapped[str] = mapped_column(unique=True)
    name_load: Mapped[str]
    name_long: Mapped[str]
    county: Mapped[str]
    in_service: Mapped[int] = mapped_column(sa.SmallInteger)
    capacity_power: Mapped[float] = mapped_column(sa.Double)
    qse_id: Mapped[int] = mapped_column(sa.ForeignKey("ercot.qses.qse_id"))
    dme_id: Mapped[int] = mapped_column(sa.ForeignKey("ercot.dmes.dme_id"))
    settlement_point_id: Mapped[int] = mapped_column(
        sa.ForeignKey("ercot.settlement_points.settlement_point_id"),
    )

    qse = relationship("QSE", backref="resources")
    dme = relationship("DME", backref="resources")
    settlement_point = relationship("SettlementPoint", backref="resources")

    __table_args__ = {"schema": "ercot"}


class SCEDGen(Base):
    __tablename__ = "sced_gen"

    time: Mapped[sa.DateTime] = mapped_column(
        sa.DateTime(timezone=True),
        primary_key=True,
    )
    resource_id: Mapped[int] = mapped_column(
        sa.ForeignKey("ercot.resources.resource_id"),
        primary_key=True,
    )
    power_generated: Mapped[float] = mapped_column(sa.Double)

    sa.Index("sced_gen_time_idx", time.desc())

    __table_args__ = {"schema": "ercot"}


class SCEDLoad(Base):
    __tablename__ = "sced_load"

    time: Mapped[sa.DateTime] = mapped_column(
        sa.DateTime(timezone=True),
        primary_key=True,
    )
    resource_id: Mapped[int] = mapped_column(
        sa.ForeignKey("ercot.resources.resource_id"),
        primary_key=True,
    )
    power_consumed: Mapped[float] = mapped_column(sa.Double)

    sa.Index("sced_load_time_idx", time.desc())

    __table_args__ = {"schema": "ercot"}


class SettlementPoint(Base):
    __tablename__ = "settlement_points"

    settlement_point_id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True)
    settlement_point_type_id: Mapped[int] = mapped_column(
        sa.ForeignKey("ercot.settlement_point_types.settlement_point_type_id"),
    )
    load_zone_id: Mapped[int | None] = mapped_column(
        sa.ForeignKey("ercot.settlement_points.settlement_point_id"),
    )
    trading_hub_id: Mapped[int | None] = mapped_column(
        sa.ForeignKey("ercot.settlement_points.settlement_point_id"),
    )

    settlement_point_type = relationship("SettlementPointType")
    load_zone = relationship(
        "SettlementPoint",
        foreign_keys=[load_zone_id],
        remote_side=[settlement_point_id],
    )
    trading_hub = relationship(
        "SettlementPoint",
        foreign_keys=[trading_hub_id],
        remote_side=[settlement_point_id],
    )

    __table_args__ = {"schema": "ercot"}


class SettlementPointMarket(Base):
    __tablename__ = "settlement_point_markets"

    settlement_point_market_id: Mapped[int] = mapped_column(
        sa.SmallInteger,
        primary_key=True,
        autoincrement=False,
    )
    name_short: Mapped[str] = mapped_column(unique=True)
    name_long: Mapped[str] = mapped_column(unique=True)

    __table_args__ = {"schema": "ercot"}


class SettlementPointType(Base):
    __tablename__ = "settlement_point_types"

    settlement_point_type_id: Mapped[int] = mapped_column(
        sa.SmallInteger,
        primary_key=True,
        autoincrement=False,
    )
    name_short: Mapped[str] = mapped_column(unique=True)
    name_long: Mapped[str] = mapped_column(unique=True)

    __table_args__ = {"schema": "ercot"}


class DAMSPP(Base):
    __tablename__ = "dam_spp"

    time: Mapped[sa.DateTime] = mapped_column(
        sa.DateTime(timezone=True),
        primary_key=True,
    )
    settlement_point_id: Mapped[int] = mapped_column(
        sa.ForeignKey("ercot.settlement_points.settlement_point_id"),
        primary_key=True,
    )
    price: Mapped[float] = mapped_column(sa.Double)

    sa.Index("dam_spp_time_idx", time.desc())

    __table_args__ = {"schema": "ercot"}


class RTMSPP(Base):
    __tablename__ = "rtm_spp"

    time: Mapped[sa.DateTime] = mapped_column(
        sa.DateTime(timezone=True),
        primary_key=True,
    )
    settlement_point_id: Mapped[int] = mapped_column(
        sa.ForeignKey("ercot.settlement_points.settlement_point_id"),
        primary_key=True,
    )
    price: Mapped[float] = mapped_column(sa.Double)

    sa.Index("rtm_spp_time_idx", time.desc())

    __table_args__ = {"schema": "ercot"}


##### END ERCOT SCHEMA #####
