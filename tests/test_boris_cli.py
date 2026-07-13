import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def run_command(command):
    return subprocess.run(command, cwd=PROJECT_ROOT, capture_output=True, text=True)


def test_cli_version_runs_as_script():
    result = run_command([sys.executable, str(PROJECT_ROOT / "boris" / "boris_cli.py"), "-v"])
    assert result.returncode == 0
    assert result.stdout.startswith("version ")


def test_cli_version_runs_as_module():
    result = run_command([sys.executable, "-m", "boris.boris_cli", "-v"])
    assert result.returncode == 0
    assert result.stdout.startswith("version ")


def test_cli_help_runs_as_script():
    result = run_command([sys.executable, str(PROJECT_ROOT / "boris" / "boris_cli.py"), "-h"])
    assert result.returncode == 0
    assert "BORIS CLI" in result.stdout
    assert "--command" in result.stdout
    assert "--nosplashscreen" not in result.stdout


def test_cli_help_runs_as_module():
    result = run_command([sys.executable, "-m", "boris.boris_cli", "-h"])
    assert result.returncode == 0
    assert "BORIS CLI" in result.stdout
    assert "--command" in result.stdout
    assert "--nosplashscreen" not in result.stdout


def test_cli_help_runs_with_uv_entrypoint():
    result = run_command(["uv", "run", "boris_cli.py", "-h"])
    assert result.returncode == 0
    assert "BORIS CLI" in result.stdout
    assert "--command" in result.stdout
    assert "--nosplashscreen" not in result.stdout


def test_importing_boris_does_not_parse_cli_arguments():
    result = run_command([sys.executable, "-c", "import sys; sys.argv = ['probe', '-h']; import boris; print(boris.name)"])
    assert result.returncode == 0
    assert result.stdout.strip() == "BORIS"
    assert result.stderr == ""
