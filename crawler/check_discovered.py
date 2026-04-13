import json

data = json.load(open("discovered_sites.json"))
success = [d for d in data if d.get("success")]
has_prompt = [d for d in data if d.get("structure", {}).get("prompt_candidates")]

print(f"已处理: {len(data)}")
print(f"有 prompt 输入框: {len(has_prompt)}")
print(f"生图成功: {len(success)}")

print("\n--- 有 prompt 的站点 ---")
for d in has_prompt:
    print(f"\n  {d['url']}")
    for p in d["structure"]["prompt_candidates"][:2]:
        print(f"    prompt_sel: {p['selector']}  visible={p['visible']}")
    for b in d["structure"]["button_candidates"][:4]:
        print(f"    button: {repr(b['text'][:30])}  onclick={repr(b['onclick'][:30])}")
    tabs = d["structure"].get("tabs", [])
    if tabs:
        print(f"    tabs: {tabs}")
