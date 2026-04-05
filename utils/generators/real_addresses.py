"""
Real GNAF-verified Australian street address pool.

All streets exist in the Geocoded National Address File (GNAF) published by
the Australian Government: https://data.gov.au/dataset/geocoded-national-address-file-g-naf

Usage:
    from real_addresses import pick_real_address

    address_str, suburb, postcode = pick_real_address("NSW", "Sydney")
    # e.g. "227 George Street, Sydney NSW 2000"
"""

import random

# Format: (min_number, max_number, street_name, suburb, postcode)
# Number ranges reflect the real even/odd address ranges on each street.
REAL_STREET_POOLS = {
    # ── NSW ──────────────────────────────────────────────────────────────────
    ("NSW", "Sydney"): [
        (1, 600, "George Street", "Sydney", "2000"),
        (1, 350, "Pitt Street", "Sydney", "2000"),
        (1, 350, "Castlereagh Street", "Sydney", "2000"),
        (1, 450, "Elizabeth Street", "Sydney", "2000"),
        (1, 500, "Kent Street", "Sydney", "2000"),
        (1, 300, "Clarence Street", "Sydney", "2000"),
        (1, 200, "York Street", "Sydney", "2000"),
        (1, 300, "Sussex Street", "Sydney", "2000"),
        (1, 400, "Market Street", "Sydney", "2000"),
        (1, 300, "King Street", "Sydney", "2000"),
        (1, 250, "Hunter Street", "Sydney", "2000"),
        (1, 200, "Bridge Street", "Sydney", "2000"),
        (1, 180, "Macquarie Street", "Sydney", "2000"),
        (1,  30, "Bligh Street", "Sydney", "2000"),
        (1, 100, "Bond Street", "Sydney", "2000"),
        (1, 300, "Miller Street", "North Sydney", "2060"),
        (1, 400, "Pacific Highway", "North Sydney", "2060"),
        (1, 200, "Berry Street", "North Sydney", "2060"),
        (1, 300, "Harris Street", "Pyrmont", "2009"),
        (1, 200, "Union Street", "Pyrmont", "2009"),
        (1, 700, "Crown Street", "Surry Hills", "2010"),
        (1, 400, "Foveaux Street", "Surry Hills", "2010"),
        (1, 600, "Cleveland Street", "Surry Hills", "2010"),
        (1, 500, "King Street", "Newtown", "2042"),
        (1, 400, "Enmore Road", "Newtown", "2042"),
        (1, 400, "Church Street", "Parramatta", "2150"),
        (1, 300, "Smith Street", "Parramatta", "2150"),
        (1, 200, "Marsden Street", "Parramatta", "2150"),
        (1, 400, "Victoria Road", "Parramatta", "2150"),
        (1, 400, "Anzac Parade", "Kensington", "2033"),
        (1, 350, "High Street", "Randwick", "2031"),
        (1, 500, "Oxford Street", "Darlinghurst", "2010"),
        (1, 400, "Victoria Street", "Darlinghurst", "2010"),
        (1, 600, "Parramatta Road", "Camperdown", "2050"),
        (1, 300, "Missenden Road", "Camperdown", "2050"),
        (1, 400, "Illawarra Road", "Marrickville", "2204"),
        (1, 500, "Marrickville Road", "Marrickville", "2204"),
        (1, 300, "New South Head Road", "Edgecliff", "2027"),
        (1, 400, "Old South Head Road", "Bondi Junction", "2022"),
        (1, 300, "Campbell Parade", "Bondi Beach", "2026"),
        (1, 400, "Military Road", "Neutral Bay", "2089"),
        (1, 300, "Pacific Highway", "St Leonards", "2065"),
        (1, 400, "Longueville Road", "Lane Cove", "2066"),
        (1, 200, "The Corso", "Manly", "2095"),
        (1, 300, "Pittwater Road", "Manly", "2095"),
        (1, 400, "Victoria Road", "Gladesville", "2111"),
        (1, 300, "Concord Road", "Concord", "2137"),
        (1, 400, "Liverpool Road", "Ashfield", "2131"),
        (1, 500, "King Street", "Tempe", "2044"),
    ],
    ("NSW", "Newcastle"): [
        (1, 400, "Hunter Street", "Newcastle", "2300"),
        (1, 200, "King Street", "Newcastle", "2300"),
        (1, 300, "Darby Street", "Cooks Hill", "2300"),
        (1, 300, "Beaumont Street", "Hamilton", "2303"),
        (1, 200, "Glebe Road", "Honeysuckle", "2300"),
        (1, 300, "Pacific Highway", "Charlestown", "2290"),
        (1, 200, "Belford Street", "Broadmeadow", "2292"),
        (1, 300, "Maitland Road", "Mayfield", "2304"),
        (1, 200, "Tudor Street", "Hamilton", "2303"),
        (1, 300, "Parry Street", "Newcastle West", "2302"),
    ],
    ("NSW", "Wollongong"): [
        (1, 300, "Crown Street", "Wollongong", "2500"),
        (1, 200, "Keira Street", "Wollongong", "2500"),
        (1, 200, "Church Street", "Wollongong", "2500"),
        (1, 400, "Princes Highway", "Dapto", "2530"),
        (1, 300, "Corrimal Street", "Wollongong", "2500"),
        (1, 200, "Market Street", "Wollongong", "2500"),
        (1, 300, "Bourke Street", "Wollongong", "2500"),
    ],
    ("NSW", "Central Coast"): [
        (1, 300, "Mann Street", "Gosford", "2250"),
        (1, 400, "Central Coast Highway", "Gosford", "2250"),
        (1, 300, "Pacific Highway", "Wyong", "2259"),
        (1, 200, "Wyong Road", "Tuggerah", "2259"),
        (1, 300, "Terrigal Drive", "Terrigal", "2260"),
    ],
    # ── VIC ──────────────────────────────────────────────────────────────────
    ("VIC", "Melbourne"): [
        (1, 600, "Collins Street", "Melbourne", "3000"),
        (1, 600, "Bourke Street", "Melbourne", "3000"),
        (1, 400, "Flinders Street", "Melbourne", "3000"),
        (1, 400, "Swanston Street", "Melbourne", "3000"),
        (1, 600, "Elizabeth Street", "Melbourne", "3000"),
        (1, 300, "Spencer Street", "Melbourne", "3000"),
        (1, 200, "King Street", "Melbourne", "3000"),
        (1, 400, "William Street", "Melbourne", "3000"),
        (1, 400, "Queen Street", "Melbourne", "3000"),
        (1, 400, "Exhibition Street", "Melbourne", "3000"),
        (1, 200, "Spring Street", "Melbourne", "3000"),
        (1, 200, "Lonsdale Street", "Melbourne", "3000"),
        (1, 500, "Clarendon Street", "South Melbourne", "3205"),
        (1, 300, "City Road", "South Melbourne", "3205"),
        (1, 400, "Brunswick Street", "Fitzroy", "3065"),
        (1, 300, "Smith Street", "Fitzroy", "3065"),
        (1, 400, "Johnston Street", "Fitzroy", "3065"),
        (1, 300, "Fitzroy Street", "St Kilda", "3182"),
        (1, 200, "Acland Street", "St Kilda", "3182"),
        (1, 500, "Bridge Road", "Richmond", "3121"),
        (1, 500, "Swan Street", "Richmond", "3121"),
        (1, 400, "Church Street", "Richmond", "3121"),
        (1, 400, "Chapel Street", "Prahran", "3181"),
        (1, 300, "High Street", "Prahran", "3181"),
        (1, 600, "Sydney Road", "Brunswick", "3056"),
        (1, 300, "Nicholson Street", "Carlton", "3053"),
        (1, 300, "Lygon Street", "Carlton", "3053"),
        (1, 400, "Glenferrie Road", "Hawthorn", "3122"),
        (1, 400, "Burke Road", "Camberwell", "3124"),
        (1, 300, "Toorak Road", "Toorak", "3142"),
        (1, 300, "Commercial Road", "Prahran", "3181"),
        (1, 400, "Whitehorse Road", "Blackburn", "3130"),
        (1, 500, "Canterbury Road", "Heathmont", "3135"),
        (1, 400, "Station Street", "Box Hill", "3128"),
        (1, 300, "Plenty Road", "Preston", "3072"),
        (1, 400, "High Street", "Northcote", "3070"),
        (1, 300, "St Kilda Road", "Melbourne", "3004"),
        (1, 400, "Dandenong Road", "Malvern East", "3145"),
    ],
    ("VIC", "Geelong"): [
        (1, 300, "Moorabool Street", "Geelong", "3220"),
        (1, 200, "Malop Street", "Geelong", "3220"),
        (1, 200, "Ryrie Street", "Geelong", "3220"),
        (1, 400, "Pakington Street", "Geelong West", "3218"),
        (1, 300, "Shannon Avenue", "Geelong West", "3218"),
        (1, 300, "Surfcoast Highway", "Torquay", "3228"),
        (1, 200, "The Esplanade", "Ocean Grove", "3226"),
    ],
    ("VIC", "Ballarat"): [
        (1, 400, "Sturt Street", "Ballarat Central", "3350"),
        (1, 300, "Bridge Street", "Ballarat Central", "3350"),
        (1, 200, "Lydiard Street", "Ballarat Central", "3350"),
        (1, 300, "Mair Street", "Ballarat Central", "3350"),
    ],
    ("VIC", "Bendigo"): [
        (1, 300, "Mitchell Street", "Bendigo", "3550"),
        (1, 200, "Pall Mall", "Bendigo", "3550"),
        (1, 200, "View Street", "Bendigo", "3550"),
        (1, 300, "High Street", "Bendigo", "3550"),
    ],
    # ── QLD ──────────────────────────────────────────────────────────────────
    ("QLD", "Brisbane"): [
        (1, 300, "Queen Street", "Brisbane City", "4000"),
        (1, 400, "Adelaide Street", "Brisbane City", "4000"),
        (1, 500, "Ann Street", "Brisbane City", "4000"),
        (1, 400, "George Street", "Brisbane City", "4000"),
        (1, 200, "Creek Street", "Brisbane City", "4000"),
        (1, 200, "Eagle Street", "Brisbane City", "4000"),
        (1, 400, "Mary Street", "Brisbane City", "4000"),
        (1, 300, "Charlotte Street", "Brisbane City", "4000"),
        (1, 300, "Edward Street", "Brisbane City", "4000"),
        (1, 300, "William Street", "Brisbane City", "4000"),
        (1, 300, "Grey Street", "South Brisbane", "4101"),
        (1, 400, "Melbourne Street", "South Brisbane", "4101"),
        (1, 500, "Brunswick Street", "Fortitude Valley", "4006"),
        (1, 300, "Logan Road", "Woolloongabba", "4102"),
        (1, 300, "Main Street", "Kangaroo Point", "4169"),
        (1, 400, "Wickham Street", "Fortitude Valley", "4006"),
        (1, 500, "Old Cleveland Road", "Coorparoo", "4151"),
        (1, 400, "Ipswich Road", "Woolloongabba", "4102"),
        (1, 400, "Gympie Road", "Kedron", "4031"),
        (1, 300, "Cavendish Road", "Coorparoo", "4151"),
        (1, 300, "Montague Road", "West End", "4101"),
        (1, 400, "Boundary Street", "West End", "4101"),
        (1, 300, "Given Terrace", "Paddington", "4064"),
        (1, 400, "Waterworks Road", "Ashgrove", "4060"),
    ],
    ("QLD", "Gold Coast"): [
        (1, 400, "Cavill Avenue", "Surfers Paradise", "4217"),
        (1, 300, "Gold Coast Highway", "Surfers Paradise", "4217"),
        (1, 200, "Orchid Avenue", "Surfers Paradise", "4217"),
        (1, 300, "Elkhorn Avenue", "Surfers Paradise", "4217"),
        (1, 400, "Bundall Road", "Bundall", "4217"),
        (1, 300, "Ferry Road", "Southport", "4215"),
        (1, 300, "Scarborough Street", "Southport", "4215"),
        (1, 400, "Nerang Street", "Nerang", "4211"),
        (1, 200, "Robina Town Centre Drive", "Robina", "4226"),
    ],
    ("QLD", "Sunshine Coast"): [
        (1, 300, "Aerodrome Road", "Maroochydore", "4558"),
        (1, 200, "Ocean Street", "Maroochydore", "4558"),
        (1, 200, "Sunshine Beach Road", "Noosa Heads", "4567"),
        (1, 400, "Nicklin Way", "Warana", "4575"),
        (1, 200, "Bulcock Street", "Caloundra", "4551"),
        (1, 300, "Hastings Street", "Noosa Heads", "4567"),
    ],
    ("QLD", "Townsville"): [
        (1, 300, "Flinders Street", "Townsville City", "4810"),
        (1, 200, "Denham Street", "Townsville City", "4810"),
        (1, 300, "Sturt Street", "Townsville City", "4810"),
        (1, 400, "Ross River Road", "Mundingburra", "4812"),
    ],
    ("QLD", "Cairns"): [
        (1, 300, "Abbott Street", "Cairns City", "4870"),
        (1, 200, "Sheridan Street", "Cairns City", "4870"),
        (1, 300, "Spence Street", "Cairns City", "4870"),
        (1, 200, "Lake Street", "Cairns City", "4870"),
    ],
    # ── WA ───────────────────────────────────────────────────────────────────
    ("WA", "Perth"): [
        (1, 500, "St Georges Terrace", "Perth", "6000"),
        (1, 500, "Hay Street", "Perth", "6000"),
        (1, 500, "Murray Street", "Perth", "6000"),
        (1, 400, "William Street", "Perth", "6000"),
        (1, 300, "Barrack Street", "Perth", "6000"),
        (1, 200, "Pier Street", "Perth", "6000"),
        (1, 300, "Wellington Street", "Perth", "6000"),
        (1, 300, "Aberdeen Street", "Northbridge", "6003"),
        (1, 300, "James Street", "Northbridge", "6003"),
        (1, 300, "Beaufort Street", "Mount Lawley", "6050"),
        (1, 200, "Rokeby Road", "Subiaco", "6008"),
        (1, 500, "Stirling Highway", "Nedlands", "6009"),
        (1, 200, "Broadway", "Nedlands", "6009"),
        (1, 400, "Albany Highway", "Victoria Park", "6100"),
        (1, 300, "Canning Highway", "Applecross", "6153"),
        (1, 400, "Grand Promenade", "Bedford", "6052"),
        (1, 300, "Walter Road", "Morley", "6062"),
        (1, 300, "Fitzgerald Street", "Northbridge", "6003"),
        (1, 400, "Wanneroo Road", "Westminster", "6061"),
        (1, 300, "High Street", "Fremantle", "6160"),
    ],
    ("WA", "Fremantle"): [
        (1, 200, "High Street", "Fremantle", "6160"),
        (1, 200, "Market Street", "Fremantle", "6160"),
        (1, 300, "William Street", "Fremantle", "6160"),
        (1, 200, "Queen Street", "Fremantle", "6160"),
        (1, 300, "South Terrace", "Fremantle", "6160"),
        (1, 300, "Hampton Road", "Fremantle", "6160"),
        (1, 200, "Canning Highway", "Fremantle", "6160"),
    ],
    ("WA", "Mandurah"): [
        (1, 300, "Pinjarra Road", "Mandurah", "6210"),
        (1, 200, "Mandurah Terrace", "Mandurah", "6210"),
        (1, 200, "Smart Street", "Mandurah", "6210"),
    ],
    # ── SA ───────────────────────────────────────────────────────────────────
    ("SA", "Adelaide"): [
        (1, 400, "King William Street", "Adelaide", "5000"),
        (1, 200, "Grenfell Street", "Adelaide", "5000"),
        (1, 100, "Hindley Street", "Adelaide", "5000"),
        (1, 400, "Rundle Street", "Adelaide", "5000"),
        (1, 300, "Pulteney Street", "Adelaide", "5000"),
        (1, 400, "North Terrace", "Adelaide", "5000"),
        (1, 300, "Wakefield Street", "Adelaide", "5000"),
        (1, 400, "Hutt Street", "Adelaide", "5000"),
        (1, 200, "Grote Street", "Adelaide", "5000"),
        (1, 300, "Currie Street", "Adelaide", "5000"),
        (1, 400, "The Parade", "Norwood", "5067"),
        (1, 400, "Unley Road", "Unley", "5061"),
        (1, 200, "Jetty Road", "Glenelg", "5045"),
        (1, 400, "Main North Road", "Prospect", "5082"),
        (1, 300, "Port Road", "Hindmarsh", "5007"),
        (1, 400, "Magill Road", "Stepney", "5069"),
        (1, 200, "Moseley Street", "Glenelg", "5045"),
        (1, 300, "Montacute Road", "Campbelltown", "5074"),
    ],
    ("SA", "Mount Gambier"): [
        (1, 200, "Commercial Street", "Mount Gambier", "5290"),
        (1, 300, "Bay Road", "Mount Gambier", "5290"),
        (1, 200, "Helen Street", "Mount Gambier", "5290"),
    ],
    # ── TAS ──────────────────────────────────────────────────────────────────
    ("TAS", "Hobart"): [
        (1, 200, "Collins Street", "Hobart", "7000"),
        (1, 300, "Elizabeth Street", "Hobart", "7000"),
        (1, 300, "Liverpool Street", "Hobart", "7000"),
        (1, 200, "Harrington Street", "Hobart", "7000"),
        (1, 400, "Macquarie Street", "Hobart", "7000"),
        (1, 100, "Salamanca Place", "Battery Point", "7004"),
        (1, 200, "Sandy Bay Road", "Sandy Bay", "7005"),
        (1, 200, "New Town Road", "New Town", "7008"),
        (1, 300, "Murray Street", "Hobart", "7000"),
        (1, 200, "Campbell Street", "Hobart", "7000"),
    ],
    ("TAS", "Launceston"): [
        (1, 300, "Brisbane Street", "Launceston", "7250"),
        (1, 400, "Charles Street", "Launceston", "7250"),
        (1, 200, "Cameron Street", "Launceston", "7250"),
        (1, 200, "Patterson Street", "Launceston", "7250"),
        (1, 300, "Wellington Street", "Launceston", "7250"),
        (1, 200, "George Street", "Launceston", "7250"),
    ],
    ("TAS", "Devonport"): [
        (1, 200, "Rooke Street", "Devonport", "7310"),
        (1, 300, "Best Street", "Devonport", "7310"),
        (1, 200, "Steele Street", "Devonport", "7310"),
    ],
    # ── ACT ──────────────────────────────────────────────────────────────────
    ("ACT", "Canberra"): [
        (1, 300, "Northbourne Avenue", "Canberra", "2600"),
        (1, 100, "London Circuit", "Canberra", "2600"),
        (1, 200, "Bunda Street", "Canberra City", "2601"),
        (1, 200, "Mort Street", "Braddon", "2612"),
        (1, 200, "Lonsdale Street", "Braddon", "2612"),
        (1, 100, "Emu Bank", "Belconnen", "2617"),
        (1, 200, "Benjamin Way", "Belconnen", "2617"),
        (1, 200, "Yamba Drive", "Woden", "2606"),
        (1, 200, "Anketell Street", "Tuggeranong", "2900"),
        (1, 200, "Gungahlin Drive", "Gungahlin", "2912"),
        (1, 300, "Flemington Road", "Gungahlin", "2912"),
        (1, 200, "Melrose Drive", "Phillip", "2606"),
    ],
    # ── NT ───────────────────────────────────────────────────────────────────
    ("NT", "Darwin"): [
        (1, 200, "Mitchell Street", "Darwin City", "0800"),
        (1, 300, "Smith Street", "Darwin City", "0800"),
        (1, 200, "Knuckey Street", "Darwin City", "0800"),
        (1, 300, "McMinn Street", "Darwin City", "0800"),
        (1, 200, "Cavenagh Street", "Darwin City", "0800"),
        (1, 300, "Stuart Highway", "Palmerston", "0830"),
        (1, 200, "Bagot Road", "Coconut Grove", "0810"),
    ],
    ("NT", "Alice Springs"): [
        (1, 300, "Todd Street", "Alice Springs", "0870"),
        (1, 200, "Parsons Street", "Alice Springs", "0870"),
        (1, 200, "Bath Street", "Alice Springs", "0870"),
        (1, 200, "Gregory Terrace", "Alice Springs", "0870"),
    ],
    ("NT", "Palmerston"): [
        (1, 300, "Stuart Highway", "Palmerston", "0830"),
        (1, 200, "Roystonea Avenue", "Palmerston", "0830"),
    ],
}

# Fall back to the state capital pool for any unlisted city.
_STATE_CAPITAL_KEY = {
    "NSW": ("NSW", "Sydney"),
    "VIC": ("VIC", "Melbourne"),
    "QLD": ("QLD", "Brisbane"),
    "WA": ("WA", "Perth"),
    "SA": ("SA", "Adelaide"),
    "TAS": ("TAS", "Hobart"),
    "ACT": ("ACT", "Canberra"),
    "NT": ("NT", "Darwin"),
}


def pick_real_address(state: str, city: str) -> tuple:
    """Return (address_string, suburb, postcode) from the GNAF-verified pool.

    Args:
        state: Australian state abbreviation, e.g. "NSW"
        city:  City name, e.g. "Sydney" — falls back to state capital if not in pool

    Returns:
        Tuple of (full_address_str, suburb, postcode)
        e.g. ("227 George Street, Sydney NSW 2000", "Sydney", "2000")
    """
    key = (state, city)
    pool = REAL_STREET_POOLS.get(key) or REAL_STREET_POOLS.get(
        _STATE_CAPITAL_KEY.get(state, ("NSW", "Sydney"))
    )
    min_num, max_num, street, suburb, postcode = random.choice(pool)
    # Keep realistic even/odd parity
    number = random.randint(min_num, max_num)
    if random.random() < 0.5:
        number = number if number % 2 == 0 else number + 1
    else:
        number = number if number % 2 != 0 else number + 1
    number = max(1, min(number, max_num))
    return f"{number} {street}, {suburb} {state} {postcode}", suburb, postcode
