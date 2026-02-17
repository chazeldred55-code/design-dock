from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# Folder where your static previews live
OUT_DIR = Path("products/static/products/product_images")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Paste your DB-expected filenames here (exactly)
FILENAMES = [
    "250-reusable-web-components.png",
    "minimal-portfolio-template.png",
    "saas-startup-website-template.png",
    "creative-agency-template.png",
    "personal-brand-website-template.png",
    "product-showcase-template.png",
    "modern-saas-ui-kit.png",
    "dark-mode-dashboard-ui-kit.png",
    "glassmorphism-ui-kit.png",
    "minimalist-web-ui-kit.png",
    "mobile-app-ui-kit.png",
    "finance-admin-dashboard.png",
    "saas-analytics-dashboard.png",
    "e-commerce-admin-panel.png",
    "crm-dashboard-template.png",
    "project-management-dashboard.png",
    "fashion-e-commerce-ui-kit.png",
    "subscription-saas-store-template.png",
    "digital-product-marketplace-template.png",
    "modern-storefront-template.png",
    "advanced-form-components-pack.png",
    "modal-overlay-system-kit.png",
    "navigation-mega-menu-pack.png",
    "pricing-table-component-suite.png",
    "headless-commerce-starter.png",
    "saas-conversion-landing-page.png",
    "app-launch-landing-page.png",
    "ai-startup-landing-template.png",
    "web3-product-landing-page.png",
    "agency-lead-capture-template.png",
    "macbook-ui-mockup-set.png",
    "iphone-app-presentation-mockups.png",
    "browser-window-mockup-pack.png",
    "branding-stationery-mockups.png",
    "social-media-post-mockups.png",
    "token-based-design-system.png",
    "enterprise-ui-foundation-kit.png",
    "atomic-component-system.png",
    "accessible-design-system-starter.png",
    "dark-light-mode-system-kit.png",
]

# Image size (good for your grid and detail pages)
W, H = 1200, 800

def title_from_filename(fn: str) -> str:
    base = fn.replace(".png", "").replace("-", " ").strip()
    return " ".join(word.capitalize() for word in base.split())

def draw_centered_text(draw, text, font, box, fill=(255, 255, 255)):
    x0, y0, x1, y1 = box
    w = x1 - x0
    y = y0
    lines = []
    words = text.split()

    # basic line wrap
    line = ""
    for word in words:
        test = (line + " " + word).strip()
        tw = draw.textlength(test, font=font)
        if tw <= w:
            line = test
        else:
            if line:
                lines.append(line)
            line = word
    if line:
        lines.append(line)

    # vertically center block
    line_h = font.size + 10
    total_h = line_h * len(lines)
    y = y0 + (y1 - y0 - total_h) // 2

    for ln in lines:
        tw = draw.textlength(ln, font=font)
        x = x0 + (w - tw) // 2
        draw.text((x, y), ln, font=font, fill=fill)
        y += line_h

def make_card(filename: str):
    path = OUT_DIR / filename
    if path.exists():
        return 0  # don't overwrite existing real images

    img = Image.new("RGB", (W, H), (15, 18, 24))
    draw = ImageDraw.Draw(img)

    # simple “design dock” style frame
    pad = 60
    draw.rounded_rectangle(
        (pad, pad, W - pad, H - pad),
        radius=36,
        outline=(80, 90, 110),
        width=4,
    )

    # top label
    label = "DESIGN DOCK PREVIEW"
    try:
        font_small = ImageFont.truetype("arial.ttf", 26)
        font_big = ImageFont.truetype("arial.ttf", 58)
    except:
        font_small = ImageFont.load_default()
        font_big = ImageFont.load_default()

    draw.text((pad + 30, pad + 22), label, font=font_small, fill=(170, 180, 200))

    # main title
    title = title_from_filename(filename)
    box = (pad + 30, pad + 110, W - pad - 30, H - pad - 60)
    draw_centered_text(draw, title, font_big, box, fill=(240, 245, 255))

    img.save(path, "PNG")
    return 1

created = 0
for fn in FILENAMES:
    created += make_card(fn)

print(f"Created {created} placeholder previews in: {OUT_DIR}")
