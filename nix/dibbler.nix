{ lib
, python3Packages
, fetchFromGitHub
}:
python3Packages.buildPythonApplication {
  pname = "dibbler";
  version = "unstable-2021-09-07";
  src = lib.cleanSource ../.;

  format = "pyproject";

  nativeBuildInputs = with python3Packages; [ setuptools ];
  propagatedBuildInputs = with python3Packages; [
    brother-ql
    matplotlib
    psycopg2
    python-barcode
    sqlalchemy
  ];
}
