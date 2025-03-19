{ lib
, python3Packages
, fetchFromGitHub
}:
python3Packages.buildPythonApplication {
  pname = "dibbler";
  version = "unstable";
  src = lib.cleanSource ../.;

  format = "pyproject";

  # brother-ql is breaky breaky
  # https://github.com/NixOS/nixpkgs/issues/285234
  dontCheckRuntimeDeps = true;

  nativeBuildInputs = with python3Packages; [ setuptools ];
  propagatedBuildInputs = with python3Packages; [
    brother-ql
    matplotlib
    psycopg2
    python-barcode
    sqlalchemy
  ];
}
