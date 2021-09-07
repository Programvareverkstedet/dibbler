{ lib, python3Packages, fetchFromGitHub }:

let
  packbits = python3Packages.buildPythonPackage rec {
    pname = "packbits";
    version = "0.6";

    src = python3Packages.fetchPypi {
      inherit pname version;
      sha256 = "0d7hzxxhyv6x160dnfjrdpyaz0239300cpl3za6aq12fnc5kfsxw";
    };
  };
  brother-ql = python3Packages.buildPythonPackage rec {
    pname = "brother-ql";
    version = "0.9.4";

    src = python3Packages.fetchPypi {
      pname = "brother_ql";
      inherit version;
      sha256 = "0q469rhkrjyhhplvs7j2hdsbnvpp0404fzrr0k1cj4ph76h5fp0z";
    };

    propagatedBuildInputs = with python3Packages; [
      click
      future
      packbits
      pillow
      pyusb
      attrs
    ];
  };
  python-barcode = python3Packages.buildPythonPackage rec {
    pname = "python-barcode";
    version = "0.13.1";

    src = python3Packages.fetchPypi {
      inherit pname version;
      sha256 = "0lmj4cp9g38hyb15yfyndarw5xhqzyac48g5gdvnkng94jma9yzs";
    };

    propagatedBuildInputs = with python3Packages; [ pillow setuptools_scm ];

    doCheck = false;

    #checkInputs = with python3Packages; [ tox ];
  };
in
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

    mv $libdir/text_based.py $out/bin/text_based.py

    runHook postInstall
  '';

}
