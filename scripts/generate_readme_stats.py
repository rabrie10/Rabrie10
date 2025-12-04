#!/usr/bin/env python3
"""
GitHub README Stats Generator

Fetches GitHub data using REST and GraphQL APIs and generates SVG files
for display in README.md files.
"""

import os
import sys
from datetime import datetime
import requests

# Configuration
GITHUB_API_BASE = "https://api.github.com"
GITHUB_GRAPHQL_URL = "https://api.github.com/graphql"

# Color scheme (radical theme inspired)
COLORS = {
    "bg": "#1a1a2e",
    "border": "#fe428e",
    "title": "#fe428e",
    "text": "#ffffff",
    "subtitle": "#a9fef7",
    "icon": "#f8d847",
}

# Language colors (common languages)
LANG_COLORS = {
    "Python": "#3572A5",
    "JavaScript": "#f1e05a",
    "TypeScript": "#2b7489",
    "HTML": "#e34c26",
    "CSS": "#563d7c",
    "Java": "#b07219",
    "C++": "#f34b7d",
    "C": "#555555",
    "C#": "#178600",
    "Go": "#00ADD8",
    "Rust": "#dea584",
    "Ruby": "#701516",
    "PHP": "#4F5D95",
    "Swift": "#ffac45",
    "Kotlin": "#F18E33",
    "Shell": "#89e051",
    "Jupyter Notebook": "#DA5B0B",
    "MATLAB": "#e16737",
    "R": "#198CE7",
    "Scala": "#c22d40",
}

# Contribution calendar colors (5-level ramp)
CONTRIB_COLORS = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]


def get_token():
    """Get GitHub token from environment."""
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("Warning: GITHUB_TOKEN not set. API calls may be rate-limited.")
    return token


def get_username():
    """Get username from environment or use default."""
    return os.environ.get("USERNAME", "rabrie10")


def make_rest_request(endpoint, token=None):
    """Make a REST API request to GitHub."""
    url = f"{GITHUB_API_BASE}{endpoint}"
    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"token {token}"
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error fetching {endpoint}: {e}")
        return None


def make_graphql_request(query, token):
    """Make a GraphQL request to GitHub."""
    if not token:
        print("Error: GraphQL API requires authentication.")
        return None
    
    headers = {
        "Authorization": f"bearer {token}",
        "Content-Type": "application/json",
    }
    
    try:
        response = requests.post(
            GITHUB_GRAPHQL_URL,
            json={"query": query},
            headers=headers,
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        if "errors" in data:
            print(f"GraphQL errors: {data['errors']}")
            return None
        return data
    except requests.RequestException as e:
        print(f"Error making GraphQL request: {e}")
        return None


def fetch_user_data(username, token):
    """Fetch basic user data from REST API."""
    print(f"Fetching user data for {username}...")
    return make_rest_request(f"/users/{username}", token)


def fetch_repos(username, token):
    """Fetch all user repositories with pagination."""
    print(f"Fetching repositories for {username}...")
    all_repos = []
    page = 1
    
    while True:
        endpoint = f"/users/{username}/repos?per_page=100&type=owner&sort=updated&page={page}"
        repos = make_rest_request(endpoint, token)
        
        if not repos:
            break
        
        all_repos.extend(repos)
        
        if len(repos) < 100:
            break
        
        page += 1
    
    print(f"  Found {len(all_repos)} repositories")
    return all_repos


def fetch_languages_for_repo(languages_url, token):
    """Fetch language breakdown for a single repo."""
    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"token {token}"
    
    try:
        response = requests.get(languages_url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return {}


def aggregate_languages(repos, token):
    """Aggregate language usage across all repos."""
    print("Aggregating language data...")
    languages = {}
    
    for repo in repos:
        if repo.get("fork"):
            continue
        
        languages_url = repo.get("languages_url")
        if languages_url:
            repo_langs = fetch_languages_for_repo(languages_url, token)
            for lang, bytes_count in repo_langs.items():
                languages[lang] = languages.get(lang, 0) + bytes_count
    
    # Sort by bytes and get top 6
    sorted_langs = sorted(languages.items(), key=lambda x: x[1], reverse=True)[:6]
    
    # Calculate percentages
    total = sum(bytes_count for _, bytes_count in sorted_langs)
    if total == 0:
        return []
    
    result = []
    for lang, bytes_count in sorted_langs:
        percentage = (bytes_count / total) * 100
        result.append({
            "name": lang,
            "bytes": bytes_count,
            "percentage": percentage,
            "color": LANG_COLORS.get(lang, "#858585")
        })
    
    print(f"  Found {len(result)} languages")
    return result


def calculate_total_stars(repos):
    """Calculate total stars across all repos."""
    return sum(repo.get("stargazers_count", 0) for repo in repos if not repo.get("fork"))


def fetch_contributions_calendar(username, token):
    """Fetch contributions calendar using GraphQL."""
    print(f"Fetching contributions calendar for {username}...")
    
    query = f'''
    query {{
        user(login: "{username}") {{
            contributionsCollection {{
                contributionCalendar {{
                    totalContributions
                    weeks {{
                        contributionDays {{
                            date
                            contributionCount
                            color
                        }}
                    }}
                }}
            }}
        }}
    }}
    '''
    
    data = make_graphql_request(query, token)
    if data and "data" in data and data["data"]["user"]:
        return data["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    return None


def write_placeholder_svg(filepath, message="Data unavailable"):
    """Write a placeholder SVG when data is unavailable."""
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="400" height="150" viewBox="0 0 400 150">
  <rect width="400" height="150" fill="{COLORS['bg']}" rx="10"/>
  <text x="200" y="75" fill="{COLORS['text']}" font-family="Arial, sans-serif" font-size="16" text-anchor="middle" dominant-baseline="middle">{message}</text>
  <text x="200" y="100" fill="#888888" font-family="Arial, sans-serif" font-size="12" text-anchor="middle" dominant-baseline="middle">Please try again later</text>
</svg>
'''
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"  Wrote placeholder to {filepath}")


def generate_stats_svg(user_data, total_stars, output_path):
    """Generate the stats.svg file."""
    print("Generating stats.svg...")
    
    if not user_data:
        write_placeholder_svg(output_path, "User data unavailable")
        return False
    
    username = user_data.get("login", "Unknown")
    followers = user_data.get("followers", 0)
    public_repos = user_data.get("public_repos", 0)
    
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="400" height="200" viewBox="0 0 400 200">
  <defs>
    <linearGradient id="statsGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#1a1a2e;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#16213e;stop-opacity:1" />
    </linearGradient>
  </defs>
  <rect width="400" height="200" fill="url(#statsGrad)" rx="10"/>
  <text x="25" y="35" fill="{COLORS['title']}" font-family="Arial, sans-serif" font-size="18" font-weight="bold">{username}'s GitHub Stats</text>
  
  <g transform="translate(25, 60)">
    <text y="20" fill="{COLORS['icon']}" font-family="Arial, sans-serif" font-size="14">⭐</text>
    <text x="25" y="20" fill="{COLORS['text']}" font-family="Arial, sans-serif" font-size="14">Total Stars:</text>
    <text x="130" y="20" fill="{COLORS['subtitle']}" font-family="Arial, sans-serif" font-size="14" font-weight="bold">{total_stars:,}</text>
  </g>
  
  <g transform="translate(25, 95)">
    <text y="20" fill="{COLORS['icon']}" font-family="Arial, sans-serif" font-size="14">📦</text>
    <text x="25" y="20" fill="{COLORS['text']}" font-family="Arial, sans-serif" font-size="14">Public Repos:</text>
    <text x="130" y="20" fill="{COLORS['subtitle']}" font-family="Arial, sans-serif" font-size="14" font-weight="bold">{public_repos:,}</text>
  </g>
  
  <g transform="translate(25, 130)">
    <text y="20" fill="{COLORS['icon']}" font-family="Arial, sans-serif" font-size="14">👥</text>
    <text x="25" y="20" fill="{COLORS['text']}" font-family="Arial, sans-serif" font-size="14">Followers:</text>
    <text x="130" y="20" fill="{COLORS['subtitle']}" font-family="Arial, sans-serif" font-size="14" font-weight="bold">{followers:,}</text>
  </g>
</svg>
'''
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"  Generated {output_path}")
    return True


def generate_top_langs_svg(languages, output_path):
    """Generate the top-langs.svg file."""
    print("Generating top-langs.svg...")
    
    if not languages:
        write_placeholder_svg(output_path, "Language data unavailable")
        return False
    
    # Calculate bar positions
    bar_height = 20
    padding = 25
    header_height = 45
    height = header_height + len(languages) * (bar_height + 10) + padding
    
    svg_parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="400" height="{height}" viewBox="0 0 400 {height}">',
        '  <defs>',
        '    <linearGradient id="langGrad" x1="0%" y1="0%" x2="100%" y2="100%">',
        '      <stop offset="0%" style="stop-color:#1a1a2e;stop-opacity:1" />',
        '      <stop offset="100%" style="stop-color:#16213e;stop-opacity:1" />',
        '    </linearGradient>',
        '  </defs>',
        f'  <rect width="400" height="{height}" fill="url(#langGrad)" rx="10"/>',
        f'  <text x="25" y="30" fill="{COLORS["title"]}" font-family="Arial, sans-serif" font-size="18" font-weight="bold">Most Used Languages</text>',
    ]
    
    y_offset = header_height
    bar_width = 300
    
    for lang in languages:
        lang_width = (lang["percentage"] / 100) * bar_width
        
        svg_parts.extend([
            f'  <g transform="translate(25, {y_offset})">',
            f'    <circle cx="8" cy="10" r="6" fill="{lang["color"]}"/>',
            f'    <text x="22" y="14" fill="{COLORS["text"]}" font-family="Arial, sans-serif" font-size="12">{lang["name"]}</text>',
            f'    <text x="350" y="14" fill="{COLORS["subtitle"]}" font-family="Arial, sans-serif" font-size="12" text-anchor="end">{lang["percentage"]:.1f}%</text>',
            f'    <rect x="0" y="20" width="{bar_width}" height="8" fill="#2d2d44" rx="4"/>',
            f'    <rect x="0" y="20" width="{lang_width}" height="8" fill="{lang["color"]}" rx="4"/>',
            '  </g>',
        ])
        
        y_offset += bar_height + 15
    
    svg_parts.append('</svg>')
    
    svg = '\n'.join(svg_parts)
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"  Generated {output_path}")
    return True


def get_contrib_color(count):
    """Get color for contribution count."""
    if count == 0:
        return CONTRIB_COLORS[0]
    elif count <= 3:
        return CONTRIB_COLORS[1]
    elif count <= 6:
        return CONTRIB_COLORS[2]
    elif count <= 9:
        return CONTRIB_COLORS[3]
    else:
        return CONTRIB_COLORS[4]


def generate_streak_svg(calendar_data, output_path):
    """Generate the streak.svg file (contributions calendar heatmap)."""
    print("Generating streak.svg...")
    
    if not calendar_data:
        write_placeholder_svg(output_path, "Contribution data unavailable")
        return False
    
    weeks = calendar_data.get("weeks", [])
    total_contributions = calendar_data.get("totalContributions", 0)
    
    if not weeks:
        write_placeholder_svg(output_path, "No contribution data")
        return False
    
    # Calendar dimensions
    cell_size = 12
    cell_gap = 3
    cell_total = cell_size + cell_gap
    left_margin = 35  # Space for day labels
    top_margin = 35   # Space for month labels
    
    num_weeks = len(weeks)
    width = left_margin + num_weeks * cell_total + 20
    height = top_margin + 7 * cell_total + 50  # Extra space for legend and stats
    
    svg_parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '  <defs>',
        '    <linearGradient id="streakGrad" x1="0%" y1="0%" x2="100%" y2="100%">',
        '      <stop offset="0%" style="stop-color:#1a1a2e;stop-opacity:1" />',
        '      <stop offset="100%" style="stop-color:#16213e;stop-opacity:1" />',
        '    </linearGradient>',
        '  </defs>',
        f'  <rect width="{width}" height="{height}" fill="url(#streakGrad)" rx="10"/>',
        f'  <text x="{width/2}" y="20" fill="{COLORS["title"]}" font-family="Arial, sans-serif" font-size="14" font-weight="bold" text-anchor="middle">{total_contributions:,} contributions in the last year</text>',
    ]
    
    # Day labels (Mon, Wed, Fri)
    day_labels = ["", "Mon", "", "Wed", "", "Fri", ""]
    for i, label in enumerate(day_labels):
        if label:
            y = top_margin + i * cell_total + cell_size - 2
            svg_parts.append(f'  <text x="5" y="{y}" fill="#8b949e" font-family="Arial, sans-serif" font-size="10">{label}</text>')
    
    # Month labels
    months_added = set()
    month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    
    for week_idx, week in enumerate(weeks):
        days = week.get("contributionDays", [])
        if days:
            # Check first day of week for month
            first_day = days[0]
            date_str = first_day.get("date", "")
            if date_str:
                try:
                    date = datetime.strptime(date_str, "%Y-%m-%d")
                    month_key = f"{date.year}-{date.month}"
                    if month_key not in months_added and date.day <= 7:
                        x = left_margin + week_idx * cell_total
                        month_name = month_names[date.month - 1]
                        svg_parts.append(f'  <text x="{x}" y="{top_margin - 8}" fill="#8b949e" font-family="Arial, sans-serif" font-size="10">{month_name}</text>')
                        months_added.add(month_key)
                except ValueError:
                    pass
    
    # Draw cells
    for week_idx, week in enumerate(weeks):
        days = week.get("contributionDays", [])
        for day_idx, day in enumerate(days):
            count = day.get("contributionCount", 0)
            color = day.get("color", get_contrib_color(count))
            
            x = left_margin + week_idx * cell_total
            y = top_margin + day_idx * cell_total
            
            svg_parts.append(f'  <rect x="{x}" y="{y}" width="{cell_size}" height="{cell_size}" fill="{color}" rx="2"/>')
    
    # Legend
    legend_y = top_margin + 7 * cell_total + 15
    svg_parts.append(f'  <text x="{width - 120}" y="{legend_y}" fill="#8b949e" font-family="Arial, sans-serif" font-size="10">Less</text>')
    
    legend_x = width - 95
    for i, color in enumerate(CONTRIB_COLORS):
        svg_parts.append(f'  <rect x="{legend_x + i * 15}" y="{legend_y - 10}" width="12" height="12" fill="{color}" rx="2"/>')
    
    svg_parts.append(f'  <text x="{legend_x + 75}" y="{legend_y}" fill="#8b949e" font-family="Arial, sans-serif" font-size="10">More</text>')
    
    svg_parts.append('</svg>')
    
    svg = '\n'.join(svg_parts)
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"  Generated {output_path}")
    return True


def main():
    """Main function to generate all stats SVGs."""
    print("=" * 50)
    print("GitHub README Stats Generator")
    print("=" * 50)
    
    token = get_token()
    username = get_username()
    
    print(f"\nGenerating stats for: {username}")
    print("-" * 50)
    
    # Output directory
    output_dir = "assets/readme-stats"
    os.makedirs(output_dir, exist_ok=True)
    
    stats_path = os.path.join(output_dir, "stats.svg")
    langs_path = os.path.join(output_dir, "top-langs.svg")
    streak_path = os.path.join(output_dir, "streak.svg")
    
    success_count = 0
    
    # Fetch user data
    try:
        user_data = fetch_user_data(username, token)
        repos = fetch_repos(username, token) or []
        total_stars = calculate_total_stars(repos)
        
        if generate_stats_svg(user_data, total_stars, stats_path):
            success_count += 1
    except Exception as e:
        print(f"Error generating stats.svg: {e}")
        write_placeholder_svg(stats_path, "Stats unavailable")
    
    # Fetch and generate language stats
    try:
        if repos:
            languages = aggregate_languages(repos, token)
        else:
            repos = fetch_repos(username, token) or []
            languages = aggregate_languages(repos, token)
        
        if generate_top_langs_svg(languages, langs_path):
            success_count += 1
    except Exception as e:
        print(f"Error generating top-langs.svg: {e}")
        write_placeholder_svg(langs_path, "Languages unavailable")
    
    # Fetch and generate contributions calendar
    try:
        calendar_data = fetch_contributions_calendar(username, token)
        if generate_streak_svg(calendar_data, streak_path):
            success_count += 1
    except Exception as e:
        print(f"Error generating streak.svg: {e}")
        write_placeholder_svg(streak_path, "Contributions unavailable")
    
    print("\n" + "=" * 50)
    print(f"Generation complete: {success_count}/3 SVGs generated successfully")
    print("=" * 50)
    
    # Always exit with 0 to not fail the workflow
    return 0


if __name__ == "__main__":
    sys.exit(main())
