{ pkgs ? import <nixpkgs> {} }:

let
  pp = pkgs.python37Packages;
in pkgs.mkShell rec {
  name = "pythiaEnv";
  venvDir = "./.venv";
  buildInputs = [
    pkgs.python37
    pkgs.pipenv
    pp.venvShellHook 
    pp.poetry

    pkgs.libspatialite
    pkgs.libspatialindex

    pkgs.black
    pp.bandit
  ];

  preShellHook = ''
    echo "${pkgs.libspatialindex}/lib"
    export DYLD_FALLBACK_LIBRARY_PATH="${pkgs.libspatialindex}/lib"
  '';
  postVenvCreation = ''
    unset SOURCE_DATE_EPOCH
    pipenv install
  '';

  postShellHook = ''
    unset SOURCE_DATE_EPOCH
  '';
}
