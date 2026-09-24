"""
Telangana jurisdiction data: District -> Mandal -> {police_stations, revenue_offices}.

SOURCING NOTE (read this before treating this as authoritative):
- The 33 districts are the real, current districts of Telangana (verified).
- Mandals are REAL mandal names drawn from the Telangana mandal list
  (Wikipedia / Census of India), but this is a CURATED SUBSET per district
  (roughly 4-6 of each district's mandals), not the complete official list
  of 612 mandals. Some district <-> mandal pairings around the 2016-2019
  district-reorganisation boundaries may be imprecise.
- Police stations and revenue offices are NOT individually scraped from
  each district police website (no single consolidated official source
  exists for this). They are generated using the real, standard naming
  convention used across Telangana ("<Mandal> PS", "<Mandal> I Town PS" /
  "II Town PS" for district HQs, "Tehsildar Office, <Mandal>", "RDO
  Office, <District HQ>"). Treat these as representative, not verified
  individually against a police roster.
Flag anything here you need to double-check before relying on it.
"""

DISTRICTS = {
    "Adilabad": ["Adilabad Urban", "Adilabad Rural", "Bela", "Boath", "Ichoda", "Utnoor"],
    "Bhadradri Kothagudem": ["Kothagudem", "Palvancha", "Yellandu", "Bhadrachalam", "Aswaraopeta", "Sathupalli"],
    "Hanumakonda": ["Hanumakonda", "Hasanparthy", "Kazipet", "Elkathurthy"],
    "Hyderabad": ["Charminar", "Golkonda", "Bahadurpura", "Nampally", "Asif Nagar", "Amberpet"],
    "Jagtial": ["Jagtial", "Jagtial Rural", "Dharmapuri", "Raikal", "Velgatoor"],
    "Jangaon": ["Jangaon", "Bachannapet", "Narmetta", "Devaruppala"],
    "Jayashankar Bhupalpally": ["Bhupalpally", "Mahadevpur", "Ghanpur (Mulugu)", "Chityal"],
    "Jogulamba Gadwal": ["Gadwal", "Aiza", "Waddepalle", "Alampur"],
    "Kamareddy": ["Kamareddy", "Bichkunda", "Yellareddy", "Banswada", "Domakonda"],
    "Karimnagar": ["Karimnagar", "Choppadandi", "Huzurabad", "Jammikunta", "Ganneruvaram"],
    "Khammam": ["Khammam Urban", "Khammam Rural", "Madhira", "Wyra", "Kusumanchi"],
    "Komaram Bheem Asifabad": ["Asifabad", "Kagaznagar", "Sirpur (T)", "Bejjur"],
    "Mahabubabad": ["Mahabubabad", "Kesamudram", "Dornakal", "Garla"],
    "Mahabubnagar": ["Mahabubnagar Urban", "Mahabubnagar Rural", "Jadcherla", "Balanagar"],
    "Mancherial": ["Mancherial", "Bellampally", "Luxettipet", "Chennur"],
    "Medak": ["Medak", "Narsapur", "Ramayampet", "Shankarampet"],
    "Medchal-Malkajgiri": ["Malkajgiri", "Shamirpet", "Kapra", "Ghatkesar"],
    "Mulugu": ["Mulugu", "Venkatapur", "Eturnagaram", "Govindaraopet"],
    "Nagarkurnool": ["Nagarkurnool", "Achampet", "Kalwakurthy", "Kollapur"],
    "Nalgonda": ["Nalgonda", "Miryalaguda", "Devarakonda", "Nakrekal"],
    "Narayanpet": ["Narayanpet", "Maganoor", "Makthal", "Narva"],
    "Nirmal": ["Nirmal Urban", "Nirmal Rural", "Bhainsa", "Khanapur"],
    "Nizamabad": ["Nizamabad Urban", "Nizamabad Rural", "Bodhan", "Armur"],
    "Peddapalli": ["Peddapalli", "Manthani", "Ramagundam", "Sultanabad"],
    "Rajanna Sircilla": ["Sircilla", "Vemulawada", "Konaraopeta", "Chandurthi"],
    "Ranga Reddy": ["Shamshabad", "Maheshwaram", "Serilingampally", "Rajendranagar"],
    "Sangareddy": ["Sangareddy", "Patancheru", "Zaheerabad", "Sadasivpet"],
    "Siddipet": ["Siddipet Urban", "Siddipet Rural", "Dubbak", "Cherial"],
    "Suryapet": ["Suryapet", "Kodad", "Maddirala", "Munagala"],
    "Vikarabad": ["Vikarabad", "Tandur", "Pargi", "Doma"],
    "Wanaparthy": ["Wanaparthy", "Atmakur", "Pebbair", "Kothakota"],
    "Warangal": ["Wardhannapet", "Narsampet", "Parvathagiri", "Geesugonda"],
    "Yadadri Bhuvanagiri": ["Bhoodhan Pochampally", "Choutuppal", "Ramannapet", "Valigonda"],
}


def _police_stations(district: str, mandal: str, is_first: bool) -> list[str]:
    if is_first:
        return [f"{mandal} I Town PS", f"{mandal} II Town PS", f"{mandal} Rural PS"]
    return [f"{mandal} PS"]


def _revenue_offices(district: str, mandal: str, is_first: bool) -> list[str]:
    offices = [f"Tehsildar Office, {mandal}"]
    if is_first:
        offices.append(f"RDO Office, {district}")
    return offices


def build_jurisdiction_tree() -> dict:
    tree = {}
    for district, mandals in DISTRICTS.items():
        tree[district] = {}
        for i, mandal in enumerate(mandals):
            tree[district][mandal] = {
                "police_stations": _police_stations(district, mandal, i == 0),
                "revenue_offices": _revenue_offices(district, mandal, i == 0),
            }
    return tree


JURISDICTION_TREE = build_jurisdiction_tree()
