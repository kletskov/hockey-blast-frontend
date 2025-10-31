from bs4 import BeautifulSoup


def beautify_tts_html(html_content):
    soup = BeautifulSoup(html_content, "html.parser")

    for a in soup.find_all("a", href=True):
        if "generate-scorecard?game_id=" in a["href"]:
            a["href"] = f"https://stats.sharksice.timetoscore.com/{a['href']}"

    # Change bgcolor attribute to teal
    for tr in soup.find_all("tr", bgcolor=True):
        if tr["bgcolor"] == "#CCCCCC":
            tr["bgcolor"] = "#66CCCC"

    # Change body attributes to red
    body_tag = soup.find("body")
    if body_tag:
        body_tag["text"] = "#ff0000"
        body_tag["vlink"] = "#ff0000"
        body_tag["link"] = "#ff0000"
        body_tag["bgcolor"] = "black"

    # Remove the player photo div
    player_photo_div = soup.find("div", id="player_photo")
    if player_photo_div:
        player_photo_div.decompose()

    # Remove the player bio div
    player_bio_div = soup.find("div", id="player_bio")
    if player_bio_div:
        player_bio_div.decompose()

    return str(soup)
