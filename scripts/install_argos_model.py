from __future__ import annotations

from argostranslate import package


def main() -> None:
    package.update_package_index()
    available = package.get_available_packages()
    installed = {(item.from_code, item.to_code) for item in package.get_installed_packages()}
    required = [("es", "en"), ("en", "es"), ("en", "fr"), ("en", "ar")]
    for source, target in required:
        if (source, target) in installed:
            continue
        candidate = next(
            (
                item
                for item in available
                if item.from_code == source and item.to_code == target
            ),
            None,
        )
        if candidate is None:
            raise RuntimeError(f"No {source}-to-{target} Argos model was found.")
        package.install_from_path(candidate.download())
        print(f"Installed local translation model: {source} -> {target}")
    print("All local translation models are ready.")


if __name__ == "__main__":
    main()
