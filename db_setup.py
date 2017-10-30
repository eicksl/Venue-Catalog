from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine

Base = declarative_base()


class User(Base):
    __tablename__ = 'user'

    key = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    email = Column(String(250), nullable=False)
    sub = Column(String(250)) # Unique google account identifier


class Category(Base):
    __tablename__ = 'category'

    key = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)

    @property
    def serialize(self):
        return {
            'name': self.name,
            'key': self.key
        }


class Venue(Base):
    __tablename__ = 'venue'

    name = Column(String(250), nullable=False)
    key = Column(Integer, primary_key=True)
    address = Column(String(250))
    phone = Column(String(30))
    description = Column(String(250))
    image = Column(String(250))
    api_id = Column(String(30))
    category_key = Column(Integer, ForeignKey('category.key'))
    category = relationship(Category)

    @property
    def serialize(self):
        return {
            'name': self.name,
            'key': self.key,
            'address': self.address,
            'phone': self.phone,
            'description': self.description,
            'image': self.image
        }


engine = create_engine('sqlite:///venue.db')
Base.metadata.create_all(engine)
