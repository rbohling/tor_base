"""Exercise launcher control flow with mocked macOS/Docker commands, not real containers."""
import os
from pathlib import Path
import shutil
import subprocess
import pytest

@pytest.fixture
def lab(tmp_path):
    root=tmp_path/'project with spaces'
    (root/'scripts').mkdir(parents=True)
    shutil.copy(Path(__file__).parents[1]/'scripts/macos.sh',root/'scripts/macos.sh')
    (root/'compose.yaml').write_text('services: {}\n')
    bin_dir=tmp_path/'bin';bin_dir.mkdir()
    commands={
        'uname': '#!/bin/bash\necho "${MOCK_OS:-Darwin}"\n',
        'curl': '#!/bin/bash\nexit 0\n',
        'docker': '''#!/bin/bash
printf '%s\\n' "$*" >> "$CALL_LOG"
case "$1" in
  info) exit 0 ;;
  run) printf 'existing-local-config\\n' > .env; exit 0 ;;
esac
if [ "${FAIL_BUILD:-0}" = 1 ] && [[ "$*" == *"up -d --build"* ]]; then exit 17; fi
if [[ "$*" == *"cat /var/lib/tor/torbase/hostname"* ]]; then echo example.onion; fi
exit 0
'''}
    for name,script in commands.items():
        p=bin_dir/name;p.write_text(script);p.chmod(0o755)
    env=dict(os.environ,PATH=str(bin_dir)+os.pathsep+os.environ['PATH'],CALL_LOG=str(tmp_path/'calls'))
    return root,env,tmp_path/'calls'

def run(lab,*args,**changes):
    root,env,_=lab
    return subprocess.run(['bash',str(root/'scripts/macos.sh'),*args],env=dict(env,**changes),
        cwd=root.parent,text=True,capture_output=True,timeout=10)

def test_first_start_creates_configuration(lab):
    result=run(lab,'start')
    assert result.returncode==0,result.stderr
    assert (lab[0]/'.env').exists()
    calls=lab[2].read_text()
    assert 'run --rm --mount type=bind,source=' in calls
    assert '--profile onion up -d --build' in calls
    assert 'Local website:' in result.stdout

def test_existing_configuration_is_preserved(lab):
    (lab[0]/'.env').write_text('do-not-replace')
    assert run(lab,'start').returncode==0
    assert (lab[0]/'.env').read_text()=='do-not-replace'
    assert 'run --rm' not in lab[2].read_text()

def test_local_start_limits_services(lab):
    assert run(lab,'start','--local').returncode==0
    assert 'up -d --build db init app' in lab[2].read_text()

def test_failed_build_is_not_reported_as_ready(lab):
    r=run(lab,'start',FAIL_BUILD='1')
    assert r.returncode!=0
    assert 'Local website:' not in r.stdout

def test_stop_preserves_volumes(lab):
    (lab[0]/'.env').touch()
    assert run(lab,'stop').returncode==0
    calls=lab[2].read_text()
    assert '--profile onion stop' in calls
    assert 'down' not in calls

def test_address_and_user_commands(lab):
    (lab[0]/'.env').touch()
    assert 'example.onion' in run(lab,'address').stdout
    assert run(lab,'user','alice').returncode==0
    assert 'exec app flask --app torbase create-user alice' in lab[2].read_text()

def test_invalid_arguments_and_non_mac(lab):
    assert run(lab,'start','--invalid').returncode!=0
    assert run(lab,'user').returncode!=0
    assert run(lab,'start',MOCK_OS='Linux').returncode!=0
    assert not lab[2].exists()
