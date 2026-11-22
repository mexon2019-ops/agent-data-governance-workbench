#!/bin/bash
set -euo pipefail

: "${MYSQL_TEST_READER_PASSWORD:?MYSQL_TEST_READER_PASSWORD must be set}"

# Escape single quotes before embedding the password in a SQL string literal.
escaped_password="$(printf '%s' "$MYSQL_TEST_READER_PASSWORD" | sed "s/'/''/g")"

mysql --protocol=socket -uroot -p"$MYSQL_ROOT_PASSWORD" "$MYSQL_DATABASE" <<SQL
CREATE USER IF NOT EXISTS 'metadata_reader'@'%' IDENTIFIED BY '$escaped_password';
ALTER USER 'metadata_reader'@'%' IDENTIFIED BY '$escaped_password';
GRANT SELECT, SHOW VIEW ON `$MYSQL_DATABASE`.* TO 'metadata_reader'@'%';
FLUSH PRIVILEGES;
SQL
