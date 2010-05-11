#!/usr/bin/python
import db

db.Base.metadata.create_all(db.engine)
