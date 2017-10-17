import sys
from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine

Base = declarative_base()


class City(Base):
    __tablename__ = 'city'

    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)


class Venue(Base):
    __tablename__ = 'venue'

    name = Column(String(250), nullable=False)
    id = Column(Integer, primary_key=True)
    address = Column(String(250))
    description = Column(String(250))
    city_id = Column(Integer, ForeignKey('city.id'))
    city = relationship(City)


engine = create_engine('sqlite:///venue.db')
Base.metadata.create_all(engine)
