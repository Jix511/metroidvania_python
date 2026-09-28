"""Atomic JSON persistence with validation and automatic backup recovery."""

import json
import os
import tempfile
from pathlib import Path


class JsonStorageError(Exception):
    pass


def backup_path_for(path):
    path = Path(path)
    return path.with_name(f'{path.stem}.backup{path.suffix}')


def _validate(data, validator):
    if validator is not None and not validator(data):
        raise JsonStorageError('JSON data failed validation')


def _read(path, validator=None):
    with Path(path).open('r', encoding='utf-8') as handle:
        data = json.load(handle)
    _validate(data, validator)
    return data


def _write_payload(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
                mode='w', encoding='utf-8', dir=path.parent,
                prefix=f'.{path.name}.', suffix='.tmp', delete=False) as handle:
            temp_path = Path(handle.name)
            json.dump(data, handle, indent=2, ensure_ascii=False)
            handle.write('\n')
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()


def save_json_atomic(path, data, validator=None):
    """Write JSON atomically and preserve the previous valid document."""
    path = Path(path)
    backup_path = backup_path_for(path)
    _validate(data, validator)

    try:
        previous = _read(path, validator)
    except (FileNotFoundError, OSError, UnicodeError, json.JSONDecodeError,
            JsonStorageError):
        previous = None

    if previous is not None:
        _write_payload(backup_path, previous)

    _write_payload(path, data)
    _write_payload(backup_path, data)


def load_json_with_recovery(path, validator=None):
    """Return ``(data, recovered)`` and restore a broken primary from backup."""
    path = Path(path)
    backup_path = backup_path_for(path)
    found_candidate = path.exists() or backup_path.exists()

    try:
        return _read(path, validator), False
    except (FileNotFoundError, OSError, UnicodeError, json.JSONDecodeError,
            JsonStorageError):
        pass

    try:
        data = _read(backup_path, validator)
    except (FileNotFoundError, OSError, UnicodeError, json.JSONDecodeError,
            JsonStorageError) as exc:
        if not found_candidate:
            raise FileNotFoundError(path) from exc
        raise JsonStorageError(f'No valid JSON copy for {path.name}') from exc

    _write_payload(path, data)
    return data, True
