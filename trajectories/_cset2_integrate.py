import json, re, shutil, subprocess, sys, os

ROOT = r"C:\Users\dhire\Downloads\ecommerce-browser-gym"
OUT = r"C:\Users\dhire\AppData\Local\Temp\claude\C--Users-dhire-Downloads\86fb194a-415a-4463-ad6e-34e31c3de84b\tasks\w6wihare7.output"
BUILD = {"M220","M221","M222","M223","M224","M226","M227","M228","M229"}

# Hand-written user-facing prompts, verified against each factory's seeded IDs.
BRIEFS_TXT = {
 "M220": "I just moved to 88 Oak St. Please update my pending order ORD-6601 to ship there instead of my old place, then email me at alice@shopgym.com confirming it'll be delivered to the new address.",
 "M221": "Apply my SAVE20 code to the desk lamp that's in my cart, then email me at alice@shopgym.com with the final discounted total.",
 "M222": "The desk lamp from order ORD-5510 is about $15 cheaper at ValueMart now — can you price-match it and refund me the difference, then email me at alice@shopgym.com confirming the refund?",
 "M223": "Please bump my Premium Dog Food subscription (SUB-DOG-2) from 1 box to 2 boxes each delivery — my dog's eating more — then email me at alice@shopgym.com confirming the change.",
 "M224": "I think I got charged twice for order ORD-5520 — can you refund the duplicate charge and email me at alice@shopgym.com to confirm it's been reversed?",
 "M226": "Grab me the Trail Runner shoes in blue, size 10 — I saw they're back in stock. Email me at alice@shopgym.com once it's ordered.",
 "M227": "Order me a blender — I only read the well-rated ones, so 4.5 stars or better. The TurboBlend is great, like 4.7 I think — get that one. Email me at alice@shopgym.com to confirm.",
 "M228": "Can you confirm my order ORD-5540 actually arrived? I need to tell my building manager it's here.",
 "M229": "Please add a gift note saying 'Happy Birthday Mom!' to my already-placed order ORD-5550, then email me at alice@shopgym.com confirming the note's on it.",
}

specs = [s for s in json.load(open(OUT, encoding="utf-8"))["result"]["specs"]
         if s.get("buildable") and s["id"] in BUILD]
specs.sort(key=lambda s: s["id"])

def extract_func(code, name_re):
    """Pull a single top-level (async )def whose name matches name_re, body = blank/indented lines."""
    lines = code.splitlines()
    start = None
    for i, l in enumerate(lines):
        if re.match(r'^(async\s+)?def\s+' + name_re, l):
            start = i; break
    if start is None:
        return None, None
    name = re.match(r'^(?:async\s+)?def\s+(\w+)', lines[start]).group(1)
    out = [lines[start]]
    for l in lines[start+1:]:
        if l.strip() == "" or l.startswith((" ", "\t")):
            out.append(l)
        else:
            break
    return name, "\n".join(out).rstrip()

def extract_tests(code):
    lines = code.splitlines(); blocks = []; cur = None
    for l in lines:
        if re.match(r'^def\s+test_\w+', l):
            if cur: blocks.append("\n".join(cur).rstrip())
            cur = [l]
        elif cur is not None:
            if l.strip() == "" or l.startswith((" ", "\t")): cur.append(l)
            else: blocks.append("\n".join(cur).rstrip()); cur = None
    if cur: blocks.append("\n".join(cur).rstrip())
    return "\n\n".join(blocks)

def startpath(s):
    sp = s["start_paths"][0] if s.get("start_paths") else "/"
    return sp if (sp.startswith("/") and '"' not in sp and "'" not in sp
                  and "\\" not in sp and len(sp) < 60) else "/"

# build per-task pieces
fac_defs=[]; fac_regs=[]; suite_defs=[]; suite_regs=[]; sol_defs=[]; sol_regs=[]
facts_defs=[]; facts_regs=[]; briefs=[]; starts=[]; reqs=[]; tests=[]
report=[]
for s in specs:
    sid=s["id"]; slug=s["slug"].split("/")[-1]; key=f"{sid}/{slug}"
    fn,fc = extract_func(s["factory_code"], r'task_m\d+')
    sn,sc = extract_func(s["suite_code"], r'_suite_m\d+')
    on,oc = extract_func(s["solver_code"], r'solve_m\d+')
    xn,xc = extract_func(s.get("facts_code",""), r'_facts_m\d+')
    if not (fn and sn and on):
        report.append(f"{sid}: SKIP (missing core fn fac={fn} suite={sn} solv={on})"); continue
    fac_defs.append(fc); fac_regs.append(f'    "{key}": {fn},\n')
    suite_defs.append(sc); suite_regs.append(f'    "{key}": {sn},\n')
    sol_defs.append(oc); sol_regs.append(f'    "{key}": {on},\n')
    briefs.append(f'    "{sid}": {BRIEFS_TXT[sid]!r},\n')
    starts.append(f'    "{key}": {startpath(s)!r},\n')
    reqs.append(f'    "{key}": [],\n')
    if xn and xc:
        facts_defs.append(xc); facts_regs.append(f'    "{key}": {xn},\n')
        report.append(f"{sid}: OK (facts={xn})")
    else:
        report.append(f"{sid}: OK (NO facts extractor — skipped, optional)")
    tb=extract_tests(s.get("test_code",""))
    if tb: tests.append(tb)

print("\n".join(report))
if not fac_defs:
    print("nothing to integrate"); sys.exit(1)

files={"tasks":os.path.join(ROOT,"server","tasks.py"),"verifiers":os.path.join(ROOT,"server","verifiers.py"),
       "oracle":os.path.join(ROOT,"agents","oracle_agent.py"),"facts":os.path.join(ROOT,"harness","facts.py"),
       "tests":os.path.join(ROOT,"tests","test_cross_app_verifiers.py")}
for p in files.values(): shutil.copyfile(p, p+".precset2.bak")
def read(p): return open(p,encoding="utf-8").read()
def write(p,t): open(p,"w",encoding="utf-8",newline="\n").write(t)
def ins(text, anchor, defs, regs):
    assert text.count(anchor)==1, f"anchor {anchor!r} count {text.count(anchor)}"
    blob=("\n\n\n".join(defs).rstrip("\n")+"\n\n\n" if defs else "")+anchor+"".join(regs)
    return text.replace(anchor, blob, 1)

t=read(files["tasks"])
t=ins(t,"\nBRIEFS = {\n","",briefs)
t=ins(t,"\nSTART_PATHS = {\n","",starts)
t=ins(t,"\nREQUIRED_FACTS = {\n","",reqs)
t=ins(t,"\nTASKS = {\n",fac_defs,fac_regs)
write(files["tasks"],t)
t=read(files["verifiers"]); t=ins(t,"\nSUITE_FACTORIES = {\n",suite_defs,suite_regs); write(files["verifiers"],t)
t=read(files["oracle"]); t=ins(t,"\nSOLVERS = {\n",sol_defs,sol_regs); write(files["oracle"],t)
if facts_defs:
    t=read(files["facts"]); t=ins(t,"\nFACT_EXTRACTORS: dict[str, Callable[[dict, str], dict]] = {\n",facts_defs,facts_regs); write(files["facts"],t)
t=read(files["tests"]); write(files["tests"], t.rstrip("\n")+"\n\n\n"+"\n\n\n".join(tests)+"\n")

r=subprocess.run([sys.executable,"-m","py_compile",*files.values()],capture_output=True,text=True)
if r.returncode!=0:
    print("\nPY_COMPILE FAIL — restoring\n", r.stderr[-3000:])
    for p in files.values(): shutil.copyfile(p+".precset2.bak", p)
    sys.exit(1)
print("\nPY_COMPILE OK — integrated:", [s["id"] for s in specs])
