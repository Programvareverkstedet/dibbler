#!/usr/bin/python
from .models.db import db

db.Base.metadata.create_all(db.engine)
