import requests
import logging

logger = logging.getLogger(__name__)

BASE_URL = "https://api.tazkarti.com/api"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
    "Referer": "https://www.tazkarti.com/",
    "Origin": "https://www.tazkarti.com",
}

# ===== قراءة JSON بشكل آمن =====
def safe_json(response):
    try:
        return response.json()
    except Exception as e:
        logger.error(f"JSON Decode Error: {e}")
        try:
            logger.error(f"Response Text: {response.text[:500]}")
        except:
            pass
        return []

# ===== جلب المباريات =====
def get_matches():
    try:
        url = f"{BASE_URL}/matches"
        response = requests.get(url, headers=HEADERS, timeout=20)
        logger.info(f"Matches Status Code: {response.status_code}")
        if response.status_code != 200:
            logger.error(f"Matches endpoint returned: {response.status_code}")
            return []
        data = safe_json(response)
        if isinstance(data, dict):
            if "data" in data:
                return data["data"]
            if "matches" in data:
                return data["matches"]
            return []
        if isinstance(data, list):
            return data
        return []
    except Exception as e:
        logger.error(f"get_matches Error: {e}")
        return []

# ===== قائمة ثابتة باندية الدوري المصري الممتاز (احتياطية) =====
# IDs سالبة عشان متتعارضش مع IDs الموقع الحقيقية. بيتم استبدالها بـ ID
# الموقع الحقيقي تلقائياً أول ما الفريق يظهر في المباريات (مطابقة بالاسم).
EGYPT_PL_TEAMS_STATIC = [
    {"id": -1, "name": "Al Ahly", "nameAr": "الأهلي"},
    {"id": -2, "name": "Zamalek", "nameAr": "الزمالك"},
    {"id": -3, "name": "Al Masry", "nameAr": "المصري"},
    {"id": -4, "name": "Pyramids", "nameAr": "بيراميدز"},
    {"id": -5, "name": "Future FC", "nameAr": "فيوتشر"},
    {"id": -6, "name": "Ismaily", "nameAr": "الإسماعيلي"},
    {"id": -7, "name": "ENPPI", "nameAr": "إنبي"},
    {"id": -8, "name": "El Dakhleya", "nameAr": "الداخلية"},
    {"id": -9, "name": "Smouha", "nameAr": "سموحة"},
    {"id": -10, "name": "Ceramica Cleopatra", "nameAr": "سيراميكا كليوباترا"},
    {"id": -11, "name": "Modern Future", "nameAr": "مودرن فيوتشر"},
    {"id": -12, "name": "National Bank of Egypt", "nameAr": "بنك القاهرة"},
    {"id": -13, "name": "Ghazl El Mahalla", "nameAr": "غزل المحلة"},
    {"id": -14, "name": "El Gouna", "nameAr": "الجونة"},
    {"id": -15, "name": "Pharco", "nameAr": "فاركو"},
    {"id": -16, "name": "Haras El Hodood", "nameAr": "حرس الحدود"},
    {"id": -17, "name": "Zed FC", "nameAr": "زد"},
    {"id": -18, "name": "ZED FC Youth", "nameAr": "المقاولون العرب"},
    {"id": -19, "name": "Baladeyet El Mahalla", "nameAr": "بلدية المحلة"},
    {"id": -20, "name": "Tala'ea El Gaish", "nameAr": "طلائع الجيش"},
]


# ===== جلب الفرق =====
def get_epl_teams():
    api_teams = []
    try:
        # جرب endpoints مختلفة للفرق
        for endpoint in ["/teams", "/epl/teams", "/football/teams", "/clubs"]:
            try:
                url = f"{BASE_URL}{endpoint}"
                response = requests.get(url, headers=HEADERS, timeout=10)
                if response.status_code == 200:
                    data = safe_json(response)
                    if isinstance(data, list) and len(data) > 0:
                        logger.info(f"Got {len(data)} teams from {endpoint}")
                        api_teams = data
                        break
                    if isinstance(data, dict):
                        for key in ["data", "teams", "clubs", "results"]:
                            if key in data and isinstance(data[key], list) and len(data[key]) > 0:
                                logger.info(f"Got {len(data[key])} teams from {endpoint} -> {key}")
                                api_teams = data[key]
                                break
                    if api_teams:
                        break
            except Exception as e:
                logger.warning(f"Endpoint {endpoint} failed: {e}")
                continue

        # استخرج كمان أي فرق تانية ظاهرة في المباريات (مش موجودة في الـ API endpoint)
        teams_dict = {t["id"]: t for t in api_teams if isinstance(t, dict) and "id" in t}

        matches = get_matches()
        for m in matches:
            t1_id = m.get("teamId1")
            if t1_id and t1_id not in teams_dict:
                teams_dict[t1_id] = {
                    "id": t1_id,
                    "name": m.get("teamName1", ""),
                    "nameAr": m.get("teamNameAr1") or m.get("teamName1", ""),
                }
            t2_id = m.get("teamId2")
            if t2_id and t2_id not in teams_dict:
                teams_dict[t2_id] = {
                    "id": t2_id,
                    "name": m.get("teamName2", ""),
                    "nameAr": m.get("teamNameAr2") or m.get("teamName2", ""),
                }

        # دمج القائمة الثابتة: لو فريق موجود بالفعل (بالاسم) من الموقع نسيبه
        # بـ ID الموقع الحقيقي، ولو مش موجود نضيفه بـ ID سالب ثابت عشان
        # يفضل يظهر في القايمة حتى لو مفيش له مباريات دلوقتي.
        existing_names = {
            (t.get("nameAr") or t.get("name") or "").strip()
            for t in teams_dict.values()
        }
        for static_team in EGYPT_PL_TEAMS_STATIC:
            if static_team["nameAr"] not in existing_names and static_team["name"] not in existing_names:
                teams_dict[static_team["id"]] = static_team

        teams = sorted(
            teams_dict.values(),
            key=lambda t: t.get("nameAr") or t.get("name") or ""
        )
        logger.info(f"Total {len(teams)} teams (API + matches + static)")
        return teams

    except Exception as e:
        logger.error(f"get_epl_teams Error: {e}")
        return EGYPT_PL_TEAMS_STATIC

# ===== مباريات فريق معين =====
def get_matches_for_team(team_id):
    try:
        matches = get_matches()
        if not matches:
            return []
        return [
            m for m in matches
            if m.get("teamId1") == team_id or m.get("teamId2") == team_id
        ]
    except Exception as e:
        logger.error(f"get_matches_for_team Error: {e}")
        return []

# ===== مباريات التذاكر متاحة فيها =====
def get_available_matches_for_team(team_id):
    try:
        matches = get_matches_for_team(team_id)
        return [m for m in matches if m.get("matchStatus") == 1]
    except Exception as e:
        logger.error(f"get_available_matches_for_team Error: {e}")
        return []
