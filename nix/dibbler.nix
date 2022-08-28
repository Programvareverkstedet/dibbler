{ lib, python3Packages, fetchFromGitHub
, conf ? ../conf.py
}:

python3Packages.buildPythonApplication {
  pname = "dibbler";
  version = "unstable-2021-09-07";

  format = "other";

  src = lib.cleanSource ../.;

  propagatedBuildInputs = with python3Packages; [
    brother-ql
    sqlalchemy
    psycopg2
    python-barcode
  ];

  preInstall = ''
    libdir=$out/lib/${python3Packages.python.libPrefix}/site-packages
    mkdir -p $out/bin $libdir
  '';

  installPhase = ''
    runHook preInstall

    libdir=$out/lib/${python3Packages.python.libPrefix}/site-packages
    mv * $libdir
    
    cp ${conf} $libdir/

    mv $libdir/text_based.py $out/bin/dibbler

    runHook postInstall
  '';

}
