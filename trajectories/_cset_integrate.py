import json, shutil, subprocess, sys, os

ROOT = r"C:\Users\dhire\Downloads\ecommerce-browser-gym"
OUT = r"C:\Users\dhire\AppData\Local\Temp\claude\C--Users-dhire-Downloads\86fb194a-415a-4463-ad6e-34e31c3de84b\tasks\wx67ozm3g.output"
MISSING = {"M212", "M213", "M214", "M216", "M218", "M219"}

specs = json.load(open(OUT, encoding="utf-8"))["result"]["specs"]
specs = sorted([s for s in specs if s["id"] in MISSING], key=lambda s: s["id"])
assert {s["id"] for s in specs} == MISSING, f"have {[s['id'] for s in specs]}"

files = {
    "tasks":     os.path.join(ROOT, "server", "tasks.py"),
    "verifiers": os.path.join(ROOT, "server", "verifiers.py"),
    "oracle":    os.path.join(ROOT, "agents", "oracle_agent.py"),
    "facts":     os.path.join(ROOT, "harness", "facts.py"),
    "tests":     os.path.join(ROOT, "tests", "test_cross_app_verifiers.py"),
}
for p in files.values():
    shutil.copyfile(p, p + ".precset.bak")

def read(p):  return open(p, encoding="utf-8").read()
def write(p, t): open(p, "w", encoding="utf-8", newline="\n").write(t)
def regline(s): return s if s.endswith("\n") else s + "\n"

def insert(text, anchor, defs_blob, reg_blob):
    n = text.count(anchor)
    assert n == 1, f"anchor count={n} for {anchor!r}"
    repl = (defs_blob.rstrip("\n") + "\n\n\n" if defs_blob else "") + anchor + reg_blob
    return text.replace(anchor, repl, 1)

def startpath(s):
    sp = s["start_paths"][0] if s["start_paths"] else "/"
    return sp if sp.startswith("/") else "/"

# ---- tasks.py: BRIEFS(short key) + START_PATHS + REQUIRED_FACTS + factory defs + TASKS ----
t = read(files["tasks"])
briefs   = "".join(f'    "{s["id"]}": {s["brief"]!r},\n' for s in specs)
starts   = "".join(f'    "{s["id"]}/{s["slug"]}": {startpath(s)!r},\n' for s in specs)
reqfacts = "".join(f'    "{s["id"]}/{s["slug"]}": {s["required_facts"]!r},\n' for s in specs)
fac_defs = "\n\n\n".join(s["factory_code"].rstrip("\n") for s in specs)
fac_regs = "".join(regline(s["factory_registry_line"]) for s in specs)
t = insert(t, "\nBRIEFS = {\n", "", briefs)
t = insert(t, "\nSTART_PATHS = {\n", "", starts)
t = insert(t, "\nREQUIRED_FACTS = {\n", "", reqfacts)
t = insert(t, "\nTASKS = {\n", fac_defs, fac_regs)
write(files["tasks"], t)

# ---- verifiers.py ----
t = read(files["verifiers"])
t = insert(t, "\nSUITE_FACTORIES = {\n",
           "\n\n\n".join(s["suite_code"].rstrip("\n") for s in specs),
           "".join(regline(s["suite_registry_line"]) for s in specs))
write(files["verifiers"], t)

# ---- oracle_agent.py ----
t = read(files["oracle"])
t = insert(t, "\nSOLVERS = {\n",
           "\n\n\n".join(s["solver_code"].rstrip("\n") for s in specs),
           "".join(regline(s["solver_registry_line"]) for s in specs))
write(files["oracle"], t)

# ---- facts.py ----
t = read(files["facts"])
t = insert(t, "\nFACT_EXTRACTORS: dict[str, Callable[[dict, str], dict]] = {\n",
           "\n\n\n".join(s["facts_code"].rstrip("\n") for s in specs),
           "".join(regline(s["facts_registry_line"]) for s in specs))
write(files["facts"], t)

# ---- tests: append blocks ----
t = read(files["tests"])
blob = "\n\n\n".join(s["test_code"].rstrip("\n") for s in specs)
write(files["tests"], t.rstrip("\n") + "\n\n\n" + blob + "\n")

# ---- compile gate ----
r = subprocess.run([sys.executable, "-m", "py_compile", *files.values()],
                   capture_output=True, text=True)
if r.returncode != 0:
    print("PY_COMPILE FAIL — restoring backups\n", r.stderr[-3500:])
    for p in files.values():
        shutil.copyfile(p + ".precset.bak", p)
    sys.exit(1)
print("PY_COMPILE OK — integrated:", [s["id"] for s in specs])
