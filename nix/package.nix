{ lib
, python3Packages
, makeWrapper
, less
}:
let
  pyproject = builtins.fromTOML (builtins.readFile ../pyproject.toml);
in
python3Packages.buildPythonApplication {
  pname = pyproject.project.name;
  version = pyproject.project.version;
  src = lib.cleanSource ../.;

  format = "pyproject";

  # brother-ql is breaky breaky
  # https://github.com/NixOS/nixpkgs/issues/285234
  # dontCheckRuntimeDeps = true;

  nativeBuildInputs = with python3Packages; [
    setuptools
    makeWrapper
  ];
  propagatedBuildInputs = with python3Packages; [
    # brother-ql
    # matplotlib
    psycopg2-binary
    # python-barcode
    sqlalchemy
  ];

  postInstall = ''
    wrapProgram $out/bin/dibbler \
    --prefix PATH : "${lib.makeBinPath [ less ]}"
  '';

  meta = {
    description = "The little kiosk that could";
    mainProgram = "dibbler";
  };
}
