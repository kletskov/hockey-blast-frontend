# Define possible organizations
orgs = {
    "caha": {
        "name": "CAHA",
        "port": 5002,
        "database_uri": "postgresql://pavelkletskov:Pwdp2799s@localhost/hockey_blast",
        "background_image": "caha.png",
        "subdirectory_json": "parsed_games_json",
        "is_gamecenter_json": False,
    },
    "sharksice": {
        "name": "Sharks Ice",
        "port": 5000,
        "database_uri": "postgresql://pavelkletskov:Pwdp2799s@localhost/hockey_blast",
        "background_image": "sharksice.jpg",
        "subdirectory_json": "fetched_gamecenter_json",
        "is_gamecenter_json": True,
    },
    "tvice": {
        "name": "Tri Valley Ice",
        "port": 5001,
        "database_uri": "postgresql://pavelkletskov:Pwdp2799s@localhost/hockey_blast",
        "background_image": "tvice.avif",
        "subdirectory_json": "parsed_games_json",
        "is_gamecenter_json": False,
    },
    "new": {
        "name": "New",
        "port": 5003,
        "database_uri": "postgresql://pavelkletskov:Pwdp2799s@localhost/hockey_blast",
        "background_image": "new.jpg",
        "subdirectory_json": "parsed_games_json",
        "is_gamecenter_json": True,
    },
}


MAX_HUMAN_SEARCH_RESULTS = 25
MAX_TEAM_SEARCH_RESULTS = 25
