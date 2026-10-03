"""Independent membership oracle and installed consumer probes.

No compiler, proof, accepts, search, wire parser or independent_validate helper
from the reviewed artifact is used to establish oracle membership.
This product-owned copy adapts console discovery to the interpreter's scripts
scheme; the preserved reviewer original and membership oracle remain unchanged.
"""
from copy import deepcopy
from decimal import Decimal
from fractions import Fraction
import hashlib
import itertools
import json
from pathlib import Path
import subprocess
import sys
import sysconfig
import tempfile
import unittest
from urllib.parse import unquote
from schemawitness import compare,Limits,review,dumps
from jsonschema import Draft202012Validator

COUNTS={}
def same(a,b):
    if type(a) is bool or type(b) is bool:return type(a) is type(b) and a==b
    if isinstance(a,(int,Decimal)) and isinstance(b,(int,Decimal)):return Fraction(a)==Fraction(b)
    if isinstance(a,list) and isinstance(b,list):return len(a)==len(b) and all(same(x,y) for x,y in zip(a,b))
    if isinstance(a,dict) and isinstance(b,dict):return a.keys()==b.keys() and all(same(a[k],b[k]) for k in a)
    return type(a) is type(b) and a==b
def member(schema,value,root=None):
    root=schema if root is None else root
    if type(schema) is bool:return schema
    if '$ref' in schema:
        pointer=unquote(schema['$ref'][1:]);target=root
        for token in pointer[1:].split('/') if pointer else []:
            token=token.replace('~1','/').replace('~0','~')
            target=target[int(token)] if isinstance(target,list) else target[token]
        if not member(target,value,root):return False
    if any(not member(s,value,root) for s in schema.get('allOf',[])):return False
    numeric=isinstance(value,(int,Decimal)) and type(value) is not bool
    integer=numeric and Fraction(value).denominator==1
    kinds={'null':value is None,'boolean':type(value) is bool,'number':numeric,'integer':integer,
           'string':type(value) is str,'array':type(value) is list,'object':type(value) is dict}
    if 'type' in schema:
        names=schema['type'] if isinstance(schema['type'],list) else [schema['type']]
        if not any(kinds[n] for n in names):return False
    if 'enum' in schema and not any(same(value,v) for v in schema['enum']):return False
    if 'const' in schema and not same(value,schema['const']):return False
    if numeric:
        for key,op in [('minimum',lambda a,b:a>=b),('maximum',lambda a,b:a<=b),
                       ('exclusiveMinimum',lambda a,b:a>b),('exclusiveMaximum',lambda a,b:a<b)]:
            if key in schema and not op(Fraction(value),Fraction(schema[key])):return False
    if type(value) is str:
        if len(value)<schema.get('minLength',0) or len(value)>schema.get('maxLength',len(value)):return False
    if type(value) is list:
        if len(value)<schema.get('minItems',0) or len(value)>schema.get('maxItems',len(value)):return False
        if any(not member(schema.get('items',True),v,root) for v in value):return False
    if type(value) is dict:
        if any(k not in value for k in schema.get('required',[])):return False
        for k,v in value.items():
            if not member(schema.get('properties',{}).get(k,schema.get('additionalProperties',True)),v,root):return False
    return True

def schemas():
    out=[True,False,{}, {'type':'integer'},{'type':'number'},{'type':['null','number']},
         {'enum':[False,0,Decimal('0.1')]},{'const':{'$schema':'literal','nested':[True,Decimal('1.0')]}},
         {'type':'object','properties':{'x':False}}, {'type':'object','required':['x'],'properties':{'x':False}}]
    for lo,hi,exclusive in [(-1,1,False),(0,0,False),(0,1,True),(Decimal('0.1'),Decimal('0.2'),True),(2,1,False)]:
        for kind in ('integer','number'):
            out.append({'type':kind,'exclusiveMinimum' if exclusive else 'minimum':lo,'maximum':hi})
    for item in [False,{'type':'integer'},{'minimum':0}]:
        out.append({'type':'array','items':item,'maxItems':2})
    for required,additional in [([],False),(['x'],True),(['x'],{'type':'integer'})]:
        out.append({'type':'object','properties':{'x':{'type':'integer','minimum':0}},'required':required,'additionalProperties':additional})
    out.extend([{'allOf':[{'type':'object','properties':{'x':True},'additionalProperties':False},
                          {'type':'object','properties':{'y':True},'additionalProperties':False}]},
                {'$defs':{'a/b~c':{'type':'integer'}},'$ref':'#%2F$defs%2Fa~1b~0c','minimum':0},
                {'type':'string','minLength':1,'maxLength':2}, {'type':'number','const':Decimal('9007199254740993.000000000000000001')}])
    return out

class ReviewerTests(unittest.TestCase):
    def test_all_pairs_pure_membership_oracle_and_actual_wire(self):
        primitives=[None,False,True,-2,-1,0,1,2,Decimal('0.1'),Decimal('0.15'),Decimal('0.2'),Decimal('1.0'),'','x','汉']
        instances=primitives+[[],*[list(v) for n in (1,2) for v in itertools.product([-1,0,True,Decimal('0.1')],repeat=n)]]
        instances += [{},*[{k:v} for k,v in itertools.product(('x','y','z'),primitives)],
                      *[{'x':a,'y':b} for a,b in itertools.product([-1,0,1,False],repeat=2)],
                      {'$schema':'literal','nested':[True,1]}]
        all_schemas=schemas();membership=[[member(s,v) for v in instances] for s in all_schemas]
        counts={'pairs':0,'compatible':0,'breaking':0,'unknown':0,'instances':len(instances)}
        for i,j in itertools.product(range(len(all_schemas)),repeat=2):
            result=compare(all_schemas[i],all_schemas[j]);counts['pairs']+=1
            if result.status=='COMPATIBLE':
                counts['compatible']+=1
                self.assertFalse(any(a and not b for a,b in zip(membership[i],membership[j])),(i,j,result.to_dict()))
            elif result.status=='BREAKING':
                counts['breaking']+=1
                value=json.loads(result.wire,parse_float=Decimal)
                self.assertTrue(member(all_schemas[i],value),(i,j,result.wire))
                self.assertFalse(member(all_schemas[j],value),(i,j,result.wire))
                self.assertTrue(result.validation['after_wire_roundtrip'])
                self.assertTrue(result.validation['source']['valid']);self.assertFalse(result.validation['target']['valid'])
            else:
                self.assertEqual(result.status,'UNKNOWN',(i,j,result.to_dict()));counts['unknown']+=1
        COUNTS['pure_oracle']=counts

    def test_ref_literals_exact_decimal_and_direction(self):
        for value in [Decimal('1.0'),Decimal('1e0'),Decimal('9007199254740993.000000000000000001')]:
            old={'const':value};new={'type':'integer'}
            r=compare(old,new,prove=False)
            self.assertEqual(r.status,'UNKNOWN' if Fraction(value).denominator==1 else 'BREAKING')
            if r.wire:self.assertTrue(member(old,json.loads(r.wire,parse_float=Decimal)))
        source={'default':{'$schema':'https://json-schema.org/draft/2020-12/schema','type':'integer'},'$ref':'#/default'}
        self.assertEqual(compare({'const':Decimal('1.0')},source,prove=False).status,'UNKNOWN')
        old={'type':'object'};new={'const':{'$schema':'literal data','nested':{'$schema':'still literal'}}}
        r=compare(old,new);v=json.loads(r.wire)
        self.assertTrue(Draft202012Validator(old).is_valid(v));self.assertFalse(Draft202012Validator(new).is_valid(v))
        self.assertEqual(compare({'type':'integer'},{'type':'number'},direction='request').status,'COMPATIBLE')
        self.assertEqual(compare({'type':'integer'},{'type':'number'},direction='response').status,'BREAKING')
        self.assertEqual(compare({'enum':[True,1]},{'enum':[1]}).status,'BREAKING')

    def test_invalid_unknown_and_resource_limits_fail_closed(self):
        for ref in ('#/allOf/-1','#/allOf/01','#/allOf/+0','#/$defs/a~3','#/$defs/a%ZZ','#/$defs/a%FF'):
            r=compare({'allOf':[True],'$ref':ref},True);self.assertEqual(r.status,'INVALID',ref)
        for source in [{'$ref':'https://example.invalid/schema'},{'pattern':'x'},{'anyOf':[True,False]},
                       {'$defs':{'x':{'$ref':'#/$defs/x'}},'$ref':'#/$defs/x'}]:
            self.assertEqual(compare(source,True).status,'UNKNOWN')
        self.assertEqual(compare({'type':'bad'},True).status,'INVALID')
        self.assertEqual(compare({'const':Decimal('1e1025')},True).status,'UNKNOWN')
        r=compare({'type':'string','minLength':20},{'const':'x'},limits=Limits(max_total_candidate_bytes=10))
        self.assertEqual(r.status,'UNKNOWN');self.assertLessEqual(r.metrics['candidate_bytes'],10)
        self.assertIn('cumulative_candidate_bytes',r.metrics['search_limit_reasons'])
        manifest={'operations':[{'id':'a','request':{'old':{'pattern':'x'},'new':True},'response':{'old':True,'new':True}}]}
        self.assertEqual(review(manifest)['decision'],'BLOCK')
        manifest['operations'].append(deepcopy(manifest['operations'][0]));self.assertEqual(review(manifest)['status'],'INVALID')
        self.assertEqual(compare({'type':'integer'},{'type':'number'},prove=False,search=False).status,'UNKNOWN')

    def test_real_console_roundtrip_exit_codes_source_preservation(self):
        executable=Path(sysconfig.get_path('scripts'))/('schemawitness.exe' if sys.platform=='win32' else 'schemawitness')
        with tempfile.TemporaryDirectory() as name:
            base=Path(name);old,new=base/'old.json',base/'new.json'
            cases=[({'type':'integer'},{'type':'number'},0),({'type':'number'},{'type':'integer'},1),
                   ({'pattern':'x'},True,2),({'type':'nonsense'},True,3),
                   ({'const':Decimal('9007199254740993.000000000000000001')},{'maximum':Decimal('9007199254740993')},1)]
            for a,b,expected in cases:
                old.write_text(dumps(a),encoding='utf-8');new.write_text(dumps(b),encoding='utf-8')
                initial=(old.read_bytes(),new.read_bytes())
                r=subprocess.run([str(executable),str(old),str(new)],capture_output=True,text=True)
                self.assertEqual(r.returncode,expected,r.stderr);report=json.loads(r.stdout,parse_float=Decimal)
                self.assertEqual((old.read_bytes(),new.read_bytes()),initial)
                if expected==1:
                    v=json.loads(report['wire'],parse_float=Decimal);self.assertTrue(member(a,v));self.assertFalse(member(b,v))
            old.write_bytes(b'{"type":"integer","type":"number"}')
            r=subprocess.run([str(executable),str(old),str(new)],capture_output=True,text=True)
            self.assertEqual(r.returncode,3);self.assertNotIn('Traceback',r.stderr)
        COUNTS['installed_console_cases']=6

if __name__=='__main__':
    outcome=unittest.main(exit=False,verbosity=2)
    print(json.dumps({'successful':outcome.result.wasSuccessful(),'counts':COUNTS},sort_keys=True))
    raise SystemExit(not outcome.result.wasSuccessful())
