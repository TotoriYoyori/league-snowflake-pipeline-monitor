# Public API for src/ui/.
from src.ui.bronze import render_bronze
from src.ui.components import render_header
from src.ui.gold import render_gold
from src.ui.seed import render_seed
from src.ui.silver import render_silver
from src.ui.theme import inject

__all__ = [
    "inject", "render_header",
    "render_seed", "render_bronze", "render_silver", "render_gold",
]
