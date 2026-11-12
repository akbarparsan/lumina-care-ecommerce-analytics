"""Membangun docs/DAX_REFERENSI.md dari berkas DAX (sumber kebenaran tunggal, agar dokumen tidak menyimpang dari kode)."""
import re, pathlib
root = pathlib.Path(__file__).resolve().parent.parent
files = [("measures.dax", "Model inti (82 measure)"), ("measures_dashboard.dax", "Dashboard (Command Center, Analisis, Recovery & Kepatuhan)")]
name_re = re.compile(r'^([A-Z][A-Za-z0-9 %\.\-\(\)\+\*]*?)\s*=(\s.*|)$')
head_re = re.compile(r'^//\s*-{4,}\s*(.+?)\s*$')
head2_re = re.compile(r'^//\s*(HALAMAN [A-Z &]+.*|TAMBAHAN HASIL.*)$')

def parse(path):
    groups, order, cur = {}, [], "Umum"
    lines = path.read_text(encoding="utf-8").split("\n")
    i = 0
    while i < len(lines):
        ln = lines[i]
        m = head_re.match(ln) or head2_re.match(ln)
        if m and not ln.startswith("// ====="):
            cur = re.sub(r'\s*\(.*$', '', m.group(1)).strip(' :-') or cur
        mm = name_re.match(ln)
        if mm and not ln.startswith(("//", "VAR ", "RETURN")) and not ln.lstrip().startswith("//"):
            name, rest = mm.group(1).strip(), mm.group(2).strip()
            body = [rest] if rest else []
            j = i + 1
            while j < len(lines) and lines[j].strip() and not lines[j].lstrip().startswith("//") and (lines[j].startswith(("VAR ", "RETURN")) or not name_re.match(lines[j])):
                body.append(lines[j].strip()); j += 1
            code = " ".join(body)
            if cur not in groups: groups[cur] = []; order.append(cur)
            groups[cur].append((name, code))
            i = j; continue
        i += 1
    return groups, order

out = ["# Referensi DAX", "",
       "Dokumen ini dibangkitkan otomatis dari `powerbi/measures.dax` dan `powerbi/measures_dashboard.dax` oleh `gen/make_dax_reference.py`. "
       "Kode lengkap ada di kedua berkas itu; di sini ringkasannya per kelompok. Rumus satu baris ditampilkan utuh, rumus panjang diberi tanda *(lihat berkas)*.", ""]
total = 0
for fn, title in files:
    groups, order = parse(root / "powerbi" / fn)
    n = sum(len(v) for v in groups.values()); total += n
    out += [f"## {title} — `{fn}` ({n} measure)", ""]
    for g in order:
        items = groups[g]
        out += [f"### {g} ({len(items)})", "", "| Measure | Rumus |", "|---|---|"]
        for name, code in items:
            code = code.strip()
            show = "*(lihat berkas)*" if len(code) > 140 or "VAR " in code[:6] else f"`{code.replace('|','\\|')}`"
            out.append(f"| {name} | {show} |")
        out.append("")
out.insert(3, f"**Total: {total} measure.**\n")
(root / "docs" / "DAX_REFERENSI.md").write_text("\n".join(out), encoding="utf-8")
print("ok", total)
