{
  description = "account-review MCP — SecretSpec (1Password) for Azure deploy";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs =
    { nixpkgs, ... }:
    let
      systems = [
        "aarch64-darwin"
        "x86_64-darwin"
        "aarch64-linux"
        "x86_64-linux"
      ];
      forAllSystems = nixpkgs.lib.genAttrs systems;
    in
    {
      # Prefer shell.nix + direnv for day-to-day use (works before flake files are
      # committed). This flake is optional: nix develop .  (after git add).
      #
      # Keep using the system `op` binary (setgid / desktop integration).
      # Do not add pkgs._1password-cli here — it breaks 1Password CLI unlock.
      devShells = forAllSystems (
        system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
        in
        {
          default = pkgs.mkShellNoCC {
            packages = [ pkgs.secretspec ];
            shellHook = ''
              echo "secretspec $(secretspec --version 2>/dev/null || echo '?') from nixpkgs"
              echo "op: $(command -v op || echo 'not found — enable 1Password CLI desktop integration')"
              echo ""
              echo "  secretspec check --profile deploy"
              echo "  secretspec run --profile deploy --reason \"Deploy account-review MCP\" -- ./deploy.sh"
            '';
          };
        }
      );
    };
}
