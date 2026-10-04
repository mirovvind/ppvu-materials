from pathlib import Path

from src.loaders import check_records, load_items, save_rejected


def main() -> None:
    records = load_items(Path("data/raw/crossref_sample.json"))
    accepted, rejected = check_records(records)
    save_rejected(rejected, Path("data/output/rejected.csv"))
    print(f"Принято: {len(accepted)}, отклонено: {len(rejected)}")


if __name__ == "__main__":
    main()
