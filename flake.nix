{
  description = "Static site renderer for Ascone (Python, Mistune, Jinja2, Sass).";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-25.05";

  outputs = { self, nixpkgs }:
    let
      supportedSystems = [
        "x86_64-linux"
        "aarch64-linux"
      ];

      forAllSystems = nixpkgs.lib.genAttrs supportedSystems;

      makeDevShell =
        { pkgs }:
        let
          python = pkgs.python3;
          pythonEnv = python.withPackages (ps: with ps; [
            beautifulsoup4
            jinja2
            libsass
            mistune
            python-frontmatter
          ]);

          # Walk up from the current directory to the project root. We use
          # the live working tree (not the Nix store snapshot) because
          # _content/ and _dist/ are gitignored and would be missing there.
          findRoot = ''
            dir=$(pwd)
            while [ "$dir" != "/" ] && [ ! -d "$dir/ascone-build" ]; do
              dir=$(dirname "$dir")
            done
            if [ ! -d "$dir/ascone-build" ]; then
              echo "error: could not find project root (no ascone-build/ above $(pwd))" >&2
              exit 1
            fi
            cd "$dir"
          '';

          mkCmd =
            name: text:
            pkgs.writeShellApplication {
              inherit name;
              text = ''
                ${findRoot}
                ${text}
              '';
            };

          buildCmd = mkCmd "build" "exec python ascone-build/";

          # Extra args are passed to the server (e.g. serve -p 8080).
          serveCmd = mkCmd "serve" ''
            if [ ! -d _dist ]; then
              echo "error: no _dist/ found — run 'build' first" >&2
              exit 1
            fi
            exec python -m http.server --directory _dist "$@"
          '';
        in
        pkgs.mkShell {
          name = "ascone-renderer";
          packages = [
            pythonEnv
            buildCmd
            serveCmd
          ];
          shellHook = ''
            echo "  /\_"
            echo "（ﾟ､ ｡\`7  ascone-renderer devshell!! :3"
            echo " {\`  ~ \   )"
            echo "  ),),\_,)/"
            echo ""
            echo "run 'build' to render the site, 'serve' to preview it"
          '';
        };
    in
    {
      devShell = forAllSystems (
        system: makeDevShell {
          pkgs = nixpkgs.legacyPackages.${system};
        }
      );
    };
}
