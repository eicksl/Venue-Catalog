import sys
from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine

Base = declarative_base()


class Category(Base):
    __tablename__ = 'category'

    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)


class Venue(Base):
    __tablename__ = 'venue'

    name = Column(String(250), nullable=False)
    id = Column(Integer, primary_key=True)
    address = Column(String(250))
    phone = Column(String(30))
    description = Column(String(250))
    image = Column(String(250))
    category_id = Column(Integer, ForeignKey('category.id'))
    category = relationship(Category)


    @property
    def serialize(self):
        return {
            'id': self.id,
            'name': self.name,
            'address': self.address,
            'phone': self.phone,
            'description': self.description,
            'image': self.image
        }


engine = create_engine('sqlite:///venue.db')
Base.metadata.create_all(engine)
