"""Product-owned copy of the supported-reference SDK/console reproducer.

Exit 0 requires both equivalent pointer spellings to yield valid BREAKING JSON.
Only console discovery differs from the preserved original reviewer probe:
use this interpreter's script installation scheme, including global Windows.
"""
import json
from pathlib import Path
import subprocess
import sys
import sysconfig
import tempfile
from schemawitness import compare

results=[]
executable=Path(sysconfig.get_path('scripts'))/('schemawitness.exe' if sys.platform=='win32' else 'schemawitness')
with tempfile.TemporaryDirectory() as name:
    old,new=Path(name)/'old.json',Path(name)/'new.json'
    old.write_text('true',encoding='utf-8')
    for ref in ('#/$defs/N','#%2F$defs%2FN'):
        schema={'$defs':{'N':{'type':'integer'}},'$ref':ref}
        entry={'ref':ref}
        try:
            result=compare(True,schema)
            entry['sdk']={'status':result.status,'wire':result.wire,'returned_result':True,
                          'valid_evidence':result.status=='BREAKING' and json.loads(result.wire) is None and
                                           result.validation['source']['valid'] and not result.validation['target']['valid']}
        except Exception as exc:
            entry['sdk']={'returned_result':False,'exception':type(exc).__name__,'message':str(exc),'valid_evidence':False}
        new.write_text(json.dumps(schema),encoding='utf-8')
        command=subprocess.run([str(executable),str(old),str(new)],capture_output=True,text=True)
        try:
            output=json.loads(command.stdout)
            valid=command.returncode==1 and output['status']=='BREAKING' and json.loads(output['wire']) is None
        except (ValueError,KeyError,TypeError):output=None;valid=False
        entry['console']={'exit':command.returncode,'parseable_json':output is not None,'traceback':'Traceback' in command.stderr,
                          'valid_evidence':valid,'stdout':command.stdout}
        results.append(entry)
successful=all(row['sdk']['valid_evidence'] and row['console']['valid_evidence'] for row in results)
print(json.dumps({'successful':successful,'results':results},sort_keys=True,indent=2))
raise SystemExit(not successful)
