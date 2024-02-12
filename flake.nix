{
  description = "Build a cargo project";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
  };

  outputs = inputs:
    with inputs;
    let
      pkgs = import nixpkgs {
        system = "x86_64-linux";
        config.allowUnfree = true;
      };
    in
    {
      devShells.x86_64-linux.default = pkgs.mkShell {
        nativeBuildInputs = with pkgs; [
          (pkgs.python3.withPackages (python-pkgs: with python-pkgs; [
            mako
            packaging
            regex
            requests
            questionary
          ]))
        ];
      };
    };
}
