"""End-to-end CLI tests — invoke telos as subprocess."""

import os
import subprocess
import sys
import time
from pathlib import Path

import pytest


VAULT_PATH = Path("/Users/mpaz/obsidian")
INTERSTITIAL_DIR = VAULT_PATH / "50-log/interstitial"
KAIROS_PACK = Path(__file__).resolve().parent.parent.parent / "packs" / "kairos"
API_KEY_FILE = Path.home() / ".config/telos/.env"


def _has_api_key() -> bool:
    """Check if ANTHROPIC_API_KEY is available."""
    if os.environ.get("ANTHROPIC_API_KEY"):
        return True
    if API_KEY_FILE.exists():
        return "ANTHROPIC_API_KEY" in API_KEY_FILE.read_text()
    return False


def _has_claude() -> bool:
    """Check if claude binary is on PATH."""
    return subprocess.run(
        ["which", "claude"], capture_output=True
    ).returncode == 0


def _has_vault() -> bool:
    """Check if the Obsidian vault exists (for working_dir)."""
    return VAULT_PATH.is_dir()


requires_real_env = pytest.mark.skipif(
    not (_has_api_key() and _has_claude() and _has_vault()),
    reason="Requires ANTHROPIC_API_KEY, claude binary, and Obsidian vault",
)


def run_telos(
    *args: str,
    env_override: dict | None = None,
    cwd: str | None = None,
    timeout: int = 120,
) -> subprocess.CompletedProcess:
    """Run the telos CLI as a subprocess."""
    env = dict(os.environ)
    if env_override:
        env.update(env_override)
    return subprocess.run(
        [sys.executable, "-m", "telos.main"] + list(args),
        capture_output=True,
        text=True,
        env=env,
        cwd=cwd,
        timeout=timeout,
    )


def run_telos_isolated(
    *args: str,
    env_override: dict | None = None,
    cwd: str | None = None,
) -> subprocess.CompletedProcess:
    """Run telos with API key stripped — for tests that don't need real routing."""
    env = dict(os.environ)
    if env_override:
        env.update(env_override)
    env.pop("ANTHROPIC_API_KEY", None)
    return subprocess.run(
        [sys.executable, "-m", "telos.main"] + list(args),
        capture_output=True,
        text=True,
        env=env,
        cwd=cwd,
    )


@pytest.fixture
def isolated_env(tmp_path):
    """Return env vars that isolate telos config/data/skills to tmp_path."""
    config_dir = tmp_path / "config"
    data_dir = tmp_path / "data"
    skills_dir = tmp_path / "skills_home"
    config_dir.mkdir()
    data_dir.mkdir()
    skills_dir.mkdir()
    return {
        "TELOS_CONFIG_DIR": str(config_dir),
        "TELOS_DATA_DIR": str(data_dir),
        "TELOS_SKILLS_DIR": str(skills_dir),
    }


@pytest.fixture
def configured_env(isolated_env, tmp_path):
    """Return env with agents discovered from skills dir."""
    config_dir = Path(isolated_env["TELOS_CONFIG_DIR"])
    skills_home = Path(isolated_env["TELOS_SKILLS_DIR"])

    # Set up kairos agent pack in skills dir
    pack = skills_home / "kairos"
    skills = pack / "skills"
    (skills / "kickoff").mkdir(parents=True)
    (skills / "kickoff" / "SKILL.md").write_text("---\ndescription: Morning orientation\n---\n# Kickoff\nStart the day")
    (skills / "shutdown").mkdir()
    (skills / "shutdown" / "SKILL.md").write_text("---\ndescription: End of day wrap-up\n---\n# Shutdown\nWrap up")
    (skills / "weekly-summary").mkdir()
    (skills / "weekly-summary" / "SKILL.md").write_text("---\ndescription: Weekly summary report\n---\n# Weekly Summary\nGenerate report")
    (pack / "agent.toml").write_text(f'name = "kairos"\ndescription = "Personal productivity"\nworking_dir = "{tmp_path}"\n')

    return isolated_env


@pytest.fixture
def real_env(tmp_path):
    """Return env that installs the kairos pack and uses the real vault as working_dir."""
    env = {}
    # Load API key from .env file if not already in environment
    if not os.environ.get("ANTHROPIC_API_KEY") and API_KEY_FILE.exists():
        for line in API_KEY_FILE.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                env[key.strip()] = value.strip()

    # Install kairos pack into isolated dirs
    config_dir = tmp_path / "config"
    data_dir = tmp_path / "data"
    skills_dir = tmp_path / "skills_home"
    config_dir.mkdir()
    data_dir.mkdir()
    skills_dir.mkdir()
    env["TELOS_CONFIG_DIR"] = str(config_dir)
    env["TELOS_DATA_DIR"] = str(data_dir)
    env["TELOS_SKILLS_DIR"] = str(skills_dir)

    # Install the pack
    result = subprocess.run(
        [sys.executable, "-m", "telos.main", "install", str(KAIROS_PACK)],
        capture_output=True, text=True,
        env={**os.environ, **env},
    )
    assert result.returncode == 0, f"Failed to install kairos pack: {result.stderr}"

    return env


# ---------------------------------------------------------------------------
# Isolated tests (no real API calls, no real claude)
# ---------------------------------------------------------------------------

class TestHelpAndBasics:
    """Basic CLI behavior tests."""

    def test_help_exits_zero(self):
        result = run_telos_isolated("--help")
        assert result.returncode == 0
        assert "Personal agent runtime" in result.stdout

    def test_no_args_exits_cleanly(self):
        result = run_telos_isolated()
        assert result.returncode == 0


class TestDryRun:
    """Tests for --dry-run mode."""

    def test_dry_run_matches_skill(self, configured_env):
        result = run_telos_isolated("--dry-run", "kickoff", env_override=configured_env)
        assert result.returncode == 0
        assert "kickoff" in result.stdout.lower()

    def test_dry_run_does_not_execute(self, configured_env):
        result = run_telos_isolated("--dry-run", "kickoff", env_override=configured_env)
        assert result.returncode == 0


class TestNoConfig:
    """Tests when no config exists."""

    def test_no_config_prints_init_hint(self, isolated_env):
        result = run_telos_isolated("list-skills", env_override=isolated_env)
        assert result.returncode != 0
        assert "init" in result.stdout.lower() or "init" in result.stderr.lower()


class TestAgentFlag:
    """Tests for --agent flag."""

    def test_agent_flag_selects_agent(self, configured_env, tmp_path):
        skills_home = Path(configured_env["TELOS_SKILLS_DIR"])

        # Set up gmail agent in skills dir
        gmail_pack = skills_home / "gmail"
        gmail_skills = gmail_pack / "skills"
        (gmail_skills / "check-email").mkdir(parents=True)
        (gmail_skills / "check-email" / "SKILL.md").write_text("---\ndescription: Check email\n---\n# Check\nCheck it")
        (gmail_pack / "agent.toml").write_text('name = "gmail"\ndescription = "Gmail"\nworking_dir = "."\n')

        result = run_telos_isolated("--agent", "gmail", "--dry-run", "check-email", env_override=configured_env)
        assert result.returncode == 0
        assert "check-email" in result.stdout.lower()


class TestVerbose:
    """Tests for --verbose flag."""

    def test_verbose_shows_routing_details(self, configured_env):
        result = run_telos_isolated("--verbose", "--dry-run", "kickoff", env_override=configured_env)
        assert result.returncode == 0
        assert "kairos" in result.stdout.lower() or "kairos" in result.stderr.lower()


class TestListSkills:
    """Tests for list-skills command."""

    def test_list_skills_prints_table(self, configured_env):
        result = run_telos_isolated("list-skills", env_override=configured_env)
        assert result.returncode == 0
        assert "kickoff" in result.stdout.lower()
        assert "shutdown" in result.stdout.lower()

    def test_list_skills_with_agent_flag(self, configured_env):
        result = run_telos_isolated("list-skills", "--agent", "kairos", env_override=configured_env)
        assert result.returncode == 0
        assert "kickoff" in result.stdout.lower()


class TestAgentsCommand:
    """Tests for the agents command."""

    def test_agents_prints_table(self, configured_env):
        result = run_telos_isolated("agents", env_override=configured_env)
        assert result.returncode == 0
        assert "kairos" in result.stdout.lower()


class TestInstallCommand:
    """Tests for the install command."""

    def test_install_agent_pack(self, isolated_env, tmp_path):
        pack_dir = tmp_path / "gmail-pack"
        pack_dir.mkdir()
        (pack_dir / "agent.toml").write_text('name = "gmail"\ndescription = "Gmail agent"\nworking_dir = "."\n')
        skills = pack_dir / "skills"
        skills.mkdir()
        (skills / "check").mkdir()
        (skills / "check" / "SKILL.md").write_text("---\ndescription: Check\n---\nBody")

        result = run_telos_isolated("install", str(pack_dir), env_override=isolated_env)
        assert result.returncode == 0
        assert "gmail" in result.stdout.lower()

        # Verify installed to skills dir
        skills_home = Path(isolated_env["TELOS_SKILLS_DIR"])
        assert (skills_home / "gmail" / "skills" / "check" / "SKILL.md").exists()


class TestUninstallCommand:
    """Tests for the uninstall command."""

    def test_uninstall_installed_agent(self, isolated_env, tmp_path):
        pack_dir = tmp_path / "gmail-pack"
        pack_dir.mkdir()
        (pack_dir / "agent.toml").write_text('name = "gmail"\ndescription = "Gmail"\nworking_dir = "."\n')
        skills = pack_dir / "skills"
        skills.mkdir()
        (skills / "check").mkdir()
        (skills / "check" / "SKILL.md").write_text("Body")

        run_telos_isolated("install", str(pack_dir), env_override=isolated_env)

        result = run_telos_isolated("uninstall", "gmail", "--yes", env_override=isolated_env)
        assert result.returncode == 0
        assert "gmail" in result.stdout.lower() or "uninstalled" in result.stdout.lower()


class TestInitCommand:
    """Tests for the init command."""

    def test_init_creates_config(self, isolated_env):
        result = run_telos_isolated("init", env_override=isolated_env)
        assert result.returncode == 0
        config_path = Path(isolated_env["TELOS_CONFIG_DIR"]) / "agents.toml"
        assert config_path.exists()

    def test_init_does_not_overwrite_existing(self, isolated_env):
        config_dir = Path(isolated_env["TELOS_CONFIG_DIR"])
        config_file = config_dir / "agents.toml"
        config_file.write_text("# existing config\n")

        result = run_telos_isolated("init", env_override=isolated_env)
        assert result.returncode == 0
        assert "already exists" in result.stdout.lower() or "not overwriting" in result.stdout.lower()
        assert config_file.read_text() == "# existing config\n"


class TestNoMatch:
    """Tests for when no skill matches."""

    def test_no_match_prints_available_skills(self, configured_env):
        result = run_telos_isolated("order me a pizza", env_override=configured_env)
        assert result.returncode != 0
        output = result.stdout.lower() + result.stderr.lower()
        assert "no matching skill" in output or "available" in output


class TestMcpConfig:
    """Tests for MCP config support."""

    def test_install_clickup_pack_with_mcp_json(self, isolated_env, tmp_path):
        """Install a pack with mcp.json → file ends up in skills dir,
        dry-run routes correctly."""
        pack_dir = tmp_path / "clickup-pack"
        pack_dir.mkdir()
        (pack_dir / "agent.toml").write_text(
            'name = "clickup"\ndescription = "ClickUp"\nworking_dir = "."\n'
        )
        skills = pack_dir / "skills"
        skills.mkdir()
        (skills / "standup").mkdir()
        (skills / "standup" / "SKILL.md").write_text(
            "---\ndescription: Project standup\n---\n# Standup\nDo standup"
        )
        (pack_dir / "mcp.json").write_text('{"mcpServers": {"clickup": {}}}')

        # Install the pack
        result = run_telos_isolated("install", str(pack_dir), env_override=isolated_env)
        assert result.returncode == 0
        assert "clickup" in result.stdout.lower()

        # Verify mcp.json was copied to skills dir
        skills_home = Path(isolated_env["TELOS_SKILLS_DIR"])
        mcp_dest = skills_home / "clickup" / "mcp.json"
        assert mcp_dest.exists()
        assert "clickup" in mcp_dest.read_text()

        # Dry-run should route correctly
        result = run_telos_isolated(
            "--agent", "clickup", "--dry-run", "standup",
            env_override=isolated_env,
        )
        assert result.returncode == 0
        assert "standup" in result.stdout.lower()


# ---------------------------------------------------------------------------
# Real E2E tests — real API key, real claude, real vault
# ---------------------------------------------------------------------------

class TestRealE2E:
    """True end-to-end tests against the real Obsidian vault.

    These make real Anthropic API calls and invoke real Claude Code.
    Skipped if the environment isn't set up for it.
    """

    @requires_real_env
    def test_interstitial_creates_file(self, real_env):
        """Full pipeline: telos receives natural language, routes via API,
        invokes Claude Code, which creates a real file in the vault."""
        # Snapshot existing interstitial files
        before = set(INTERSTITIAL_DIR.glob("*.md")) if INTERSTITIAL_DIR.exists() else set()

        result = run_telos(
            "write an interstitial about the telos e2e test run",
            env_override=real_env,
            timeout=120,
        )

        assert result.returncode == 0, f"telos failed.\nstdout: {result.stdout}\nstderr: {result.stderr}"

        # A new file should exist in the interstitial directory
        after = set(INTERSTITIAL_DIR.glob("*.md"))
        new_files = after - before
        assert len(new_files) >= 1, (
            f"Expected a new interstitial file in {INTERSTITIAL_DIR}.\n"
            f"Before: {len(before)} files, After: {len(after)} files.\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )

        # Verify the new file has relevant content
        new_file = sorted(new_files)[-1]  # most recent by filename
        content = new_file.read_text()
        assert "interstitial" in content.lower() or "e2e" in content.lower() or "telos" in content.lower(), (
            f"New file {new_file.name} doesn't contain expected content:\n{content}"
        )

    @requires_real_env
    def test_dry_run_with_real_api_routing(self, real_env):
        """API routing correctly matches natural language to a skill."""
        result = run_telos(
            "--verbose", "--dry-run",
            "let's wrap up for the day",
            env_override=real_env,
            timeout=30,
        )

        assert result.returncode == 0
        assert "shutdown" in result.stdout.lower()

    @requires_real_env
    def test_no_match_with_real_api(self, real_env):
        """API correctly returns NONE for nonsense input."""
        result = run_telos(
            "order me a pizza",
            env_override=real_env,
            timeout=30,
        )

        assert result.returncode != 0
        output = result.stdout.lower() + result.stderr.lower()
        assert "no matching skill" in output
