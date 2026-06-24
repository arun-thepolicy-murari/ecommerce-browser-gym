import json, re, shutil, subprocess, sys, os
ROOT = r"C:\Users\dhire\Downloads\ecommerce-browser-gym"
specs = json.load(open(os.path.join(ROOT,"trajectories","_diverse_specs.json"), encoding="utf-8"))
specs = [s for s in specs if s.get("buildable")]
specs.sort(key=lambda s: s["id"])

def extract_func(code, name_re):
    lines = (code or "").splitlines(); start=None
    for i,l in enumerate(lines):
        if re.match(r'^(async\s+)?def\s+'+name_re, l): start=i; break
    if start is None: return None,None
    name=re.match(r'^(?:async\s+)?def\s+(\w+)', lines[start]).group(1)
    out=[lines[start]]
    for l in lines[start+1:]:
        if l.strip()=="" or l.startswith((" ","\t")): out.append(l)
        else: break
    return name, "\n".join(out).rstrip()
def extract_tests(code):
    lines=(code or "").splitlines(); blocks=[]; cur=None
    for l in lines:
        if re.match(r'^def\s+test_\w+', l):
            if cur: blocks.append("\n".join(cur).rstrip())
            cur=[l]
        elif cur is not None:
            if l.strip()=="" or l.startswith((" ","\t")): cur.append(l)
            else: blocks.append("\n".join(cur).rstrip()); cur=None
    if cur: blocks.append("\n".join(cur).rstrip())
    return "\n\n".join(blocks)
def sp(s):
    p = (s.get("start_path") or "/").strip()
    return p if (p.startswith("/") and '"' not in p and "'" not in p and "\\" not in p and len(p)<70) else "/"

fac_d=[];fac_r=[];su_d=[];su_r=[];so_d=[];so_r=[];fx_d=[];fx_r=[];br=[];st=[];rq=[];ts=[];rep=[]
for s in specs:
    sid=s["id"]; slug=s["slug"].split("/")[-1]; key=f"{sid}/{slug}"
    fn,fc=extract_func(s.get("factory_code",""), r'task_m\d+')
    sn,sc=extract_func(s.get("suite_code",""), r'_suite_m\d+')
    on,oc=extract_func(s.get("solver_code",""), r'solve_m\d+')
    xn,xc=extract_func(s.get("facts_code",""), r'_facts_m\d+')
    if not(fn and sn and on): rep.append(f"{sid}: SKIP fac={fn} suite={sn} solv={on}"); continue
    brief=s.get("brief","").strip()
    fac_d.append(fc); fac_r.append(f'    "{key}": {fn},\n')
    su_d.append(sc); su_r.append(f'    "{key}": {sn},\n')
    so_d.append(oc); so_r.append(f'    "{key}": {on},\n')
    br.append(f'    "{sid}": {brief!r},\n'); st.append(f'    "{key}": {sp(s)!r},\n'); rq.append(f'    "{key}": [],\n')
    if xn and xc: fx_d.append(xc); fx_r.append(f'    "{key}": {xn},\n'); rep.append(f"{sid}: OK facts={xn}")
    else: rep.append(f"{sid}: OK (no facts)")
    tb=extract_tests(s.get("test_code",""));
    if tb: ts.append(tb)
print("\n".join(rep))
if not fac_d: print("nothing"); sys.exit(1)

F={"tasks":os.path.join(ROOT,"server","tasks.py"),"verifiers":os.path.join(ROOT,"server","verifiers.py"),
   "oracle":os.path.join(ROOT,"agents","oracle_agent.py"),"facts":os.path.join(ROOT,"harness","facts.py"),
   "tests":os.path.join(ROOT,"tests","test_cross_app_verifiers.py")}
for p in F.values(): shutil.copyfile(p, p+".prediv.bak")
rd=lambda p: open(p,encoding="utf-8").read(); wr=lambda p,t: open(p,"w",encoding="utf-8",newline="\n").write(t)
def ins(text,anchor,defs,regs):
    assert text.count(anchor)==1, f"anchor {anchor!r} x{text.count(anchor)}"
    return text.replace(anchor, ("\n\n\n".join(defs).rstrip("\n")+"\n\n\n" if defs else "")+anchor+"".join(regs), 1)
t=rd(F["tasks"]); t=ins(t,"\nBRIEFS = {\n","",br); t=ins(t,"\nSTART_PATHS = {\n","",st)
t=ins(t,"\nREQUIRED_FACTS = {\n","",rq); t=ins(t,"\nTASKS = {\n",fac_d,fac_r); wr(F["tasks"],t)
t=rd(F["verifiers"]); t=ins(t,"\nSUITE_FACTORIES = {\n",su_d,su_r); wr(F["verifiers"],t)
t=rd(F["oracle"]); t=ins(t,"\nSOLVERS = {\n",so_d,so_r); wr(F["oracle"],t)
if fx_d:
    t=rd(F["facts"]); t=ins(t,"\nFACT_EXTRACTORS: dict[str, Callable[[dict, str], dict]] = {\n",fx_d,fx_r); wr(F["facts"],t)
t=rd(F["tests"]); wr(F["tests"], t.rstrip("\n")+"\n\n\n"+"\n\n\n".join(ts)+"\n")
r=subprocess.run([sys.executable,"-m","py_compile",*F.values()],capture_output=True,text=True)
if r.returncode!=0:
    print("PY_COMPILE FAIL — restoring\n", r.stderr[-3000:])
    for p in F.values(): shutil.copyfile(p+".prediv.bak", p)
    sys.exit(1)
print("\nPY_COMPILE OK — integrated:", [s["id"] for s in specs])
