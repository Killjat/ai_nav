"""检查页面实际结构，找到正确的选择器"""
import json
from playwright.sync_api import sync_playwright

with open("checked.json") as f:
    data = json.load(f)

sites = [d["url"] for d in data if d.get("is_active") and d.get("text_to_image")][:8]

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    for url in sites:
        page = browser.new_page(ignore_https_errors=True)
        try:
            page.goto(url, timeout=15000, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)

            textareas = page.locator("textarea").all()
            inputs = page.locator("input[type=text]").all()
            buttons = page.locator("button").all()

            print(f"\n{'='*60}")
            print(f"URL: {url}")
            print(f"textarea:{len(textareas)}  input[text]:{len(inputs)}  button:{len(buttons)}")

            for ta in textareas[:3]:
                try:
                    ph = ta.get_attribute("placeholder") or ""
                    nm = ta.get_attribute("name") or ""
                    cls = ta.get_attribute("class") or ""
                    print(f"  [textarea] placeholder={ph!r} name={nm!r} class={cls[:40]!r}")
                except Exception:
                    pass

            for inp in inputs[:3]:
                try:
                    ph = inp.get_attribute("placeholder") or ""
                    nm = inp.get_attribute("name") or ""
                    print(f"  [input] placeholder={ph!r} name={nm!r}")
                except Exception:
                    pass

            for btn in buttons[:6]:
                try:
                    txt = btn.inner_text().strip()[:40]
                    if txt:
                        print(f"  [button] {txt!r}")
                except Exception:
                    pass

        except Exception as e:
            print(f"{url} -> ERROR: {e}")
        finally:
            page.close()

    browser.close()
