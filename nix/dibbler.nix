{ lib
, fetchFromGitHub
, buildPythonApplication
, setuptools
, brother-ql
, matplotlib
, psycopg2
, python-barcode
, sqlalchemy
}:

buildPythonApplication {
  pname = "dibbler";
  version = "0-unstable-2021-09-07";
  pyproject = true;

  src = lib.cleanSource ../.;

  built-system = [ setuptools ];
  dependencies = [
    brother-ql#-next
    matplotlib
    psycopg2
    python-barcode
    sqlalchemy
  ];
}
