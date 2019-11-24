from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, Text, ForeignKey, Float
from sqlalchemy import create_engine
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.ext.hybrid import hybrid_method
from serialalchemy import Serializable

Base = declarative_base()
engine = create_engine('mysql+pymysql://root:Amazinggaw1452!@localhost/timepix?host=localhost?port=3306', echo=True)


class AcquisitionModel(Base):
    __tablename__ = 'acquisition'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(Text())
    frames = relationship('FrameModel', back_populates='acquisition')


class FrameModel(Base):
    __tablename__ = 'frame'

    id = Column(Integer, primary_key=True, autoincrement=True)
    acquisition_id = Column(Integer, ForeignKey('acquisition.id'))
    acquisition = relationship('AcquisitionModel', back_populates='frames')
    frame_data = Column(Text())
    acq_time = Column(Float())
    acq_start = Column(Float())
    description = Column(Text())
    counts = Column(Integer())
    clusters = relationship('ClusterModel', back_populates='frame')


class ClusterModel(Base, Serializable):
    __tablename__ = 'cluster'

    id = Column(Integer, primary_key=True, autoincrement=True)
    frame_id = Column(Integer, ForeignKey('frame.id'))
    frame = relationship('FrameModel', back_populates='clusters')
    min_area_box = Column(Text())
    track_length = Column(Float())
    intersections = Column(Text())
    region_properties = Column(Text(4294000000))
    bbox = Column(Text())
    bbox_area = Column(Float())
    centroid = Column(Text())
    convex_area = Column(Float())
    convex_image = Column(Text(4294000000))
    coords = Column(Text())
    eccentricity = Column(Float())
    equivalent_diameter = Column(Float())
    euler_number = Column(Integer())
    extent = Column(Float())
    filled_area = Column(Integer())
    filled_image = Column(Text(4294000000))
    image = Column(Text(4294000000))
    inertia_tensor = Column(Text())
    inertia_tensor_eigvals = Column(Text())
    intensity_image = Column(Text(4294000000))
    label = Column(Integer())
    local_centroid = Column(Integer())
    major_axis_length = Column(Float())
    max_intensity = Column(Float())
    min_intensity = Column(Float())
    minor_axis_length = Column(Float())
    moments = Column(Text())
    moments_central = Column(Text())
    moments_hu = Column(Text())
    moments_normalized = Column(Text())
    orientation = Column(Float())
    perimeter = Column(Float())
    slice = Column(Float())
    solidity = Column(Float())
    weighted_centroid = Column(Text())
    weighted_local_centroid = Column(Text())
    weighted_moments = Column(Text())
    weighted_moments_central = Column(Text())
    weighted_moments_hu = Column(Text())
    weighted_moments_normalized = Column(Text())


def get_db_session():
    Session = sessionmaker(bind=engine)
    session = Session()
    return session


if __name__ == '__main__':
    Base.metadata.create_all(engine)


