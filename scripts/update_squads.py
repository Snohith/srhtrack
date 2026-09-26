"""
Script to update squadofsunrisers.xlsx with official Sunrisers franchises data:
- Sunrisers Hyderabad (IPL)
- Sunrisers Eastern Cape (SA20)
- Sunrisers Leeds Men (The Hundred)
- Sunrisers Leeds Women (The Hundred) - Preserved exactly as requested
"""
import os
import pandas as pd

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXCEL_PATH = os.path.join(REPO_ROOT, "squadofsunrisers.xlsx")

# 1. Read existing Leeds Women data to preserve 100% exactly
df_existing = pd.read_excel(EXCEL_PATH)
womens_data = df_existing[df_existing["Team"].astype(str).str.contains("Women")].copy()

# 2. Define Updated Men's Squads
leeds_men = [
    {"Team": "Sunrisers Leeds Men", "Player": "Dan Vettori", "Role": "Head Coach", "Country": "New Zealand", "Notes": "Head Coach; Overseas"},
    {"Team": "Sunrisers Leeds Men", "Player": "Zak Crawley", "Role": "Captain / Batter", "Country": "England", "Notes": "Captain"},
    {"Team": "Sunrisers Leeds Men", "Player": "Mitch Marsh", "Role": "All-rounder", "Country": "Australia", "Notes": "Overseas"},
    {"Team": "Sunrisers Leeds Men", "Player": "Ryan Rickelton", "Role": "Wicket-keeper batter", "Country": "South Africa", "Notes": "Overseas"},
    {"Team": "Sunrisers Leeds Men", "Player": "Harry Brook", "Role": "Batter", "Country": "England", "Notes": ""},
    {"Team": "Sunrisers Leeds Men", "Player": "Dan Lawrence", "Role": "Batter", "Country": "England", "Notes": ""},
    {"Team": "Sunrisers Leeds Men", "Player": "Matty Revis", "Role": "All-rounder", "Country": "England", "Notes": "Wildcard"},
    {"Team": "Sunrisers Leeds Men", "Player": "Liam Patterson-White", "Role": "Spin bowler / All-rounder", "Country": "England", "Notes": ""},
    {"Team": "Sunrisers Leeds Men", "Player": "Brydon Carse", "Role": "Pace bowler / All-rounder", "Country": "England", "Notes": ""},
    {"Team": "Sunrisers Leeds Men", "Player": "Matthew Potts", "Role": "Pace bowler", "Country": "England", "Notes": ""},
    {"Team": "Sunrisers Leeds Men", "Player": "Nathan Ellis", "Role": "Pace bowler", "Country": "Australia", "Notes": "Overseas"},
    {"Team": "Sunrisers Leeds Men", "Player": "Abrar Ahmed", "Role": "Spin bowler", "Country": "Pakistan", "Notes": "Overseas"},
    {"Team": "Sunrisers Leeds Men", "Player": "Benny Howell", "Role": "All-rounder", "Country": "England", "Notes": ""},
    {"Team": "Sunrisers Leeds Men", "Player": "Tom Lawes", "Role": "Pace bowler", "Country": "England", "Notes": ""},
    {"Team": "Sunrisers Leeds Men", "Player": "Ed Barnard", "Role": "All-rounder", "Country": "England", "Notes": ""},
    {"Team": "Sunrisers Leeds Men", "Player": "Tom Alsop", "Role": "Wicket-keeper batter", "Country": "England", "Notes": "Ruled out (injury)"},
    {"Team": "Sunrisers Leeds Men", "Player": "Reece Topley", "Role": "Pace bowler", "Country": "England", "Notes": "Ruled out (injury)"},
    {"Team": "Sunrisers Leeds Men", "Player": "Charlie Allison", "Role": "Batter", "Country": "England", "Notes": "Wildcard"},
    {"Team": "Sunrisers Leeds Men", "Player": "Graham Clark", "Role": "Batter", "Country": "England", "Notes": "Replacement"},
    {"Team": "Sunrisers Leeds Men", "Player": "James Fuller", "Role": "All-rounder", "Country": "England", "Notes": "Replacement"},
]

srh_men = [
    {"Team": "Sunrisers Hyderabad IPL 2026", "Player": "Daniel Vettori", "Role": "Head Coach", "Country": "New Zealand", "Notes": "Head Coach; Overseas"},
    {"Team": "Sunrisers Hyderabad IPL 2026", "Player": "Pat Cummins", "Role": "Captain / Pace bowler", "Country": "Australia", "Notes": "Captain; Overseas"},
    {"Team": "Sunrisers Hyderabad IPL 2026", "Player": "Abhishek Sharma", "Role": "All-rounder", "Country": "India", "Notes": ""},
    {"Team": "Sunrisers Hyderabad IPL 2026", "Player": "Travis Head", "Role": "Batter", "Country": "Australia", "Notes": "Overseas"},
    {"Team": "Sunrisers Hyderabad IPL 2026", "Player": "Ishan Kishan", "Role": "Wicket-keeper batter", "Country": "India", "Notes": "Stand-in captain (early season)"},
    {"Team": "Sunrisers Hyderabad IPL 2026", "Player": "Heinrich Klaasen", "Role": "Wicket-keeper batter", "Country": "South Africa", "Notes": "Overseas"},
    {"Team": "Sunrisers Hyderabad IPL 2026", "Player": "Nitish Kumar Reddy", "Role": "All-rounder", "Country": "India", "Notes": ""},
    {"Team": "Sunrisers Hyderabad IPL 2026", "Player": "Aniket Verma", "Role": "Batter", "Country": "India", "Notes": ""},
    {"Team": "Sunrisers Hyderabad IPL 2026", "Player": "Salil Arora", "Role": "Wicket-keeper batter", "Country": "India", "Notes": ""},
    {"Team": "Sunrisers Hyderabad IPL 2026", "Player": "Shivang Kumar", "Role": "All-rounder", "Country": "India", "Notes": ""},
    {"Team": "Sunrisers Hyderabad IPL 2026", "Player": "Sakib Hussain", "Role": "Bowler", "Country": "India", "Notes": ""},
    {"Team": "Sunrisers Hyderabad IPL 2026", "Player": "Eshan Malinga", "Role": "Bowler", "Country": "Sri Lanka", "Notes": "Overseas"},
    {"Team": "Sunrisers Hyderabad IPL 2026", "Player": "Praful Hinge", "Role": "Bowler", "Country": "India", "Notes": ""},
    {"Team": "Sunrisers Hyderabad IPL 2026", "Player": "Harshal Patel", "Role": "All-rounder / Pace bowler", "Country": "India", "Notes": ""},
    {"Team": "Sunrisers Hyderabad IPL 2026", "Player": "Jaydev Unadkat", "Role": "Bowler", "Country": "India", "Notes": ""},
    {"Team": "Sunrisers Hyderabad IPL 2026", "Player": "Shivam Mavi", "Role": "Bowler", "Country": "India", "Notes": "Withdrawn (injury)"},
    {"Team": "Sunrisers Hyderabad IPL 2026", "Player": "Zeeshan Ansari", "Role": "Bowler", "Country": "India", "Notes": ""},
    {"Team": "Sunrisers Hyderabad IPL 2026", "Player": "Harsh Dubey", "Role": "All-rounder", "Country": "India", "Notes": ""},
    {"Team": "Sunrisers Hyderabad IPL 2026", "Player": "R Smaran", "Role": "Batter", "Country": "India", "Notes": ""},
    {"Team": "Sunrisers Hyderabad IPL 2026", "Player": "Onkar Tarmale", "Role": "Bowler", "Country": "India", "Notes": ""},
    {"Team": "Sunrisers Hyderabad IPL 2026", "Player": "Amit Kumar", "Role": "Bowler", "Country": "India", "Notes": ""},
    {"Team": "Sunrisers Hyderabad IPL 2026", "Player": "Krains Fuletra", "Role": "All-rounder", "Country": "India", "Notes": ""},
    {"Team": "Sunrisers Hyderabad IPL 2026", "Player": "RS Ambrish", "Role": "All-rounder / Bowler", "Country": "India", "Notes": "Replacement for Shivam Mavi"},
    {"Team": "Sunrisers Hyderabad IPL 2026", "Player": "Liam Livingstone", "Role": "All-rounder", "Country": "England", "Notes": "Overseas"},
    {"Team": "Sunrisers Hyderabad IPL 2026", "Player": "Gerald Coetzee", "Role": "Pace bowler", "Country": "South Africa", "Notes": "Overseas; Replacement"},
    {"Team": "Sunrisers Hyderabad IPL 2026", "Player": "David Payne", "Role": "Bowler", "Country": "England", "Notes": "Overseas; Replacement then Withdrawn"},
    {"Team": "Sunrisers Hyderabad IPL 2026", "Player": "Brydon Carse", "Role": "Pace bowler", "Country": "England", "Notes": "Overseas; Withdrawn (injury)"},
    {"Team": "Sunrisers Hyderabad IPL 2026", "Player": "Kamindu Mendis", "Role": "All-rounder", "Country": "Sri Lanka", "Notes": "Overseas"},
    {"Team": "Sunrisers Hyderabad IPL 2026", "Player": "Dilshan Madhushanka", "Role": "Bowler", "Country": "Sri Lanka", "Notes": "Overseas; Replacement for Brydon Carse"},
    {"Team": "Sunrisers Hyderabad IPL 2026", "Player": "Jack Edwards", "Role": "All-rounder", "Country": "Australia", "Notes": "Overseas; Withdrawn (injury)"},
]

sec_men = [
    {"Team": "Sunrisers Eastern Cape SA20 2026", "Player": "Adrian Birrell", "Role": "Head Coach", "Country": "South Africa", "Notes": "Head Coach"},
    {"Team": "Sunrisers Eastern Cape SA20 2026", "Player": "Tristan Stubbs", "Role": "Captain / Wicket-keeper batter", "Country": "South Africa", "Notes": "Captain"},
    {"Team": "Sunrisers Eastern Cape SA20 2026", "Player": "Quinton De Kock", "Role": "Wicket-keeper batter", "Country": "South Africa", "Notes": ""},
    {"Team": "Sunrisers Eastern Cape SA20 2026", "Player": "Mitch Marsh", "Role": "All-rounder", "Country": "Australia", "Notes": "Overseas; Pre-signed"},
    {"Team": "Sunrisers Eastern Cape SA20 2026", "Player": "Matthew Breetzke", "Role": "Batter / Wicket-keeper", "Country": "South Africa", "Notes": ""},
    {"Team": "Sunrisers Eastern Cape SA20 2026", "Player": "Jordan Hermann", "Role": "Batter", "Country": "South Africa", "Notes": ""},
    {"Team": "Sunrisers Eastern Cape SA20 2026", "Player": "James Coles", "Role": "All-rounder", "Country": "England", "Notes": "Overseas"},
    {"Team": "Sunrisers Eastern Cape SA20 2026", "Player": "Marco Jansen", "Role": "All-rounder", "Country": "South Africa", "Notes": "Wildcard"},
    {"Team": "Sunrisers Eastern Cape SA20 2026", "Player": "Senuran Muthusamy", "Role": "All-rounder", "Country": "South Africa", "Notes": ""},
    {"Team": "Sunrisers Eastern Cape SA20 2026", "Player": "Rishad Hossain", "Role": "Bowler / All-rounder", "Country": "Bangladesh", "Notes": "Overseas; Pre-signed"},
    {"Team": "Sunrisers Eastern Cape SA20 2026", "Player": "Anrich Nortje", "Role": "Bowler", "Country": "South Africa", "Notes": ""},
    {"Team": "Sunrisers Eastern Cape SA20 2026", "Player": "Adam Milne", "Role": "Bowler", "Country": "New Zealand", "Notes": "Overseas"},
    {"Team": "Sunrisers Eastern Cape SA20 2026", "Player": "Lutho Sipamla", "Role": "Bowler", "Country": "South Africa", "Notes": ""},
    {"Team": "Sunrisers Eastern Cape SA20 2026", "Player": "Patrick Kruger", "Role": "All-rounder", "Country": "South Africa", "Notes": ""},
    {"Team": "Sunrisers Eastern Cape SA20 2026", "Player": "Mitch Van Buuren", "Role": "Batter", "Country": "South Africa", "Notes": ""},
    {"Team": "Sunrisers Eastern Cape SA20 2026", "Player": "CJ King", "Role": "All-rounder (U23)", "Country": "South Africa", "Notes": ""},
    {"Team": "Sunrisers Eastern Cape SA20 2026", "Player": "JP King", "Role": "All-rounder (U23)", "Country": "South Africa", "Notes": ""},
    {"Team": "Sunrisers Eastern Cape SA20 2026", "Player": "Lewis Gregory", "Role": "All-rounder", "Country": "England", "Notes": "Overseas"},
]

df_leeds_men = pd.DataFrame(leeds_men)
df_srh = pd.DataFrame(srh_men)
df_sec = pd.DataFrame(sec_men)

# Combine: Leeds Men, Leeds Women, SRH, SEC
combined_df = pd.concat([df_leeds_men, womens_data, df_srh, df_sec], ignore_index=True)

# Write to Excel
combined_df.to_excel(EXCEL_PATH, index=False)
print(f"Successfully updated {EXCEL_PATH} with {len(combined_df)} total squad entries.")
