"""
Graphic Studio Generator using Python Pillow (PIL) (V1.5).
Includes smart auto-template detection (Fifty, Century, 5-Wicket Haul, Bowling, General).
"""

import os
import re
from PIL import Image, ImageDraw, ImageFont
from utils.logger import graphics_logger, error_logger

GENERATED_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "generated")

def ensure_generated_dir():
    if not os.path.exists(GENERATED_DIR):
        os.makedirs(GENERATED_DIR)

def detect_best_template(main_stat_text):
    """Automatically selects appropriate template based on stats text."""
    text = main_stat_text.lower()
    
    # Check for runs / centuries / fifties
    runs_match = re.search(r'(\d+)\s*(runs|off|b)', text)
    if runs_match:
        runs = int(runs_match.group(1))
        if runs >= 100:
            return "century", "💯 MAIDEN CENTURY!"
        elif runs >= 50:
            return "fifty", "🔥 HALF-CENTURY!"
            
    # Check for wickets
    wkts_match = re.search(r'(\d+)\s*(wickets|wkts|wkt|/|\-)', text)
    if wkts_match:
        wkts = int(wkts_match.group(1))
        if wkts >= 5:
            return "five_wickets", "🎯 5-WICKET HAUL!"
        elif wkts >= 3:
            return "bowling", "⚡ BOWLING SPELL!"
            
    return "general", "💥 MATCHDAY HIGHLIGHT"

def create_stat_card(player_name, franchise, main_stat, sub_stat, opponent="Opponent", template_type="auto"):
    """
    Generates a 1200x675 (16:9 Twitter optimized) branded Sunrisers stat card image.
    Uses auto-detected templates if template_type is 'auto'.
    """
    try:
        ensure_generated_dir()
        width, height = 1200, 675
        
        # Auto template detection
        if template_type == "auto":
            template_key, banner_title = detect_best_template(main_stat)
        else:
            template_key = template_type
            banner_title = "💥 MATCHDAY HIGHLIGHT"
            
        # Select background accent color
        if template_key == "century":
            accent_color = "#FFD700"  # Gold
        elif template_key == "five_wickets":
            accent_color = "#00E676"  # Bright Green
        else:
            accent_color = "#F26522"  # Sunrisers Orange
            
        img = Image.new("RGB", (width, height), color="#121212")
        draw = ImageDraw.Draw(img)
        
        # Sunrisers Header & Footer Accent Lines
        draw.rectangle([0, 0, width, 25], fill=accent_color)
        draw.rectangle([0, height - 15, width, height], fill=accent_color)
        draw.rectangle([50, 60, 60, 600], fill=accent_color)
        
        try:
            title_font = ImageFont.truetype("Helvetica", 54)
            subtitle_font = ImageFont.truetype("Helvetica", 36)
            stat_font = ImageFont.truetype("Helvetica", 76)
            footer_font = ImageFont.truetype("Helvetica", 24)
        except Exception:
            title_font = ImageFont.load_default()
            subtitle_font = ImageFont.load_default()
            stat_font = ImageFont.load_default()
            footer_font = ImageFont.load_default()
            
        # Banner Header Badge
        draw.text((90, 70), f"@SRHXtra | {franchise.upper()} | {banner_title}", fill=accent_color, font=subtitle_font)
        
        # Player Name
        draw.text((90, 140), player_name.upper(), fill="#FFFFFF", font=title_font)
        
        # Stat Display Box
        draw.rectangle([90, 240, 1110, 420], fill="#1E1E1E", outline=accent_color, width=3)
        draw.text((120, 280), main_stat, fill=accent_color, font=stat_font)
        
        # Opponent & Sub-stats
        draw.text((90, 450), f"VS {opponent.upper()}", fill="#CCCCCC", font=subtitle_font)
        draw.text((90, 510), sub_stat, fill="#888888", font=subtitle_font)
        
        # Footer
        draw.text((90, 610), "OFFICIAL @SRHXtra MATCHDAY STAT CARD | ZERO-API ENGINE", fill="#666666", font=footer_font)
        
        clean_filename = f"{player_name.lower().replace(' ', '_')}_{template_key}.png"
        filepath = os.path.join(GENERATED_DIR, clean_filename)
        img.save(filepath, "PNG")
        graphics_logger.info(f"Generated Stat Card ({template_key}): {filepath}")
        return filepath
    except Exception as e:
        error_logger.error(f"Failed to generate stat card for {player_name}: {e}")
        return ""
