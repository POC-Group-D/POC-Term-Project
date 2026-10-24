"""Generate the extended Online Boutique catalog (200 products).

Keeps the 9 upstream products unchanged and adds 191 new ones across 17
product groups, so recommendations have realistic choices to make.

Outputs (both committed, regenerate with `python generate_catalog.py`):
  productcatalogservice/products.json         catalog served by productcatalogservice
  frontend/static/img/products/generated/*.svg  one placeholder picture per new product

Everything is deterministic: ids are derived from product names and prices
are fixed in the table below, so regenerating produces identical files.
"""

import hashlib
import json
import re
from pathlib import Path
from textwrap import wrap

HERE = Path(__file__).resolve().parent
UPSTREAM_CATALOG = HERE.parent / "online-boutique/src/productcatalogservice/products.json"
CATALOG_OUT = HERE / "productcatalogservice/products.json"
IMAGES_OUT = HERE / "frontend/static/img/products/generated"
PICTURE_URL = "/static/img/products/generated/{slug}.svg"

# (categories, picture colour, [(name, description, price in USD), ...])
GROUPS = [
    (["kitchen", "cookware"], "#c0573e", [
        ("Cast Iron Skillet", "Pre-seasoned 10-inch skillet that goes from stovetop to oven.", 34.99),
        ("Chef's Knife", "8-inch stainless steel chef's knife with a balanced handle.", 49.99),
        ("Bamboo Cutting Board", "Large reversible bamboo board with a juice groove.", 24.99),
        ("Nonstick Frying Pan", "Lightweight 11-inch pan with a ceramic nonstick coating.", 29.99),
        ("Dutch Oven", "Enamelled 5-quart Dutch oven for stews, bread and braises.", 79.99),
        ("Wooden Spoon Set", "Three olive-wood spoons for stirring, tasting and serving.", 16.99),
        ("Mixing Bowl Set", "Nesting stainless steel bowls in three sizes with lids.", 27.99),
        ("Silicone Spatula", "Heat-resistant spatula that will not scratch nonstick pans.", 8.99),
        ("Stainless Saucepan", "2-quart saucepan with a glass lid and pour spouts.", 39.99),
        ("Kitchen Scale", "Digital scale accurate to one gram, with a tare button.", 19.99),
        ("Herb Scissors", "Five-blade scissors that chop fresh herbs in seconds.", 11.99),
        ("Garlic Press", "Heavy-duty press that crushes cloves without peeling.", 13.99),
        ("Linen Apron", "Washed linen apron with a front pocket and adjustable strap.", 26.99),
        ("Ceramic Dinner Plates", "Set of four speckled stoneware dinner plates.", 44.99),
        ("Pasta Bowls", "Set of four wide, shallow bowls for pasta and salads.", 38.99),
        ("Olive Oil Dispenser", "Glass bottle with a drip-free pour spout for oils.", 15.99),
    ]),
    (["kitchen", "coffee"], "#7a4e2d", [
        ("French Press", "Glass and steel French press that brews four cups.", 32.99),
        ("Pour-Over Coffee Dripper", "Ceramic cone dripper for a clean, bright cup.", 22.99),
        ("Burr Coffee Grinder", "Hand grinder with adjustable steel burrs.", 44.99),
        ("Gooseneck Kettle", "Precision-pour kettle for pour-over coffee and tea.", 39.99),
        ("Espresso Cups", "Set of four double-walled glass espresso cups.", 21.99),
        ("Travel Coffee Mug", "Insulated stainless mug that keeps drinks hot for hours.", 24.99),
        ("Tea Infuser", "Fine-mesh stainless infuser for loose-leaf tea.", 9.99),
        ("Ceramic Teapot", "Hand-glazed teapot with a removable infuser basket.", 34.99),
        ("Milk Frother", "Battery-powered whisk for foamy lattes at home.", 14.99),
        ("Coffee Canister", "Airtight canister that keeps beans fresh longer.", 19.99),
        ("Loose Leaf Green Tea", "Tin of organic sencha green tea, 100 g.", 12.99),
        ("Whole Bean Coffee", "Medium roast single-origin beans, 340 g bag.", 16.99),
    ]),
    (["decor", "home"], "#5b6c8f", [
        ("Linen Throw Pillow", "Soft washed-linen cushion cover with an insert.", 29.99),
        ("Ceramic Vase", "Matte white vase for fresh or dried flowers.", 32.99),
        ("Wall Mirror", "Round mirror with a thin brass frame, 60 cm.", 89.99),
        ("Woven Basket", "Seagrass storage basket with handles.", 27.99),
        ("Table Lamp", "Ceramic table lamp with a linen shade.", 64.99),
        ("Scented Soy Candle", "Hand-poured candle with notes of cedar and fig.", 22.99),
        ("Picture Frame Set", "Three black frames for 5x7 and 8x10 photos.", 34.99),
        ("Faux Olive Tree", "Realistic potted olive tree, 120 cm tall.", 119.99),
        ("Wool Throw Blanket", "Chunky knit throw blanket for the sofa.", 74.99),
        ("Wall Clock", "Minimal wooden wall clock with a silent movement.", 39.99),
        ("Bookends", "Pair of heavy marble bookends.", 29.99),
        ("Jute Area Rug", "Hand-woven jute rug, 120 x 180 cm.", 99.99),
        ("Brass Candlesticks", "Set of two brass candlesticks for taper candles.", 26.99),
        ("Terracotta Planter", "Indoor plant pot with a drainage saucer.", 18.99),
    ]),
    (["home", "bath"], "#3f8f8b", [
        ("Cotton Bath Towels", "Set of two plush Turkish cotton bath towels.", 44.99),
        ("Linen Sheet Set", "Breathable stonewashed linen sheets, queen size.", 149.99),
        ("Down Alternative Pillow", "Hypoallergenic pillow with a cotton cover.", 39.99),
        ("Bath Mat", "Absorbent cotton bath mat with a non-slip back.", 24.99),
        ("Shower Curtain", "Waffle-weave cotton shower curtain.", 34.99),
        ("Waffle Bathrobe", "Lightweight waffle cotton robe.", 59.99),
        ("Duvet Cover", "Percale duvet cover with button closure, queen size.", 89.99),
        ("Soap Dispenser", "Refillable ceramic soap dispenser.", 17.99),
        ("Weighted Blanket", "7 kg blanket for calmer sleep.", 119.99),
        ("Laundry Hamper", "Collapsible cotton hamper with leather handles.", 32.99),
        ("Bamboo Bath Tray", "Expandable bath caddy for books and drinks.", 36.99),
        ("Silk Pillowcase", "Mulberry silk pillowcase that is gentle on hair and skin.", 39.99),
    ]),
    (["clothing", "tops"], "#b5577b", [
        ("Crew Neck T-Shirt", "Everyday organic cotton tee.", 22.99),
        ("Oxford Shirt", "Button-down cotton Oxford shirt.", 49.99),
        ("Linen Shirt", "Relaxed-fit linen shirt for warm days.", 54.99),
        ("Merino Sweater", "Fine-knit merino wool crew neck sweater.", 89.99),
        ("Hooded Sweatshirt", "Brushed fleece hoodie with a kangaroo pocket.", 54.99),
        ("Striped Breton Top", "Classic long-sleeve striped cotton top.", 39.99),
        ("Silk Blouse", "Washable silk blouse with a relaxed fit.", 79.99),
        ("Polo Shirt", "Pique cotton polo shirt.", 39.99),
        ("Cardigan", "Soft cotton cardigan with horn buttons.", 64.99),
        ("Turtleneck", "Slim ribbed turtleneck.", 44.99),
        ("Flannel Shirt", "Brushed cotton plaid flannel shirt.", 49.99),
        ("Henley Shirt", "Long-sleeve waffle-knit henley.", 34.99),
        ("Workout Tank", "Moisture-wicking tank top for training.", 24.99),
        ("Denim Shirt", "Washed chambray denim shirt.", 54.99),
    ]),
    (["clothing", "bottoms"], "#8a4f9e", [
        ("Slim Jeans", "Stretch denim jeans in a dark wash.", 69.99),
        ("Chino Pants", "Garment-dyed cotton chinos.", 59.99),
        ("Linen Trousers", "Drawstring linen trousers.", 64.99),
        ("Jogger Pants", "Fleece joggers with a tapered leg.", 49.99),
        ("Denim Shorts", "Mid-rise denim shorts.", 39.99),
        ("Pleated Skirt", "Midi pleated skirt with an elastic waist.", 54.99),
        ("Yoga Leggings", "High-waisted leggings with pockets.", 44.99),
        ("Cargo Pants", "Utility cargo pants in ripstop cotton.", 64.99),
        ("Wool Trousers", "Tailored wool-blend trousers.", 89.99),
        ("Swim Trunks", "Quick-dry swim trunks with a mesh lining.", 34.99),
    ]),
    (["clothing", "outerwear"], "#4f6d3a", [
        ("Rain Jacket", "Waterproof, breathable shell with a packable hood.", 99.99),
        ("Denim Jacket", "Classic trucker jacket in a medium wash.", 79.99),
        ("Puffer Jacket", "Lightweight insulated puffer jacket.", 129.99),
        ("Wool Overcoat", "Single-breasted wool-blend overcoat.", 199.99),
        ("Fleece Jacket", "Recycled polyester fleece full-zip.", 59.99),
        ("Trench Coat", "Water-resistant cotton trench coat.", 169.99),
        ("Bomber Jacket", "Nylon bomber jacket with ribbed cuffs.", 89.99),
        ("Quilted Vest", "Lightweight quilted vest for layering.", 64.99),
        ("Leather Jacket", "Lambskin leather moto jacket.", 249.99),
        ("Windbreaker", "Packable windbreaker for running and travel.", 54.99),
    ]),
    (["footwear"], "#6b5b4b", [
        ("White Sneakers", "Minimal leather sneakers that go with everything.", 89.99),
        ("Running Shoes", "Cushioned running shoes with a breathable mesh upper.", 119.99),
        ("Chelsea Boots", "Suede Chelsea boots with elastic sides.", 139.99),
        ("Canvas Slip-Ons", "Easy canvas slip-on shoes.", 44.99),
        ("Hiking Boots", "Waterproof boots with a grippy outsole.", 149.99),
        ("Leather Sandals", "Slide sandals with a contoured footbed.", 59.99),
        ("Wool Slippers", "Felted wool slippers for the house.", 39.99),
        ("Ankle Boots", "Leather ankle boots with a block heel.", 129.99),
        ("Espadrilles", "Canvas espadrilles with jute soles.", 49.99),
        ("Rain Boots", "Rubber rain boots with a cotton lining.", 64.99),
        ("Dress Shoes", "Polished leather Oxford dress shoes.", 159.99),
        ("Wool Socks", "Pack of three cushioned merino wool socks.", 24.99),
    ]),
    (["accessories"], "#c49a2c", [
        ("Wool Beanie", "Ribbed merino wool beanie.", 24.99),
        ("Baseball Cap", "Washed cotton cap with an adjustable strap.", 22.99),
        ("Cashmere Scarf", "Soft cashmere scarf in a solid colour.", 79.99),
        ("Leather Belt", "Full-grain leather belt with a brass buckle.", 44.99),
        ("Leather Gloves", "Touchscreen-compatible leather gloves.", 49.99),
        ("Straw Sun Hat", "Wide-brim straw hat for sunny days.", 34.99),
        ("Silk Tie", "Woven silk tie.", 39.99),
        ("Compact Umbrella", "Wind-resistant travel umbrella.", 27.99),
        ("Leather Wallet", "Slim bifold wallet with RFID blocking.", 49.99),
        ("Card Holder", "Minimal leather card holder.", 29.99),
        ("Bandana", "Printed cotton bandana.", 12.99),
        ("Key Ring", "Brass key ring with a leather loop.", 14.99),
    ]),
    (["accessories", "jewelry"], "#a0729c", [
        ("Gold Hoop Earrings", "Lightweight 14k gold-plated hoops.", 39.99),
        ("Pearl Necklace", "Freshwater pearl necklace on a gold chain.", 89.99),
        ("Silver Ring", "Sterling silver band ring.", 34.99),
        ("Charm Bracelet", "Adjustable bracelet with small gold charms.", 44.99),
        ("Stud Earrings", "Cubic zirconia stud earrings.", 24.99),
        ("Pendant Necklace", "Dainty pendant necklace with a crescent moon.", 49.99),
        ("Beaded Bracelet", "Stretch bracelet with natural stone beads.", 19.99),
        ("Signet Ring", "Polished signet ring in gold vermeil.", 69.99),
        ("Cufflinks", "Brushed silver cufflinks.", 49.99),
        ("Jewelry Box", "Velvet-lined travel jewelry case.", 34.99),
    ]),
    (["accessories", "bags"], "#5a4636", [
        ("Canvas Tote Bag", "Heavy canvas tote with an inner pocket.", 29.99),
        ("Leather Backpack", "Everyday leather backpack with a laptop sleeve.", 149.99),
        ("Crossbody Bag", "Compact leather crossbody bag.", 89.99),
        ("Weekender Bag", "Waxed canvas weekender with leather trim.", 129.99),
        ("Laptop Sleeve", "Padded felt sleeve for 14-inch laptops.", 34.99),
        ("Belt Bag", "Nylon belt bag for travel essentials.", 39.99),
        ("Toiletry Bag", "Water-resistant hanging toiletry bag.", 29.99),
        ("Messenger Bag", "Canvas messenger bag with a padded strap.", 79.99),
        ("Gym Duffel", "Duffel bag with a separate shoe compartment.", 59.99),
        ("Coin Purse", "Small leather zip coin purse.", 19.99),
    ]),
    (["beauty", "skincare"], "#d0857a", [
        ("Facial Cleanser", "Gentle gel cleanser for all skin types.", 18.99),
        ("Moisturizer", "Lightweight daily moisturizer with hyaluronic acid.", 29.99),
        ("Sunscreen SPF 50", "Broad-spectrum mineral sunscreen for the face.", 24.99),
        ("Lip Balm Set", "Three nourishing lip balms.", 12.99),
        ("Vitamin C Serum", "Brightening serum with 15% vitamin C.", 34.99),
        ("Hand Cream", "Rich shea butter hand cream.", 14.99),
        ("Body Lotion", "Unscented body lotion with oat extract.", 19.99),
        ("Face Mask Set", "Five hydrating sheet masks.", 16.99),
        ("Makeup Brush Set", "Eight soft synthetic makeup brushes.", 39.99),
        ("Perfume", "Eau de parfum with notes of bergamot and amber.", 89.99),
        ("Nail Polish Set", "Four long-wearing nail colours.", 22.99),
        ("Jade Face Roller", "Cooling jade roller for facial massage.", 24.99),
    ]),
    (["hair", "beauty"], "#9c6644", [
        ("Wide-Tooth Comb", "Handmade cellulose acetate comb.", 12.99),
        ("Boar Bristle Brush", "Brush that smooths and adds shine.", 29.99),
        ("Hair Straightener", "Ceramic flat iron with adjustable heat.", 59.99),
        ("Curling Iron", "1-inch ceramic curling iron.", 49.99),
        ("Silk Scrunchies", "Set of five silk scrunchies.", 19.99),
        ("Argan Hair Oil", "Nourishing oil for frizz control.", 24.99),
        ("Dry Shampoo", "Refreshing dry shampoo spray.", 14.99),
        ("Hair Clips", "Set of six tortoiseshell claw clips.", 16.99),
    ]),
    (["fitness", "sports"], "#2f7d5b", [
        ("Yoga Mat", "Non-slip 6 mm yoga mat with a carry strap.", 39.99),
        ("Adjustable Dumbbells", "Pair of dumbbells adjustable from 2 to 12 kg.", 149.99),
        ("Resistance Bands", "Set of five resistance bands with handles.", 24.99),
        ("Jump Rope", "Speed jump rope with ball bearings.", 14.99),
        ("Foam Roller", "High-density foam roller for recovery.", 29.99),
        ("Water Bottle", "Insulated 750 ml stainless steel bottle.", 27.99),
        ("Kettlebell", "Cast iron kettlebell, 12 kg.", 54.99),
        ("Yoga Blocks", "Pair of cork yoga blocks.", 24.99),
        ("Fitness Tracker Band", "Activity and sleep tracking wristband.", 69.99),
        ("Gym Towel", "Quick-dry microfibre gym towel.", 14.99),
    ]),
    (["outdoor", "travel"], "#3d6e8f", [
        ("Camping Tent", "Two-person lightweight backpacking tent.", 179.99),
        ("Sleeping Bag", "Three-season sleeping bag rated to -5 C.", 99.99),
        ("Headlamp", "Rechargeable LED headlamp, 400 lumens.", 34.99),
        ("Camping Mug", "Enamel camping mug.", 14.99),
        ("Picnic Blanket", "Water-resistant picnic blanket with a carry strap.", 39.99),
        ("Hiking Backpack", "28-litre daypack with a rain cover.", 89.99),
        ("Trekking Poles", "Collapsible aluminium trekking poles.", 59.99),
        ("Hammock", "Parachute nylon hammock with tree straps.", 49.99),
        ("Travel Pillow", "Memory foam neck pillow.", 24.99),
        ("Packing Cubes", "Set of four compression packing cubes.", 29.99),
    ]),
    (["office", "stationery"], "#4a5a7a", [
        ("Dotted Notebook", "A5 hardcover notebook with dotted pages.", 18.99),
        ("Fountain Pen", "Steel-nib fountain pen with a converter.", 34.99),
        ("Desk Organizer", "Wooden desk organizer with three compartments.", 29.99),
        ("Weekly Planner", "Undated weekly planner with a linen cover.", 22.99),
        ("Brass Pen", "Solid brass ballpoint pen.", 39.99),
        ("Sticky Notes Set", "Colourful sticky notes in six sizes.", 9.99),
        ("Desk Lamp", "Adjustable LED desk lamp with dimming.", 49.99),
        ("Leather Desk Mat", "Large leather desk mat.", 44.99),
        ("Watercolour Set", "24-colour travel watercolour palette.", 29.99),
        ("Greeting Cards", "Set of ten letterpress greeting cards.", 16.99),
    ]),
    (["electronics", "accessories"], "#36454f", [
        ("Wireless Earbuds", "Bluetooth earbuds with a charging case.", 79.99),
        ("Phone Case", "Slim protective phone case.", 24.99),
        ("Portable Charger", "10,000 mAh power bank with USB-C.", 34.99),
        ("Bluetooth Speaker", "Water-resistant portable speaker.", 59.99),
        ("Charging Cable", "Braided USB-C cable, 2 m.", 14.99),
        ("Laptop Stand", "Aluminium laptop stand for better posture.", 39.99),
        ("Wireless Charger", "Fast wireless charging pad.", 29.99),
        ("Over-Ear Headphones", "Noise-cancelling over-ear headphones.", 179.99),
        ("Smart Watch Band", "Silicone replacement band for smart watches.", 19.99),
    ]),
]

EXPECTED_NEW_PRODUCTS = 191
ID_ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def product_id(name):
    """Stable 10-character id in the upstream style, derived from the name."""
    value = int(hashlib.sha1(name.encode()).hexdigest(), 16)
    chars = []
    for _ in range(10):
        value, index = divmod(value, len(ID_ALPHABET))
        chars.append(ID_ALPHABET[index])
    return "".join(chars)


def slugify(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def price(usd):
    units = int(usd)
    return {"currencyCode": "USD", "units": units, "nanos": round((usd - units) * 100) * 10_000_000}


def picture_svg(name, category, colour):
    lines = wrap(name, 14)
    first_y = 200 - (len(lines) - 1) * 26
    text = "".join(
        f'<text x="200" y="{first_y + i * 52}" font-size="44" font-weight="600" '
        f'text-anchor="middle" fill="#ffffff">{line.replace("&", "&amp;")}</text>'
        for i, line in enumerate(lines)
    )
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 400" '
        'font-family="Helvetica, Arial, sans-serif">'
        f'<rect width="400" height="400" fill="{colour}"/>'
        f'<rect x="20" y="20" width="360" height="360" rx="24" fill="none" '
        'stroke="#ffffff" stroke-opacity="0.35" stroke-width="4"/>'
        f"{text}"
        f'<text x="200" y="350" font-size="24" text-anchor="middle" fill="#ffffff" '
        f'fill-opacity="0.8" letter-spacing="3">{category.upper()}</text>'
        "</svg>\n"
    )


def main():
    upstream = json.loads(UPSTREAM_CATALOG.read_text(encoding="utf-8"))["products"]
    products = list(upstream)
    seen_ids = {p["id"] for p in products}
    seen_names = {p["name"] for p in products}

    IMAGES_OUT.mkdir(parents=True, exist_ok=True)
    for old in IMAGES_OUT.glob("*.svg"):
        old.unlink()

    for categories, colour, items in GROUPS:
        for name, description, usd in items:
            pid = product_id(name)
            if pid in seen_ids or name in seen_names:
                raise ValueError(f"duplicate product: {name} ({pid})")
            seen_ids.add(pid)
            seen_names.add(name)
            slug = slugify(name)
            products.append({
                "id": pid,
                "name": name,
                "description": description,
                "picture": PICTURE_URL.format(slug=slug),
                "priceUsd": price(usd),
                "categories": categories,
            })
            (IMAGES_OUT / f"{slug}.svg").write_text(picture_svg(name, categories[-1], colour), encoding="utf-8")

    added = len(products) - len(upstream)
    if added != EXPECTED_NEW_PRODUCTS:
        raise ValueError(f"expected {EXPECTED_NEW_PRODUCTS} new products, got {added}")

    CATALOG_OUT.parent.mkdir(parents=True, exist_ok=True)
    CATALOG_OUT.write_text(json.dumps({"products": products}, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(products)} products ({added} new) and {added} pictures")


if __name__ == "__main__":
    main()
