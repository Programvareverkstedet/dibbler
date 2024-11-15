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
  version = "0.0.0";
  pyproject = true;

  src = lib.cleanSource ../.;

  build-system = [ setuptools ];
  dependencies = [
    # we override pname to satisfy mkPythonEditablePackage
    (brother-ql.overridePythonAttrs { pname = "brother-ql-next"; })
    matplotlib
    psycopg2
    python-barcode
    sqlalchemy
  ];
}
