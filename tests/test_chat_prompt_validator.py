"""Tests for chat prompt validation and intent routing."""

from smartinstall.ui.services.chat_prompt_validator import (
    ChatPromptIntent,
    is_install_command_intent,
    validate_chat_prompt,
)


def test_rejects_empty_prompt() -> None:
    result = validate_chat_prompt("   ")
    assert result.valid is False
    assert result.intent is ChatPromptIntent.INVALID


def test_rejects_too_short_prompt() -> None:
    result = validate_chat_prompt("a")
    assert result.valid is False


def test_accepts_list_command() -> None:
    result = validate_chat_prompt("list available installers")
    assert result.valid is True
    assert result.intent is ChatPromptIntent.COMMAND_LIST


def test_accepts_help_command() -> None:
    result = validate_chat_prompt("help")
    assert result.valid is True
    assert result.intent is ChatPromptIntent.COMMAND_HELP


def test_accepts_install_command() -> None:
    result = validate_chat_prompt("install mingw-get-setup.exe")
    assert result.valid is True
    assert result.intent is ChatPromptIntent.COMMAND_INSTALL
    assert result.installer_name == "mingw-get-setup.exe"


def test_rejects_invalid_installer_name() -> None:
    result = validate_chat_prompt("install ..\\secret.exe")
    assert result.valid is False


def test_classifies_last_install_question() -> None:
    result = validate_chat_prompt("What went wrong with the last installation?")
    assert result.valid is True
    assert result.intent is ChatPromptIntent.DIAGNOSE_LAST


def test_classifies_knowledge_question() -> None:
    result = validate_chat_prompt("How do I fix exit code 1603?")
    assert result.valid is True
    assert result.intent is ChatPromptIntent.KNOWLEDGE_QUERY


def test_classifies_capabilities_as_help() -> None:
    result = validate_chat_prompt("What can Smart Installer AI do?")
    assert result.valid is True
    assert result.intent is ChatPromptIntent.COMMAND_HELP


def test_rejects_unrecognized_prompt() -> None:
    result = validate_chat_prompt("asdfghjkl qwerty")
    assert result.valid is False
    assert result.intent is ChatPromptIntent.INVALID


def test_install_intent_detection() -> None:
    install = validate_chat_prompt("install demo.msi")
    browse = validate_chat_prompt("browse")
    help_result = validate_chat_prompt("help")
    assert is_install_command_intent(install.intent) is True
    assert is_install_command_intent(browse.intent) is True
    assert is_install_command_intent(help_result.intent) is False
