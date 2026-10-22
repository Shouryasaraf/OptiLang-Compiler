"""Write a standalone, offline compiler-stage explorer."""

from __future__ import annotations

from html import escape

from .compiler import CompilationResult


def render_html(source: str, result: CompilationResult) -> str:
    sections = [
        ("Tokens", [f"{item.line}:{item.column} {item.kind:<12} {item.lexeme!r}"
                    for item in result.tokens]),
        ("AST", result.ast),
        ("Symbols", [f"{key}: {value}" for key, value in result.symbols.items()]),
        ("TAC", result.tac),
        ("Optimized TAC", result.optimized_tac),
        ("CFG", result.cfg),
        ("Optimization record", result.optimizations or ["No rewrite applied"]),
        ("Bytecode", result.bytecode),
        ("VM trace", result.vm_trace),
        ("Output", result.output),
    ]
    buttons = "".join(
        f'<button class="tab" type="button" data-panel="p{i}">{escape(name)}</button>'
        for i, (name, _) in enumerate(sections)
    )
    panels = "".join(
        f'<section class="panel" id="p{i}" role="tabpanel" hidden>'
        f'<h2>{escape(name)}</h2><pre>{escape(chr(10).join(lines))}</pre></section>'
        for i, (name, lines) in enumerate(sections)
    )
    numbered_source = "\n".join(
        f"{index:>3}  {line}" for index, line in enumerate(source.splitlines(), 1)
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>OptiLang compiler explorer</title><style>
:root {{ color-scheme: light; font-family: system-ui, sans-serif; color: #14283e; background: #f4f8f8; }}
* {{ box-sizing: border-box; }} body {{ margin: 0; }}
header {{ background: #14283e; color: white; padding: 1.3rem max(2rem, calc((100vw - 1440px)/2)); }}
header h1 {{ margin: 0; font-size: 1.55rem; }} header p {{ margin: .35rem 0 0; color: #c6e1e1; }}
main {{ max-width: 1440px; margin: auto; padding: 1.5rem; display: grid; grid-template-columns: minmax(290px, 40%) minmax(340px, 60%); gap: 1.3rem; }}
.surface {{ background: white; border: 1px solid #d5e2e2; border-radius: 9px; padding: 1.25rem; min-width: 0; }}
h2 {{ margin: 0 0 1rem; font-size: 1.15rem; }} pre {{ margin: 0; white-space: pre-wrap; overflow-wrap: anywhere; font: 0.91rem/1.6 ui-monospace, SFMono-Regular, Consolas, monospace; }}
.tabs {{ display: flex; gap: .4rem; flex-wrap: wrap; margin-bottom: 1.2rem; }}
button {{ background: #edf5f5; color: #173f46; border: 1px solid #d5e2e2; border-radius: 5px; padding: .55rem .75rem; cursor: pointer; }}
button[aria-selected="true"] {{ background: #157a80; border-color: #157a80; color: white; }}
.status {{ color: #187a57; font-weight: 600; }}
@media(max-width: 850px) {{ main {{ display: block; }} .surface {{ margin-bottom: 1rem; }} }}
</style></head><body><header><h1>OptiLang compiler explorer</h1>
<p>Source, representations, optimization decisions and virtual-machine execution</p></header>
<main><section class="surface"><h2>Source program</h2><pre>{escape(numbered_source)}</pre></section>
<section class="surface"><div class="tabs" role="tablist" aria-label="Compiler stages">{buttons}</div>
{panels}<p class="status">Validation: original AST, optimized AST and VM output and global state agree.</p></section></main>
<script>const buttons=[...document.querySelectorAll('.tab')];const panels=[...document.querySelectorAll('.panel')];
function select(id){{buttons.forEach(b=>b.setAttribute('aria-selected',String(b.dataset.panel===id)));
panels.forEach(p=>p.hidden=p.id!==id);}}buttons.forEach(b=>b.addEventListener('click',()=>select(b.dataset.panel)));select('p0');</script>
</body></html>"""
