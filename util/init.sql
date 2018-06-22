DROP DATABASE IF EXISTS lincoln;
DROP DATABASE IF EXISTS lincoln_testing;
CREATE USER lincoln WITH PASSWORD 'testing';
CREATE DATABASE lincoln;
GRANT ALL PRIVILEGES ON DATABASE lincoln to lincoln;
-- Create a testing database to be different than dev
CREATE DATABASE lincoln_testing;
GRANT ALL PRIVILEGES ON DATABASE lincoln_testing to lincoln;
\c lincoln
CREATE EXTENSION hstore;
\c lincoln_testing
CREATE EXTENSION hstore;
