# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See LICENSE for more details.
#
# Copyright: Red Hat Inc. 2020
# Authors: Cleber Rosa <crosa@redhat.com>

"""
Test requirements module.
"""

import os
import sqlite3

from ....data_dir import get_datafile_path

#: The location of the requirements cache database
CACHE_DATABASE_PATH = get_datafile_path('cache', 'requirements.sqlite')

#: The definition of the database schema
SCHEMA = [
    'CREATE TABLE IF NOT EXISTS requirement_type (requirement_type TEXT UNIQUE)',
    'CREATE TABLE IF NOT EXISTS environment_type (environment_type TEXT UNIQUE)',
    ('CREATE TABLE IF NOT EXISTS environment ('
     'environment_type TEXT,'
     'environment TEXT,'
     'FOREIGN KEY(environment_type) REFERENCES '
     'environment_type(environment_type)'
     ')'),
    ('CREATE UNIQUE INDEX IF NOT EXISTS '
     'environment_idx ON environment (environment, environment_type)'),
    ('CREATE TABLE IF NOT EXISTS requirement ('
     'environment_type TEXT,'
     'environment TEXT,'
     'requirement_type TEXT,'
     'requirement TEXT,'
     'FOREIGN KEY(environment_type) REFERENCES environment(environment_type),'
     'FOREIGN KEY(environment) REFERENCES environment(environment),'
     'FOREIGN KEY(requirement_type) REFERENCES requirement_type(requirement_type)'
     ')'),
    ('CREATE UNIQUE INDEX IF NOT EXISTS requirement_idx ON requirement '
     '(environment_type, environment, requirement_type, requirement)')
]


def _create_requirement_cache_db():
    with sqlite3.connect(CACHE_DATABASE_PATH) as conn:
        cursor = conn.cursor()
        for entry in SCHEMA:
            _ = cursor.execute(entry)
        conn.commit()


def set_requirement(environment_type, environment,
                    requirement_type, requirement):
    if not os.path.exists(CACHE_DATABASE_PATH):
        _create_requirement_cache_db()

    with sqlite3.connect(CACHE_DATABASE_PATH) as conn:
        cursor = conn.cursor()
        sql = "INSERT OR IGNORE INTO environment_type VALUES (?)"
        cursor.execute(sql, (environment_type, ))
        sql = "INSERT OR IGNORE INTO environment VALUES (?, ?)"
        cursor.execute(sql, (environment_type, environment))
        sql = "INSERT OR IGNORE INTO requirement_type VALUES (?)"
        cursor.execute(sql, (requirement_type, ))
        sql = "INSERT OR IGNORE INTO requirement VALUES (?, ?, ?, ?)"
        cursor.execute(sql, (environment_type, environment,
                             requirement_type, requirement))
    conn.commit()


def get_requirement(environment_type, environment,
                    requirement_type, requirement):
    if not os.path.exists(CACHE_DATABASE_PATH):
        return False

    sql = ("SELECT COUNT(*) FROM requirement WHERE ("
           "environment_type = ? AND "
           "environment = ? AND "
           "requirement_type = ? AND "
           "requirement = ?)")

    with sqlite3.connect(CACHE_DATABASE_PATH) as conn:
        cursor = conn.cursor()
        result = cursor.execute(sql, (environment_type, environment,
                                      requirement_type, requirement))
        row = result.fetchone()
        if row is not None:
            return row[0] == 1
    return False
