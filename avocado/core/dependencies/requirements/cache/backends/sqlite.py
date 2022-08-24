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

from avocado.core.data_dir import get_datafile_path

#: The location of the requirements cache database
CACHE_DATABASE_PATH = get_datafile_path("cache", "requirements.sqlite")

sqlite3.register_adapter(bool, int)
sqlite3.register_converter("BOOLEAN", lambda v: bool(int(v)))

#: The definition of the database schema
SCHEMA = [
    "CREATE TABLE IF NOT EXISTS requirement_type (requirement_type TEXT UNIQUE)",
    "CREATE TABLE IF NOT EXISTS environment_type (environment_type TEXT UNIQUE)",
    (
        "CREATE TABLE IF NOT EXISTS environment ("
        "environment_type TEXT,"
        "environment TEXT,"
        "FOREIGN KEY(environment_type) REFERENCES "
        "environment_type(environment_type)"
        ")"
    ),
    (
        "CREATE UNIQUE INDEX IF NOT EXISTS "
        "environment_idx ON environment (environment, environment_type)"
    ),
    (
        "CREATE TABLE IF NOT EXISTS requirement ("
        "environment_type TEXT,"
        "environment TEXT,"
        "requirement_type TEXT,"
        "requirement TEXT,"
        "saved BOOLEAN,"
        "FOREIGN KEY(environment_type) REFERENCES environment(environment_type),"
        "FOREIGN KEY(environment) REFERENCES environment(environment),"
        "FOREIGN KEY(requirement_type) REFERENCES requirement_type(requirement_type)"
        ")"
    ),
    (
        "CREATE UNIQUE INDEX IF NOT EXISTS requirement_idx ON requirement "
        "(environment_type, environment, requirement_type, requirement)"
    ),
]


def _create_requirement_cache_db():
    os.makedirs(os.path.dirname(CACHE_DATABASE_PATH), exist_ok=True)
    with sqlite3.connect(CACHE_DATABASE_PATH) as conn:
        cursor = conn.cursor()
        for entry in SCHEMA:
            _ = cursor.execute(entry)
        conn.commit()


def set_requirement(
    environment_type, environment, requirement_type, requirement, saved=True
):
    if not os.path.exists(CACHE_DATABASE_PATH):
        _create_requirement_cache_db()

    with sqlite3.connect(CACHE_DATABASE_PATH) as conn:
        cursor = conn.cursor()
        sql = "INSERT OR IGNORE INTO environment_type VALUES (?)"
        cursor.execute(sql, (environment_type,))
        sql = "INSERT OR IGNORE INTO environment VALUES (?, ?)"
        cursor.execute(sql, (environment_type, environment))
        sql = "INSERT OR IGNORE INTO requirement_type VALUES (?)"
        cursor.execute(sql, (requirement_type,))
        sql = "INSERT OR IGNORE INTO requirement VALUES (?, ?, ?, ?, ?)"
        cursor.execute(
            sql, (environment_type, environment, requirement_type, requirement, saved)
        )
        conn.commit()


def is_requirement_in_cache(
    environment_type, environment, requirement_type, requirement
):
    """Checks if requirement is in cache.

    :rtype: True if requirement is in cache
            False if requirement is not in cache
            None if requirement is in cache but it is not saved yet.
    """
    if not os.path.exists(CACHE_DATABASE_PATH):
        return False

    sql = (
        "SELECT r.saved FROM requirement r WHERE ("
        "environment_type = ? AND "
        "environment = ? AND "
        "requirement_type = ? AND "
        "requirement = ?)"
    )

    with sqlite3.connect(CACHE_DATABASE_PATH) as conn:
        cursor = conn.cursor()
        result = cursor.execute(
            sql, (environment_type, environment, requirement_type, requirement)
        )
        row = result.fetchone()
        if row is not None:
            if row[0]:
                return True
            return None
    return False


def is_environment_prepared(environment):
    """Checks if environment has all requirements saved."""

    if not os.path.exists(CACHE_DATABASE_PATH):
        return False

    sql = (
        "SELECT COUNT(*) FROM requirement r JOIN "
        "environment e ON e.environment = r.environment "
        "WHERE (r.environment = ? AND "
        "r.saved = 0)"
    )

    with sqlite3.connect(
        CACHE_DATABASE_PATH, detect_types=sqlite3.PARSE_DECLTYPES
    ) as conn:
        cursor = conn.cursor()
        result = cursor.execute(sql, (environment,))

        row = result.fetchone()
        if row is not None:
            return row[0] == 0
    return False


def update_environment(environment_type, old_environment, new_environment):
    """Updates environment information for each requirement in one environment.

    It will remove the old environment and add the new one to the cache.

    :param environment_type: Type of fetched environment
    :type environment_type: str
    :param old_environment: Environment which should be updated
    :type environment: str
    :param new_environment: Environment, which will be a reimbursement for the
                            old one.
    :type environment: str
    """
    if not os.path.exists(CACHE_DATABASE_PATH):
        return False

    with sqlite3.connect(CACHE_DATABASE_PATH) as conn:
        cursor = conn.cursor()
        sql = "INSERT OR IGNORE INTO environment VALUES (?, ?)"
        cursor.execute(sql, (environment_type, new_environment))

        sql = (
            "UPDATE requirement SET environment = ? WHERE ("
            "environment_type = ? AND "
            "environment = ? )"
        )

        cursor.execute(sql, (new_environment, environment_type, old_environment))

        sql = (
            "DELETE FROM environment WHERE ("
            "environment_type = ? AND "
            "environment = ? )"
        )

        cursor.execute(sql, (environment_type, old_environment))
        conn.commit()


def update_requirement_status(
    environment_type, environment, requirement_type, requirement, new_status
):
    """Updates status of selected requirement in cache.

    The status has two values, save=True or not_save=False.

    :param environment_type: Type of fetched environment
    :type environment_type: str
    :param environment: Environment where the requirement is
    :type environment: str
    :param requirement_type: Type of the requirement in environment
    :type requirement_type: str
    :param requirement: Name of requirement
    :type requirement: str
    :param new_status: Requirement status which will be updated
    :type new_status: bool
    """

    if not os.path.exists(CACHE_DATABASE_PATH):
        return False

    sql = (
        "UPDATE requirement SET saved = ? WHERE ("
        "environment_type = ? AND "
        "environment = ? AND "
        "requirement_type = ? AND "
        "requirement = ?)"
    )

    with sqlite3.connect(CACHE_DATABASE_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            sql,
            (new_status, environment_type, environment, requirement_type, requirement),
        )
        conn.commit()

    return True


def delete_environment(environment_type, environment):
    """Deletes environment with all its requirements from cache.

    :param environment_type: Type of environment
    :type environment_type: str
    :param environment: Environment which will be deleted
    :type environment: str
    """

    if not os.path.exists(CACHE_DATABASE_PATH):
        return False

    with sqlite3.connect(CACHE_DATABASE_PATH) as conn:
        sql = (
            "DELETE FROM requirement WHERE ("
            "environment_type = ? AND "
            "environment = ? )"
        )
        cursor = conn.cursor()
        cursor.execute(sql, (environment_type, environment))
        sql = (
            "DELETE FROM environment WHERE ("
            "environment_type = ? AND "
            "environment = ? )"
        )
        cursor.execute(sql, (environment_type, environment))
        conn.commit()


def delete_requirement(environment_type, environment, requirement_type, requirement):
    """Deletes requirement from cache.

    :param environment_type: Type of environment
    :type environment_type: str
    :param environment: Environment where the requirement is.
    :type environment: str
    :param requirement_type: Type of the requirement in environment
    :type requirement_type: str
    :param requirement: Name of requirement which will be deleted
    :type requirement: str
    """

    if not os.path.exists(CACHE_DATABASE_PATH):
        return False

    with sqlite3.connect(CACHE_DATABASE_PATH) as conn:
        sql = (
            "DELETE FROM requirement WHERE ("
            "environment_type = ? AND "
            "environment = ? AND "
            "requirement_type = ? AND "
            "requirement = ?)"
        )
        cursor = conn.cursor()
        cursor.execute(
            sql, (environment_type, environment, requirement_type, requirement)
        )
        conn.commit()


def get_all_environments_with_requirement(
    environment_type, requirement_type, requirement
):
    """Fetches all environments with selected requirement from cache.

    :param environment_type: Type of fetched environment
    :type environment_type: str
    :param requirement_type: Type of the requirement in environment
    :type requirement_type: str
    :param requirement: Name of requirement
    :type requirement: str
    :return: Dict with all environments which has selected requirements.

    """
    requirements = {}
    if not os.path.exists(CACHE_DATABASE_PATH):
        return requirements

    environment_select = (
        "SELECT e.environment FROM requirement r JOIN "
        "environment e ON e.environment = r.environment "
        "WHERE (r.environment_type = ? AND "
        "r.requirement_type = ? AND "
        "r.requirement = ?)"
    )
    sql = (
        f"SELECT r.environment, r.requirement_type, r.requirement "
        f"FROM requirement AS r, ({environment_select}) AS e "
        f"WHERE r.environment = e.environment"
    )

    with sqlite3.connect(
        CACHE_DATABASE_PATH, detect_types=sqlite3.PARSE_DECLTYPES
    ) as conn:
        cursor = conn.cursor()
        result = cursor.execute(sql, (environment_type, requirement_type, requirement))

        for row in result.fetchall():
            if row[0] in requirements:
                requirements[row[0]].append((row[1], row[2]))
            else:
                requirements[row[0]] = [(row[1], row[2])]
    return requirements


def get_all_requirements():
    """Fetches all requirements from database.

    :return: Dict with all environments which has requirements.

    """
    requirements = {}
    if not os.path.exists(CACHE_DATABASE_PATH):
        return requirements

    sql = "SELECT * FROM requirement"

    with sqlite3.connect(
        CACHE_DATABASE_PATH, detect_types=sqlite3.PARSE_DECLTYPES
    ) as conn:
        cursor = conn.cursor()
        result = cursor.execute(sql)

        for row in result.fetchall():
            environment_type = row[0]
            if environment_type not in requirements:
                requirements[environment_type] = []
            requirements[environment_type].append(
                {
                    "environment": row[1],
                    "requirement_type": row[2],
                    "requirement": row[3],
                }
            )
    return requirements
