import argparse


def main():
    parser = argparse.ArgumentParser(description="<description>")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    args = parser.parse_args()
    print("Hello from <library_name>!")


if __name__ == "__main__":
    main()
