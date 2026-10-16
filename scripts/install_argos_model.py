from __future__ import annotations

from argostranslate import package


def main() -> None:
    package.update_package_index()
    candidates = [
        item
        for item in package.get_available_packages()
        if item.from_code == "es" and item.to_code == "en"
    ]
    if not candidates:
        raise RuntimeError("No Spanish-to-English Argos model was found.")
    package.install_from_path(candidates[0].download())
    print("Spanish-to-English local translation model installed.")


if __name__ == "__main__":
    main()
