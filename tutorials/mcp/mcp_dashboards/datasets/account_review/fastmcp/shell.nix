# Ephemeral SecretSpec from nixpkgs — no profile install.
#   nix-shell
#   direnv allow   # with .envrc → use nix
#
# Keep using the system `op` binary for 1Password desktop CLI integration.
{
  pkgs ? import <nixpkgs> { },
}:
pkgs.mkShellNoCC {
  packages = [ pkgs.secretspec ];
}
