import io
import pathlib
import sys

try:
    import pytest
except ImportError as exc:
    pathlib.Path('pytest_output.txt').write_text(f'IMPORT_ERROR: {exc}')
    raise

buf = io.StringIO()
sys_stdout = sys.stdout
sys.stdout = buf
try:
    exit_code = pytest.main(['-q'])
finally:
    sys.stdout = sys_stdout
pathlib.Path('pytest_output.txt').write_text(buf.getvalue() + f'\nEXIT {exit_code}')
