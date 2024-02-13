{
  description = "Build a cargo project";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
    systems.url = "github:nix-systems/default";
  };

  outputs = inputs:
    with inputs;
    let
      eachSystem = nixpkgs.lib.genAttrs (import systems);
    in
    {
      devShells = eachSystem (system:
        let
          pkgs = import nixpkgs { inherit system; };
        in
        {
          default = pkgs.mkShell {
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
        });

      packages = eachSystem (system:
        let
          pkgs = import nixpkgs { inherit system; };
        in
        {
          default = pkgs.writeShellApplication {
            name = "juice";
            runtimeInputs = [
              (pkgs.python3.withPackages (python-pkgs: with python-pkgs; [
                mako
                packaging
                regex
                requests
                questionary
              ]))
            ];

            text = ''
              pushd ${./.} > /dev/null
              python3 juicebar.py "$@"
              popd
            '';
          };
        });
    };
}
