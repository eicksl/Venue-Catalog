from sqlalchemy import Column, ForeignKey, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine


Base = declarative_base()


class User(Base):
    __tablename__ = 'user'

    key = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False)
    email = Column(String(250), nullable=False)
    sub = Column(String(250))  # Unique google account identifier
    fb_id = Column(String(250))  # Unique facebook account identifier
    venues = relationship('Venue', back_populates='user')


class Category(Base):
    __tablename__ = 'category'

    key = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    venues = relationship('Venue', back_populates='category')

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
    category_key = Column(Integer, ForeignKey('category.key'), nullable=False)
    category = relationship('Category', back_populates='venues')
    user_key = Column(Integer, ForeignKey('user.key'), nullable=False)
    user = relationship('User', back_populates='venues')

    @property
    def serialize(self):
        return {
            'name': self.name,
            'key': self.key,
            'address': self.address,
            'phone': self.phone,
            'description': self.description,
            'image': self.image,
            'category_key': self.category_key
        }


class Activity(Base):
    __tablename__ = 'activity'

    key = Column(Integer, primary_key=True)
    user_name = Column(String(50), nullable=False)
    action = Column(String(10), nullable=False)
    venue_key = Column(Integer)
    venue_name = Column(String(250), nullable=False)
    category_key = Column(Integer)
    datetime = Column(DateTime, nullable=False)

    @property
    def serialize(self):
        return {
            'user_name': self.user_name,
            'action': self.action,
            'venue_name': self.venue_name,
            'venue_key': self.venue_key,
            'category_key': self.category_key,
            'datetime': self.datetime
        }


engine = create_engine('postgresql://cataloguser:password@localhost/catalogdb')
Base.metadata.create_all(engine)
