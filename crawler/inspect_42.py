from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(ignore_https_errors=True, viewport={"width": 1280, "height": 900})
    page.goto("https://42.193.219.6", timeout=15000, wait_until="domcontentloaded")
    page.wait_for_timeout(3000)

    buttons = page.locator("button").all()
    print("按钮列表:")
    for i, btn in enumerate(buttons):
        try:
            txt = btn.inner_text().strip()
            visible = btn.is_visible()
            onclick = btn.get_attribute("onclick") or ""
            print(f"  [{i}] visible={visible} text={repr(txt)} onclick={repr(onclick)}")
        except Exception as e:
            print(f"  [{i}] error={e}")

    print("\ntextarea 列表:")
    tas = page.locator("textarea").all()
    for i, ta in enumerate(tas):
        ph = ta.get_attribute("placeholder") or ""
        visible = ta.is_visible()
        print(f"  [{i}] visible={visible} placeholder={repr(ph)}")

    browser.close()
