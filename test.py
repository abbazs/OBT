import click
from click.testing import CliRunner
import run
from src.log import print_exception

def test_obt():
    print("Started testing")
    runner = CliRunner()
    result = runner.invoke(
        run.cli,
        ["-mitr", 10, "-ssaf", 0.95, "-noad", 1, "ssrnd", "-nexp", 3, "-ndays", 45],
    )
    print(f"exe_info : {result.exc_info}")
    print(f"exception : {result.exception}")
    print(f"stdout : {result.stdout}")
    print(f"Output : {result.output}")
    print(f"Exit code : {result.exit_code}")
    assert result.exception is TypeError

    assert result.exit_code > 0
    

if __name__ == "__main__":
    test_obt()