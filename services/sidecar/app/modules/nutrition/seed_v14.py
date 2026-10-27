"""v1.4 additions to the food table: South Indian dishes from the food-photo dataset.

These are the dishes in the team's Roboflow export (ml/food/class_map.yaml) that had no row
to log yet. Same rules as seed.py and seed_v12.py: VALUES ARE APPROXIMATE, rounded typical
values per ONE household portion for a home or mess-style recipe, estimated from the main
ingredients with public summaries of the Indian Food Composition Tables (IFCT 2017, NIN
Hyderabad) and the Indian Nutrient Databank (INDB). They are not lab measurements: oil,
coconut, ghee and portion size change them a lot, and the app says so next to every
estimate.

Columns: name, portion label, portion grams (or ml), kcal, protein g, carbs g, fat g.
Added by migration 0035 (names already in the table are skipped).
"""

from __future__ import annotations

SOURCE = "approx. IFCT 2017 / INDB-style estimate (v1.4, rounded, home-style)"

FOODS_V14: list[tuple[str, str, float, float, float, float, float]] = [
    # Poriyal (stir-fried vegetables with coconut)
    ("Carrot poriyal", "1 katori", 100, 110, 1.5, 10.0, 7.0),
    ("Beetroot poriyal", "1 katori", 100, 115, 2.0, 11.0, 7.0),
    # Chutneys
    ("Kara chutney", "1 tbsp", 20, 35, 0.5, 3.0, 2.4),
    ("Mint chutney", "1 tbsp", 20, 30, 0.8, 2.5, 1.9),
    # Millet porridge
    ("Kambu koozh", "1 glass", 250, 150, 5.0, 26.0, 2.5),
    # Kozhukattai (steamed rice-flour dumplings): three dishes that look and eat differently
    ("Pidi kozhukattai", "1 piece", 40, 70, 1.2, 13.0, 1.5),
    ("Poorna kozhukattai", "1 piece", 50, 118, 1.5, 20.0, 3.5),
    ("Paal kozhukattai", "1 katori", 150, 230, 5.0, 38.0, 6.5),
    # Rice dishes
    ("Mushroom biryani", "1 plate", 300, 445, 9.0, 66.0, 16.0),
    ("Paneer biryani", "1 plate", 300, 515, 17.0, 64.0, 21.0),
    ("Ghee rice", "1 katori", 150, 280, 4.0, 42.0, 10.5),
    ("Sambar rice", "1 plate", 250, 330, 9.0, 55.0, 8.0),
    # Curries
    ("Paneer masala", "1 katori", 150, 300, 12.0, 11.0, 23.0),
    ("Prawn thokku", "1 katori", 100, 170, 16.0, 6.0, 9.0),
    ("Crab masala", "1 katori", 150, 200, 20.0, 7.0, 10.0),
]
