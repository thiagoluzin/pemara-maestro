import sys,unittest,json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'services/studio'))
names=['test_external_anchor_removed','test_generative_control','test_maestro_ui_contracts','test_creative_os_integration','test_creative_os_adapters']
suite=unittest.defaultTestLoader.loadTestsFromNames(names)
result=unittest.TestResult();suite.run(result)
report={'testsRun':result.testsRun,'failures':[{'test':str(t),'detail':msg.splitlines()[-1][:220]} for t,msg in result.failures],'errors':[{'test':str(t),'detail':msg.splitlines()[-1][:220]} for t,msg in result.errors]}
baseline=[]
for test,msg in result.failures:
    if test.__class__.__module__!='test_maestro_ui_contracts':continue
    case=test.__class__(test._testMethodName)
    case.setUp()
    case.source=(root/'backups/remove_nim_video_gate_20260926/app/assets/maestro.js').read_text(encoding='utf-8-sig')
    try:getattr(case,case._testMethodName)();baseline.append({'test':str(test),'baselineFails':False})
    except AssertionError:baseline.append({'test':str(test),'baselineFails':True})
report['preexistingFailureComparison']=baseline
(root/'backups/remove_nim_video_gate_20260926/test_report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
