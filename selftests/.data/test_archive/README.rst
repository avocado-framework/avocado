Test Archive Files
=================

This directory contains "golden" archive files used for testing the archive functionality in Avocado.

Purpose
-------

Instead of creating archive files at runtime during tests (which consumes resources, adds dependencies, and can be error-prone), these pre-created archives serve as reliable test fixtures.

Archive Types
------------

The directory includes various types of archives:

- **ZIP archives**: ``archive.zip``, ``zipfile`` (without extension), ``test_archive__symlinks.zip``
- **TAR archives**: ``archive.tar``, ``tarfile`` (without extension)
- **GZIP files**: ``avocado.gz``, ``test_file.gz``, ``gzipfile`` (without extension)
- **XZ files**: ``avocado.xz``, ``test_file.xz``, ``xzfile`` (without extension)
- **ZSTD files**: ``avocado.zst``
- **BZIP2 files**: ``empty.tar.bz2``

Metadata Files
-------------

Each archive has an associated ``.metadata`` file (e.g., ``archive.tar.metadata``) that documents the contents of the archive. The metadata is in JSON format and includes:

.. code-block:: json

    {
      "members": [["filename", "hash"]]
    }

The "members" field contains a list of files in the archive along with their SHA-256 hash values, which are used to verify the integrity of the files. For symlinks, the hash is replaced with a "symlink:" prefix followed by the target path.

These metadata files serve multiple purposes:

1. Documentation for the archive contents
2. Verification that the expected files exist in the archive
3. Verification that the file contents match the expected hash values

The tests extract the archives and verify both the presence of the expected files and that their hash values match those specified in the metadata.

Usage in Tests
-------------

These archives are used in the ``avocado/selftests/unit/utils/test_archive.py`` file to test the archive functionality. The tests verify that the archives can be properly detected, opened, and extracted.

Adding New Archives
-----------------

When adding new test archives:

1. Create the archive with the desired content
2. Add it to this directory
3. Create a metadata file to document its contents
4. Update the tests to use the new archive

This approach ensures consistent and reliable testing without runtime dependencies.
