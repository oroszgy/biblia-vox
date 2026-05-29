"""CLI integration tests for the reference subcommand group.

Uses typer.testing.CliRunner to test the CLI commands without
spawning subprocesses.
"""

from __future__ import annotations

from typer.testing import CliRunner

from bibliavox.main import app

runner = CliRunner()


class TestHelp:
    """Tests for the top-level CLI help."""

    def test_help_exits_zero(self) -> None:
        """bibliavox --help should exit with code 0."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "bibliavox" in result.output.lower()

    def test_help_shows_reference_subcommand(self) -> None:
        """bibliavox --help should show the reference subcommand."""
        result = runner.invoke(app, ["--help"])
        assert "reference" in result.output.lower()


class TestReferenceList:
    """Tests for the `bibliavox reference list` command."""

    def test_list_shows_73_books(self) -> None:
        """bibliavox reference list should show all 73 Catholic books."""
        result = runner.invoke(app, ["reference", "list"])
        assert result.exit_code == 0
        assert "73" in result.output

    def test_list_filter_ot(self) -> None:
        """bibliavox reference list --testament OT should show only OT books."""
        result = runner.invoke(app, ["reference", "list", "--testament", "OT"])
        assert result.exit_code == 0
        # OT has 46 books in Catholic canon
        assert "46" in result.output

    def test_list_filter_nt(self) -> None:
        """bibliavox reference list --testament NT should show only NT books."""
        result = runner.invoke(app, ["reference", "list", "--testament", "NT"])
        assert result.exit_code == 0
        # NT has 27 books
        assert "27" in result.output

    def test_list_filter_deuterocanonical(self) -> None:
        """bibliavox reference list -d should show only deuterocanonical books."""
        result = runner.invoke(app, ["reference", "list", "--deuterocanonical"])
        assert result.exit_code == 0
        # Deuterocanonical books exist
        assert "Catholic Bible Books" in result.output


class TestReferenceLookup:
    """Tests for the `bibliavox reference lookup` command."""

    def test_lookup_ter(self) -> None:
        """bibliavox reference lookup Ter should show GEN (Genesis)."""
        result = runner.invoke(app, ["reference", "lookup", "Ter"])
        assert result.exit_code == 0
        assert "GEN" in result.output
        assert "Teremtés" in result.output

    def test_lookup_mk(self) -> None:
        """bibliavox reference lookup Mk should show MRK (Mark)."""
        result = runner.invoke(app, ["reference", "lookup", "Mk"])
        assert result.exit_code == 0
        assert "MRK" in result.output

    def test_lookup_unknown(self) -> None:
        """bibliavox reference lookup XYZ should exit with code 1."""
        result = runner.invoke(app, ["reference", "lookup", "XYZ"])
        assert result.exit_code == 1
        assert "Unknown" in result.output

    def test_lookup_case_insensitive(self) -> None:
        """Lookup should be case-insensitive."""
        result = runner.invoke(app, ["reference", "lookup", "ter"])
        assert result.exit_code == 0
        assert "GEN" in result.output


class TestReferenceInfo:
    """Tests for the `bibliavox reference info` command."""

    def test_info_gen(self) -> None:
        """bibliavox reference info GEN should show Genesis details."""
        result = runner.invoke(app, ["reference", "info", "GEN"])
        assert result.exit_code == 0
        assert "Teremtés" in result.output
        assert "50" in result.output  # Genesis has 50 chapters

    def test_info_by_abbreviation(self) -> None:
        """bibliavox reference info Ter should also work (abbreviation lookup)."""
        result = runner.invoke(app, ["reference", "info", "Ter"])
        assert result.exit_code == 0
        assert "GEN" in result.output
        assert "Teremtés" in result.output

    def test_info_unknown(self) -> None:
        """bibliavox reference info FAKE should exit with code 1."""
        result = runner.invoke(app, ["reference", "info", "FAKE"])
        assert result.exit_code == 1
        assert "Unknown" in result.output

    def test_info_shows_verse_table(self) -> None:
        """bibliavox reference info GEN should show verse counts per chapter."""
        result = runner.invoke(app, ["reference", "info", "GEN"])
        assert result.exit_code == 0
        # Genesis 1 has 31 verses
        assert "31" in result.output
