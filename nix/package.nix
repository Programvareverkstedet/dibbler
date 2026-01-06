{ lib
, sourceInfo
, python3Packages
, makeWrapper
, less
}:
let
  pyproject = builtins.fromTOML (builtins.readFile ../pyproject.toml);
in
python3Packages.buildPythonApplication {
  pname = pyproject.project.name;
  version = "0.1";
  src = lib.cleanSource ../.;

  format = "pyproject";

  # brother-ql is breaky breaky
  # https://github.com/NixOS/nixpkgs/issues/285234
  # dontCheckRuntimeDeps = true;

  env.SETUPTOOLS_SCM_PRETEND_METADATA = (x: "{${x}}") (lib.concatStringsSep ", " [
    "node=\"${sourceInfo.rev or (lib.substring 0 64 sourceInfo.dirtyRev)}\""
    "node_date=${lib.substring 0 4 sourceInfo.lastModifiedDate}-${lib.substring 4 2 sourceInfo.lastModifiedDate}-${lib.substring 6 2 sourceInfo.lastModifiedDate}"
    "dirty=${if sourceInfo ? dirtyRev then "true" else "false"}"
  ]);

  nativeBuildInputs = with python3Packages; [
    makeWrapper
    setuptools
    setuptools-scm
  ];
  propagatedBuildInputs = with python3Packages; [
    # brother-ql
    # matplotlib
    psycopg2-binary
    # python-barcode
    sqlalchemy
  ];

  pythonImportsCheck = [];

  doCheck = true;
  nativeCheckInputs = with python3Packages; [
    pytest
    pytestCheckHook
    sqlparse
    pytest-html
    pytest-cov
    pytest-benchmark
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
