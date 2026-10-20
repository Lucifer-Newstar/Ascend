"""Seeded Indian food table (~30 items) with household portions.

VALUES ARE APPROXIMATE. They are rounded, typical home-style values compiled
from public summaries of the Indian Food Composition Tables (IFCT 2017, NIN
Hyderabad) and the Indian Nutrient Databank (INDB). Real dishes vary a lot with
recipe, oil and portion size. Replace with the full INDB import in a later phase.

Columns: name, portion label, portion grams, kcal, protein g, carbs g, fat g
(nutrients are per ONE portion).
"""

from __future__ import annotations

SOURCE = "approx. IFCT 2017 / INDB-style values (rounded, home-style)"

FOODS: list[tuple[str, str, float, float, float, float, float]] = [
    ("Idli", "1 piece", 40, 58, 2.0, 12.0, 0.2),
    ("Plain dosa", "1 piece", 80, 168, 3.9, 29.0, 3.7),
    ("Masala dosa", "1 piece", 175, 330, 6.5, 47.0, 12.5),
    ("Rava upma", "1 katori", 150, 210, 5.0, 31.0, 7.5),
    ("Ven pongal", "1 katori", 150, 230, 6.0, 33.0, 8.0),
    ("Medu vada", "1 piece", 45, 135, 4.5, 13.0, 7.5),
    ("Sambar", "1 katori", 150, 110, 5.5, 15.0, 3.0),
    ("Rasam", "1 katori", 150, 55, 1.5, 8.0, 2.0),
    ("Coconut chutney", "1 tbsp", 20, 45, 0.6, 2.0, 4.0),
    ("Tomato chutney", "1 tbsp", 20, 25, 0.4, 3.0, 1.4),
    ("Peanut chutney", "1 tbsp", 20, 70, 2.6, 2.5, 5.6),
    ("Steamed rice", "1 katori", 150, 195, 3.8, 43.0, 0.4),
    ("Curd rice", "1 katori", 180, 240, 6.5, 36.0, 7.5),
    ("Lemon rice", "1 katori", 150, 250, 4.0, 40.0, 8.0),
    ("Chicken biryani", "1 plate", 300, 520, 24.0, 62.0, 19.0),
    ("Veg biryani", "1 plate", 300, 430, 9.0, 66.0, 14.0),
    ("Chapati", "1 piece", 40, 110, 3.1, 18.0, 3.0),
    ("Parotta", "1 piece", 90, 280, 5.5, 38.0, 11.5),
    ("Toor dal", "1 katori", 150, 165, 9.5, 22.0, 4.5),
    ("Rajma curry", "1 katori", 150, 190, 9.0, 25.0, 6.0),
    ("Chana masala", "1 katori", 150, 210, 9.5, 27.0, 7.0),
    ("Palak paneer", "1 katori", 150, 260, 12.0, 9.0, 19.0),
    ("Mixed veg poriyal", "1 katori", 100, 95, 2.5, 9.0, 5.5),
    ("Chicken curry", "1 katori", 150, 245, 22.0, 6.0, 15.0),
    ("Fish curry", "1 katori", 150, 200, 20.0, 5.0, 11.0),
    ("Boiled egg", "1 piece", 50, 72, 6.3, 0.4, 4.8),
    ("Curd (plain)", "1 katori", 100, 60, 3.1, 4.7, 3.3),
    ("Buttermilk", "1 glass", 200, 40, 2.0, 3.0, 2.0),
    ("Filter coffee (with milk, sugar)", "1 tumbler", 150, 90, 2.5, 12.0, 3.5),
    ("Banana", "1 medium", 120, 105, 1.3, 27.0, 0.4),
    ("Sundal (chickpea)", "1 katori", 100, 150, 7.5, 21.0, 4.0),
]
