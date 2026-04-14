import re
import unicodedata

import streamlit as st


KNOWN_PLACES = ["더화이트호텔", "화이트호텔", "오리엔탈", "그네"]
VEHICLE_KEYWORDS = (
    "CAR",
    "AUTOMOBILE",
    "TAXI",
    "TRUCK",
    "BUS",
    "VAN",
    "SCOOTER",
    "MOTOR",
    "TRACTOR",
    "BICYCLE",
    "BIKE",
    "RICKSHAW",
    "TRAM",
    "LOCOMOTIVE",
    "SHIP",
    "BOAT",
    "CANOE",
    "FERRY",
)


def normalize_phone(text: str) -> str:
    m = re.search(r"010\D*\d{3,4}\D*\d{4}", text)
    if not m:
        return ""
    digits = re.sub(r"\D", "", m.group(0))
    if len(digits) != 11 or not digits.startswith("010"):
        return ""
    return f"{digits[:3]} {digits[3:7]} {digits[7:]}"


def normalize_time(hour: int, minute: int) -> str:
    return f"{hour:02d}:{minute:02d}"


def extract_naver_time(line: str) -> str:
    m = re.search(r"(?:오전|오후)?\s*(\d{1,2})\s*:\s*(\d{2})", line)
    if not m:
        return ""
    return normalize_time(int(m.group(1)), int(m.group(2)))


def extract_phone_time(line: str) -> str:
    m = re.search(r"(?:오전|오후)?\s*(\d{1,2})\s*:\s*(\d{1,2})", line)
    if m:
        return normalize_time(int(m.group(1)), int(m.group(2)))
    m = re.search(r"(?:오전|오후)?\s*(\d{1,2})\s*시(?:\s*(\d{1,2})\s*분?)?", line)
    if m:
        return normalize_time(int(m.group(1)), int(m.group(2) or 0))
    return ""


def contains_vehicle_emoji(text: str) -> bool:
    for ch in text:
        name = unicodedata.name(ch, "")
        if not name or "CLOCK" in name:
            continue
        if any(key in name for key in VEHICLE_KEYWORDS):
            return True
    return False


def extract_place(text: str) -> str:
    if "휘닉스" in text:
        return "그네"
    for place in KNOWN_PLACES:
        if place in text:
            return place
    m = re.search(r"([가-힣A-Za-z0-9]{2,20}?)(?:에서|로|으로)?\s*(?:픽업|픽드랍)", text)
    if m:
        return m.group(1).strip()
    return ""


def split_naver_blocks(text: str) -> list[str]:
    normalized = text.replace("\r\n", "\n").strip()
    if not normalized:
        return []
    blocks = re.split(r"(?=예약자)", normalized)
    return [b.strip() for b in blocks if "예약자" in b]


def parse_naver(text: str) -> list[dict]:
    items: list[dict] = []
    for block in split_naver_blocks(text):
        lines = [ln.strip() for ln in block.split("\n") if ln.strip()]
        joined = "\n".join(lines)

        name = ""
        for line in lines:
            m_name = re.search(r"예약자\s*(.+)", line)
            if m_name:
                name = m_name.group(1).strip()
                break

        time = ""
        for line in lines:
            if "이용일시" in line:
                time = extract_naver_time(line)
                break
        if not time:
            continue

        adult_matches = re.findall(r"성인\s*(\d+)", joined)
        child_matches = re.findall(r"어린이\s*(\d+)", joined)
        adult = int(adult_matches[-1]) if adult_matches else 0
        child = int(child_matches[-1]) if child_matches else 0

        phone = normalize_phone(joined)

        pickup = ("픽업" in joined) or ("픽드랍" in joined)

        place_context = " ".join([ln for ln in lines if any(k in ln for k in ("요청사항", "상품", "픽업", "픽드랍"))])
        place = extract_place(place_context if place_context else joined)
        if not pickup:
            place = ""

        items.append(
            {
                "time": time,
                "adult": adult,
                "child": child,
                "place": place,
                "pickup": pickup,
                "phone": phone,
                "name": name,
            }
        )
    return items


def parse_phone(text: str) -> list[dict]:
    blocks = re.split(r"\n\s*\n", text.strip()) if text.strip() else []
    items: list[dict] = []

    for block in blocks:
        lines = [ln.strip() for ln in block.split("\n") if ln.strip()]
        if not lines:
            continue
        joined = "\n".join(lines)

        time = ""
        for line in lines:
            time = extract_phone_time(line)
            if time:
                break
        if not time:
            continue

        adult_matches = re.findall(r"성인[\t ]*(\d+)", joined)
        child_matches = re.findall(r"(?:어린이|아이)[\t ]*(\d+)", joined)
        adult = int(adult_matches[-1]) if adult_matches else 0
        child = int(child_matches[-1]) if child_matches else 0
        if adult == 0 and child == 0:
            m_count = re.search(r"(\d+)\s*명", joined)
            if m_count:
                adult = int(m_count.group(1))

        phone = ""
        for line in lines:
            phone = normalize_phone(line)
            if phone:
                break

        pickup = (
            "픽업" in joined
            or "픽드랍" in joined
            or "그네" in joined
            or contains_vehicle_emoji(joined)
        )

        place = "그네" if "그네" in joined else extract_place(joined)
        if pickup and not place:
            place = "그네"

        items.append(
            {
                "time": time,
                "adult": adult,
                "child": child,
                "place": place,
                "pickup": pickup,
                "phone": phone,
            }
        )
    return items


def sort_items(items: list[dict]) -> list[dict]:
    return sorted(items, key=lambda x: int(x["time"][:2]) * 60 + int(x["time"][3:]))


def build_people_text(adult: int, child: int) -> str:
    parts = []
    if adult > 0:
        parts.append(f"성인 {adult}")
    if child > 0:
        parts.append(f"아이 {child}")
    return " ".join(parts)


def format_item(item: dict) -> str:
    line2_parts = [build_people_text(item.get("adult", 0), item.get("child", 0))]
    if item.get("place"):
        line2_parts.append(item["place"])
    if item.get("pickup"):
        line2_parts.append("🚗")
    line2 = " ".join([x for x in line2_parts if x]).strip()
    return f"{item.get('time', '')}\n{line2}\n{item.get('phone', '')}"


def format_output(items: list[dict]) -> str:
    return "\n\n".join(format_item(item) for item in items)


st.set_page_config(page_title="예약 정리기", layout="centered")
st.title("예약 정리기")

naver_text = st.text_area("네이버 예약 텍스트", height=240)
phone_text = st.text_area("전화 예약 텍스트", height=220)

if st.button("정리하기"):
    naver_items = parse_naver(naver_text)
    phone_items = parse_phone(phone_text)
    st.write(f"네이버 파싱 개수: {len(naver_items)}")

    all_items = sort_items(naver_items + phone_items)
    result = format_output(all_items)

    if result:
        st.success("완료")
        st.text_area("결과", result, height=420)
    else:
        st.info("파싱된 예약이 없습니다.")
