#!/usr/bin/env python3
"""Build a single-file HTML dashboard for Observer knowledge cards."""

import json
import os
import re
import yaml
from pathlib import Path
from datetime import datetime

ARCHIVE_DIR = Path(os.environ.get(
    "OBSERVER_ARCHIVE",
    os.path.expanduser("~/.openclaw/workspace-observer/archive")
))
OUTPUT = Path(os.environ.get(
    "DASHBOARD_OUTPUT",
    os.path.expanduser("~/projects/openviking-local/dashboard.html")
))


def parse_card(filepath: Path) -> dict:
    text = filepath.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return None

    try:
        end = text.index("---", 3)
        meta = yaml.safe_load(text[3:end])
        if not meta or not isinstance(meta, dict):
            raise ValueError("empty")
    except Exception:
        meta = {}
        for key in ["title", "source", "score", "date", "url"]:
            m = re.search(rf"^{key}:\s*(.+)", text, re.M)
            if m:
                val = m.group(1).strip().strip('"')
                meta[key] = (int(val) if key == "score" and val.isdigit()
                             else val)
        topics_m = re.search(r"^topics:\s*\[(.+?)\]", text, re.M)
        if topics_m:
            meta["topics"] = [
                t.strip() for t in topics_m.group(1).split(",")]

    card = {
        "title": str(meta.get("title", filepath.stem))[:120],
        "source": str(meta.get("source", "?")),
        "url": str(meta.get("url", "")),
        "date": str(meta.get("date", ""))[:10],
        "score": (int(meta.get("score", 0))
                  if isinstance(meta.get("score"), (int, float)) else 0),
        "topics": (meta.get("topics", [])
                   if isinstance(meta.get("topics"), list) else []),
        "highlights": (meta.get("highlights", [])
                       if isinstance(meta.get("highlights"), list) else []),
        "summary": str(meta.get("summary", "")),
        "golden_quote": str(meta.get("golden_quote", "")),
        "action": str(meta.get("action", "none")),
        "entities": meta.get("entities", {}),
        "datapoints": (meta.get("datapoints", [])
                       if isinstance(meta.get("datapoints"), list) else []),
        "quotes": (meta.get("quotes", [])
                   if isinstance(meta.get("quotes"), list) else []),
        "file": filepath.name,
    }
    card["topics"] = [str(t) for t in card["topics"]]
    return card


def build_html(cards: list) -> str:
    all_sources = sorted(set(c["source"] for c in cards))
    all_topics = sorted(set(t for c in cards for t in c["topics"]))

    cards_json = json.dumps(cards, ensure_ascii=False, indent=None)

    src_opts = "\n".join(
        f'<option value="{s}">{s}</option>' for s in all_sources)
    tp_opts = "\n".join(
        f'<option value="{t}">{t}</option>' for t in all_topics[:50])

    return f"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Observer Knowledge Cards</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,'PingFang SC',sans-serif;background:#0d1117;color:#c9d1d9}}
.header{{padding:16px 24px;background:#161b22;border-bottom:1px solid #30363d;display:flex;align-items:center;gap:16px;flex-wrap:wrap}}
.header h1{{font-size:18px;color:#58a6ff;white-space:nowrap}}
.stats{{font-size:13px;color:#8b949e}}
.filters{{padding:12px 24px;background:#161b22;border-bottom:1px solid #30363d;display:flex;gap:12px;flex-wrap:wrap;align-items:center}}
.filters label{{font-size:12px;color:#8b949e}}
.filters select,.filters input{{background:#0d1117;color:#c9d1d9;border:1px solid #30363d;border-radius:6px;padding:4px 8px;font-size:13px}}
.filters input[type=text]{{width:200px}}
.filters select{{min-width:120px}}
.grid{{padding:16px 24px;display:grid;grid-template-columns:repeat(auto-fill,minmax(380px,1fr));gap:12px}}
.card{{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:14px;cursor:pointer;transition:border-color .2s}}
.card:hover{{border-color:#58a6ff}}
.card-head{{display:flex;justify-content:space-between;align-items:flex-start;gap:8px;margin-bottom:8px}}
.card-title{{font-size:14px;font-weight:600;color:#e6edf3;line-height:1.4;flex:1}}
.card-title a{{color:#58a6ff;text-decoration:none}}
.card-title a:hover{{text-decoration:underline}}
.score{{font-size:13px;font-weight:700;padding:2px 8px;border-radius:12px;white-space:nowrap}}
.score-high{{background:#1a7f37;color:#fff}}
.score-mid{{background:#9e6a03;color:#fff}}
.score-low{{background:#30363d;color:#8b949e}}
.card-meta{{font-size:12px;color:#8b949e;margin-bottom:8px}}
.card-meta span{{margin-right:12px}}
.topics{{display:flex;flex-wrap:wrap;gap:4px;margin-bottom:8px}}
.topic{{font-size:11px;background:#1f2937;color:#7ee787;padding:2px 8px;border-radius:10px}}
.card-body{{font-size:13px;color:#8b949e;line-height:1.5}}
.card-body.collapsed{{max-height:60px;overflow:hidden}}
.highlights{{list-style:none;padding:0}}
.highlights li{{padding:2px 0;padding-left:12px;position:relative}}
.highlights li::before{{content:'\\2022';position:absolute;left:0;color:#58a6ff}}
.detail{{margin-top:8px;padding-top:8px;border-top:1px solid #21262d}}
.detail-section{{margin-bottom:6px}}
.detail-label{{font-size:11px;color:#58a6ff;text-transform:uppercase;letter-spacing:.5px}}
.detail-value{{font-size:12px;color:#c9d1d9}}
.entity-tag{{font-size:11px;background:#1c2333;color:#a5d6ff;padding:1px 6px;border-radius:4px;margin-right:4px}}
.quote{{font-style:italic;color:#8b949e;border-left:2px solid #30363d;padding-left:8px;margin:4px 0;font-size:12px}}
.sort-bar{{padding:8px 24px;display:flex;gap:8px;align-items:center;font-size:12px;color:#8b949e}}
.sort-btn{{background:none;border:1px solid #30363d;color:#8b949e;padding:3px 10px;border-radius:4px;cursor:pointer;font-size:12px}}
.sort-btn.active{{background:#1f6feb;color:#fff;border-color:#1f6feb}}
.empty{{padding:60px;text-align:center;color:#484f58;font-size:15px}}
</style>
</head>
<body>
<div class="header">
  <h1>Observer Knowledge Cards</h1>
  <span class="stats" id="stats"></span>
</div>
<div class="filters">
  <div><label>Search</label><br><input type="text" id="q" placeholder="title / summary / entity..."></div>
  <div><label>Source</label><br><select id="src"><option value="">All</option>{src_opts}</select></div>
  <div><label>Score</label><br><select id="sc"><option value="">All</option><option value="85">85+</option><option value="70">70+</option><option value="50">50+</option></select></div>
  <div><label>Topic</label><br><select id="tp"><option value="">All</option>{tp_opts}</select></div>
  <div><label>Action</label><br><select id="act"><option value="">All</option><option value="alert">alert</option><option value="analyze">analyze</option></select></div>
</div>
<div class="sort-bar">
  Sort:
  <button class="sort-btn active" data-sort="score">Score</button>
  <button class="sort-btn" data-sort="date">Date</button>
  <button class="sort-btn" data-sort="title">Title</button>
</div>
<div class="grid" id="grid"></div>
<script>
const CARDS={cards_json};
let sortKey='score',sortDir=-1,expanded=new Set();
function render(){{const q=document.getElementById('q').value.toLowerCase();const src=document.getElementById('src').value;const sc=parseInt(document.getElementById('sc').value)||0;const tp=document.getElementById('tp').value;const act=document.getElementById('act').value;let filtered=CARDS.filter(c=>{{if(src&&c.source!==src)return false;if(sc&&c.score<sc)return false;if(tp&&!c.topics.includes(tp))return false;if(act&&c.action!==act)return false;if(q){{const hay=(c.title+' '+c.summary+' '+c.source+' '+c.topics.join(' ')+' '+JSON.stringify(c.entities)).toLowerCase();if(!hay.includes(q))return false;}}return true;}});filtered.sort((a,b)=>{{let va=a[sortKey],vb=b[sortKey];if(typeof va==='string')return sortDir*va.localeCompare(vb);return sortDir*((va||0)-(vb||0));}});document.getElementById('stats').textContent=filtered.length+' / '+CARDS.length+' cards';const grid=document.getElementById('grid');if(!filtered.length){{grid.innerHTML='<div class="empty">No cards match filters</div>';return;}}grid.innerHTML=filtered.map((c,i)=>{{const scClass=c.score>=85?'score-high':c.score>=70?'score-mid':'score-low';const isExp=expanded.has(c.file);const hl=(c.highlights||[]).map(h=>'<li>'+esc(h)+'</li>').join('');let detail='';if(isExp){{detail='<div class="detail">';if(c.summary)detail+='<div class="detail-section"><div class="detail-label">Summary</div><div class="detail-value">'+esc(c.summary)+'</div></div>';if(c.entities&&(c.entities.people?.length||c.entities.orgs?.length||c.entities.products?.length)){{detail+='<div class="detail-section"><div class="detail-label">Entities</div><div class="detail-value">';for(const[k,v]of Object.entries(c.entities)){{if(v&&v.length)detail+=v.map(e=>'<span class="entity-tag">'+esc(k.slice(0,-1))+': '+esc(e)+'</span>').join('');}}detail+='</div></div>';}}if(c.quotes?.length){{detail+='<div class="detail-section"><div class="detail-label">Quotes</div>';detail+=c.quotes.map(q=>'<div class="quote">'+esc(q)+'</div>').join('');detail+='</div>';}}if(c.datapoints?.length){{detail+='<div class="detail-section"><div class="detail-label">Data Points</div><div class="detail-value">'+c.datapoints.map(d=>esc(d)).join(' | ')+'</div></div>';}}if(c.golden_quote)detail+='<div class="detail-section"><div class="detail-label">Golden Quote</div><div class="quote">'+esc(c.golden_quote)+'</div></div>';detail+='</div>';}}return'<div class="card" data-file="'+c.file+'">'+'<div class="card-head">'+'<div class="card-title">'+(c.url?'<a href="'+c.url+'" target="_blank">'+esc(c.title)+'</a>':esc(c.title))+'</div>'+'<span class="score '+scClass+'">'+c.score+'</span>'+'</div>'+'<div class="card-meta"><span>'+esc(c.source)+'</span><span>'+c.date+'</span>'+(c.action!=='none'?'<span style="color:#f0883e">'+c.action+'</span>':'')+'</div>'+'<div class="topics">'+c.topics.map(t=>'<span class="topic">'+esc(t)+'</span>').join('')+'</div>'+'<div class="card-body'+(isExp?'':' collapsed')+'"><ul class="highlights">'+hl+'</ul>'+detail+'</div>'+'</div>';}}).join('');grid.querySelectorAll('.card').forEach(el=>{{el.addEventListener('click',e=>{{if(e.target.tagName==='A')return;const f=el.dataset.file;expanded.has(f)?expanded.delete(f):expanded.add(f);render();}});}});}}
function esc(s){{return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}}
document.querySelectorAll('#q,#src,#sc,#tp,#act').forEach(el=>el.addEventListener('input',render));
document.querySelectorAll('.sort-btn').forEach(btn=>{{btn.addEventListener('click',()=>{{const s=btn.dataset.sort;if(sortKey===s)sortDir*=-1;else{{sortKey=s;sortDir=s==='title'?1:-1;}}document.querySelectorAll('.sort-btn').forEach(b=>b.classList.remove('active'));btn.classList.add('active');render();}});}});
render();
</script>
</body>
</html>"""


def main():
    cards = []
    if ARCHIVE_DIR.exists():
        for month_dir in sorted(ARCHIVE_DIR.iterdir()):
            if not month_dir.is_dir():
                continue
            for f in sorted(month_dir.glob("*.md")):
                card = parse_card(f)
                if card:
                    cards.append(card)

    print(f"Parsed {len(cards)} cards")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    html = build_html(cards)
    OUTPUT.write_text(html, encoding="utf-8")
    print(f"Dashboard: {OUTPUT}")
    print(f"Size: {OUTPUT.stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main()
